# 生产级 Serving 栈——KV Offloading 与 Cache-Aware 路由

> 一个生产级 serving 栈把 router、engine 与可观测性串成一个 Kubernetes 部署——并把 KV cache 当作一种可以离开 GPU 的资源。KV offloading 把 KV cache 从 GPU 显存中抽出，并在查询与 engine 之间复用它（先 CPU DRAM，再磁盘/Ceph）。vLLM 的 production-stack 是参考部署；LMCache 是 offloading 层。vLLM 0.11.0 的 KV Offloading Connector（2026 年 1 月）通过 Connector API（v0.9.0+）让这套机制异步化、可插拔。offload 路径通常藏在请求路径之外，不过 cache miss 与 promotion 会增加端到端 latency。即使没有共享前缀，LMCache 也有价值——当 GPU 的 KV slot 用尽时，被抢占的请求可以从 CPU 恢复，而不必重算 prefill。在 4 个 a3-highgpu-4g 上 16x H100（80GB HBM）的公开 benchmark：当 KV cache 超过 HBM 时，原生 CPU offload 与 LMCache 都能显著提升吞吐；在低 KV 占用时，所有配置都与基线持平，只有很小的开销。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级 KV-spill 模拟器)
**Prerequisites:** 第 17 阶段，第 04 课（Serving Engine Internals），第 06 课（SGLang/RadixAttention）
**Time:** ~60 分钟

## Learning Objectives

- 画出 vLLM production-stack 的分层：router、engine、KV offload、可观测性。
- 解释 KV Offloading Connector API（v0.9.0+），以及 0.11.0 的异步路径如何隐藏 offload latency。
- 量化 LMCache 的 CPU-DRAM 何时有帮助（KV > HBM）、何时只增加开销（KV 小到能装进 HBM）。
- 在部署约束下，在原生 vLLM CPU offload 与 LMCache connector 之间做选择。

## 问题场景

你的 vLLM serving 显示 GPU 的 HBM 占用 100%，并发一升高就出现 preemption 事件。请求被驱逐、重新排队，你在同一分钟里对同一个 2K-token prompt 重复做了四次 prefill。GPU 算力花在了冗余的 prefill 上；goodput 远低于原始吞吐。

加更多 GPU 是线性成本。加更多 HBM 不可能。但 CPU DRAM 很便宜——一个 socket 就有 512 GB+，latency 比 HBM 差几个数量级，但对“暂时温热”的 KV cache 足够。

LMCache 把 KV cache 抽取到 CPU DRAM，让被抢占的请求快速恢复，并让跨 engine 的重复前缀共享缓存，而不必每个 engine 各自重做 prefill。

## 核心概念

### vLLM production-stack

`github.com/vllm-project/production-stack` 是参考 Kubernetes 部署：

- **Router**——cache-aware（第 17 阶段 · 11）。消费 KV 事件。
- **Engine**——vLLM worker。每张 GPU 或每个 TP/PP 组一个。
- **KV cache offload**——LMCache 部署或原生 connector。
- **可观测性**——Prometheus 抓取、Grafana dashboard、OTel trace。
- **控制平面**——服务发现、配置、滚动更新。

以 Helm chart + operator 的形式交付。

### KV Offloading Connector API（v0.9.0+）

vLLM 0.9.0 引入了 Connector API，用于可插拔的 KV cache 后端。你的 engine 把 block offload 给 connector；connector 把它们存起来（RAM、磁盘、对象存储、LMCache）。请求需要某个 block 时，connector 把它加载回来。

vLLM 0.11.0（2026 年 1 月）增加了异步 offload 路径——offload 可以在后台进行，因此在常见情况下 engine 不会阻塞在它上面。端到端 latency 与吞吐仍取决于负载形态、KV cache 命中率与系统压力；vLLM 自己的说明也指出，在低命中率时 custom-kernel offload 可能降低吞吐，且异步调度与 speculative decoding 存在已知的交互问题。

### 原生 CPU offload vs LMCache

**原生 vLLM CPU offload**：engine 本地。把 KV block 存在宿主 RAM。实现快，零网络跳转。不跨 engine。

**LMCache connector**：集群级。把 block 存在共享的 LMCache server（CPU DRAM + Ceph/S3 层）。任何 engine 都能访问这些 block。公开了 16x H100 的 benchmark。

单 engine 有 HBM 压力时选原生。多个 engine 共享前缀时（RAG 共用 system prompt、多租户共用模板）选 LMCache。

### Benchmark 表现

跨 4 个 a3-highgpu-4g 的 16x H100（80 GB HBM）测试：

- 低 KV 占用（短 prompt、低并发）：所有配置都与基线持平，LMCache 增加约 3-5% 开销。
- 中等占用：LMCache 开始在跨 engine 的前缀复用上有帮助。
- KV 超过 HBM：原生 CPU offload 与 LMCache 都显著提升吞吐；LMCache 增益更大，因为跨 engine 共享。

### 什么时候 LMCache 是决定性的

- 多租户 serving，system prompt 在租户之间共享。
- RAG 场景，文档 chunk 在查询之间重复。
- 同一基座的微调变体（LoRA），复用 base 模型的 KV 能减少冗余工作。
- preemption 频繁的负载：从 CPU 恢复比重新 prefill 便宜。

### 什么时候不该启用

- HBM 压力小——你付出开销却得不到收益。
- 短上下文（<1K tokens）——传输时间 > 重新 prefill。
- 单租户单 prompt 负载——没有可捕获的复用。

### 与 disaggregated serving 的集成

第 17 阶段 · 17 的 disaggregated serving + LMCache 会叠加：从 prefill 池到 decode 池的 KV 传输如果没有被使用，就落在 LMCache 里；后续查询从 LMCache 拉取。第 17 阶段 · 11 的 cache-aware router 可以路由到本地缓存或 LMCache 共享缓存匹配的 engine。

### 你该记住的数字

- vLLM 0.9.0：Connector API 发布。
- vLLM 0.11.0（2026 年 1 月）：异步 offload 路径；端到端 latency 影响取决于负载、KV 命中率与系统压力（不是绝对保证）。
- 16x H100 benchmark：当 KV 占用超过 HBM 时，LMCache 有帮助。
- HBM 压力小时：3-5% 开销且无收益。

```figure
zero-sharding
```

## Use It

`code/main.py` 模拟一个 preemption 频繁、有/无 LMCache 的负载。报告避免的重 prefill 次数、吞吐增益，以及盈亏平衡的 HBM 利用率。

## Ship It

本课产出 `outputs/skill-vllm-stack-decider.md`。给定负载形态与 vLLM 部署，决定用原生、LMCache，还是都不用。

## Exercises

1. 运行 `code/main.py`。在什么 HBM 利用率上，LMCache 开始划算？
2. 一个租户每小时 200 次查询共享一个 6K-token 的 system prompt。计算每个租户的预期 LMCache 节省。
3. LMCache server 是单点故障。设计 HA 策略（副本、回退到原生）。
4. LMCache 存到机械盘上的 Ceph。对于 70B FP8 的 4K-token KV（500 MB），读时间 vs 重新 prefill 是多少？
5. 论证 vLLM 0.11.0 的异步路径是否“免费”——开销藏在哪里？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Production-stack | “参考部署” | vLLM 的 Kubernetes Helm chart + operator |
| Connector API | “KV 后端接口” | vLLM 0.9.0+ 的可插拔 KV 存储接口 |
| Native CPU offload | “engine 本地 spill” | 把 KV 存在同一 engine 的宿主 RAM |
| LMCache | “集群 KV cache” | CPU DRAM + 磁盘上的跨 engine KV cache server |
| 0.11.0 async | “非阻塞 offload” | offload 藏在 engine stream 之后 |
| Preemption | “驱逐腾地方” | HBM 满时对 KV cache 的腾挪 |
| Prefix reuse | “相同 system prompt” | 多个查询共享开头；缓存命中 |
| Ceph tier | “磁盘层” | 缓存层级中位于 DRAM 之下的持久存储 |

## Further Reading

- [vLLM Blog — KV Offloading Connector (Jan 2026)](https://blog.vllm.ai/2026/01/08/kv-offloading-connector.html)
- [vLLM Production Stack GitHub](https://github.com/vllm-project/production-stack) ——Helm chart + operator。
- [LMCache for Enterprise-Scale LLM Inference (arXiv:2510.09665)](https://arxiv.org/html/2510.09665v2)
- [LMCache GitHub](https://github.com/LMCache/LMCache) ——Connector 实现。
- [vLLM 0.11.0 release notes](https://github.com/vllm-project/vllm/releases) ——异步路径细节。
