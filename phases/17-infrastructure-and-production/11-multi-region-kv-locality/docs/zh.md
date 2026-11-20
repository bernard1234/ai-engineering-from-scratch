# 多区域 LLM 服务与 KV cache 局部性

> 轮询负载均衡对带缓存的 LLM 推理是有害的。一个请求若没有落到持有其 prefix 的节点上，就要付完整的 prefill 成本 —— 长 prompt 上 P50 约 800 ms，而 cache 命中时约 80 ms。2026 年的生产模式是 cache-aware router（Rust 写的 vLLM Router、llm-d router），它消费 KV-cache 事件并按 prefix-hash 匹配路由。近期研究（GORGO）把跨区域网络延迟作为路由目标中的一个显式项。商业化的“cross-region inference”产品（Bedrock cross-region inference、GKE multi-cluster gateway）把推理当作黑盒 —— 它们处理可用性，不处理 TTFT。JPMorgan 和 Mayo Clinic 在 2024 年 11 月做过 us-east-1 故障切换，耗时约 22 分钟。容灾的现实是：32% 的 LLM DR 失败，是因为团队备份了权重却忘了 tokenizer 文件或量化配置。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级 prefix-cache-aware router 模拟器)
**Prerequisites:** 第 17 阶段，第 04 课（vLLM Serving），第 06 课（SGLang RadixAttention）
**Time:** ~60 分钟

## Learning Objectives

- 解释为什么轮询负载均衡会破坏带缓存的推理，并量化 TTFT 惩罚。
- 画出 cache-aware router 的结构：输入（KV-cache 事件）、算法（prefix-hash 匹配）、打平规则（GPU 利用率）。
- 说出 LLM 的 32% DR 失败驱动因素（缺少 tokenizer 文件 / 量化配置），并给出一份三文件 DR 清单。
- 区分商业跨区域产品（Bedrock CRI、GKE Multi-Cluster Gateway）与 KV-aware routing。

## 问题场景

你的服务跑在 us-east-1、us-west-2 和 eu-west-1。你在前面放了一个轮询的 ALB。生产中的 prefix cache 命中率降到 8%。TTFT P50 翻了三倍。你的 vLLM 日志显示每个请求都在付完整 prefill 成本。

轮询对无状态服务是最优的。LLM 推理在设计上是有状态的 —— KV cache 编码了模型见过的所有内容。盲目路由就是路由到错误的 cache。

另外，你的团队有一套 DR 计划。你把模型权重备份到 S3 跨区域。一次区域性故障发生，你尝试故障切换，副本却拒绝启动。你忘了 tokenizer.json、量化配置和 RoPE 缩放配置在一个你没同步的独立 bucket 里。

多区域 LLM 服务既是 cache 问题、路由问题，也是 DR 卫生问题 —— 不是负载均衡器问题。

## 核心概念

### Cache-aware routing

请求带着 prompt 到达。Router 对 prefix 做哈希（比如前 512 个 token）；它逐个询问副本“你缓存了这个 prefix 吗？”。副本在分配和驱逐 block 时通过 pub/sub 通道发布 KV-cache 事件。Router 选出匹配的副本，若无人匹配则退回到基于 GPU 利用率的打平规则。

**vLLM Router**（Rust，2026 生产栈）：订阅 `kv.cache.block_added` 事件，维护 prefix-hash → 副本的索引，以 O(1) 查找完成路由。无匹配时退回到最小队列深度。

**llm-d router**：同样的模式，Kubernetes 原生。通过 ControlPlane API 发布事件。

**SGLang RadixAttention**（第 17 阶段 · 06）是副本内的等价物。跨副本路由严格位于上游。

### 数字

2K token prompt、Llama 3.3 70B FP8、H100 上的 TTFT P50：
- Cache 命中（同一副本，prefix 常驻）：约 80 ms。
- Cache 未命中（冷 prefill）：约 800 ms。

10 倍差距。如果你的 router 在副本间达到 60-80% 的 prefix cache 命中，你就在 N 副本容量下近似了单副本性能。如果只命中 10%，你近似的是朴素扩展。

### 跨区域带来了新约束 —— 网络延迟

区域间 RTT：
- us-east-1 ↔ us-west-2：约 65 ms。
- us-east-1 ↔ eu-west-1：约 75 ms。
- us-east-1 ↔ ap-southeast-1：约 220 ms。

如果路由把 us-east-1 的请求送到 ap-southeast-1 的一个热 prefix，节省的 prefill（800 → 80 ms）会被 440 ms 的往返时延彻底淹没。GORGO（2026 年研究）把这层关系显式化 —— 联合最小化 `prefill_time + network_latency`，而不是只看 prefill。答案往往是保持区域化路由，除非 prefix 达到数 MB 级、prefill 占绝对主导。

### 商业的“cross-region inference”在这里帮不上忙

AWS Bedrock cross-region inference 在容量压力下自动把请求路由到其他区域。它优化的是可用性而非 TTFT，并且把推理当作黑盒。GKE Multi-Cluster Gateway 同理 —— 服务级故障切换，对 KV cache 无感知。

即便使用这些产品，你仍然需要应用层的 cache-aware router。它们处理“us-east-1 着火了”这种情况。Cache-aware routing 处理 TTFT 这种情况。

### DR 卫生 —— 32% 的缺文件问题

2026 年被广泛引用的统计：32% 的 LLM DR 失败之所以发生，是因为团队备份了权重却忘了：

- `tokenizer.json` 或 `tokenizer.model`
- 量化配置（`quantize_config.json`、AWQ scale、GPTQ zero-point）
- 模型专属配置（RoPE 缩放、attention mask、chat template）
- 引擎配置（`vllm_config.yaml`、采样默认值、LoRA adapter manifest）

解决办法是一份三文件最小 DR 清单：

1. HF 模型仓库下的所有文件（权重 + 配置 + tokenizer）。
2. 引擎专属的服务配置。
3. 部署清单（K8s YAML、Dockerfile、依赖锁文件）。

此外：每季度跑一次 DR 演练。JPMorgan 在 2024 年 11 月的 us-east-1 演练能实现 22 分钟恢复，仅因为 playbook 被反复演练过。

### 数据驻留是正交问题

EU 客户的 PHI 不能离开 EU。如果你的 cache-aware router 为了一次 prefix 匹配把来自巴黎的请求发到 us-east-1，无论 TTFT 收益多大，你都已经违反 GDPR。先按驻留边界划分 router，再优化 cache。

### 应该记住的数字

- Cache 命中与未命中的 TTFT 差距：约 10 倍（2K prompt 上 80 ms vs 800 ms）。
- 美欧区域间 RTT：约 75 ms。
- DR 失败：32% 缺 tokenizer/量化配置。
- JPMorgan 2024 年 11 月 us-east-1 故障切换：22 分钟（30 分钟 SLA）。

```figure
cache-aware-router
```

## Use It

`code/main.py` 在多区域负载上模拟三种路由策略（轮询、cache-aware 区域化、cache-aware 全局化）。报告 cache 命中率、TTFT P50/P99 和跨区域账单。

## Ship It

本课产出 `outputs/skill-multi-region-router.md`。给定区域、驻留约束和 SLA，设计一套路由方案。

## Exercises

1. 运行 `code/main.py`。在 75 ms RTT 下，prompt 长度达到多少时跨区域路由开始优于仅本地路由？
2. 你的 cache 命中率从 70% 掉到 12%。诊断三种可能原因，以及能确认每种原因的可观测信号。
3. 为一个在 vLLM 中服务、带 5 个 LoRA adapter 的 70B AWQ 量化模型设计 DR 清单。列出每个文件和配置。
4. 论证对 TTFT SLO 严格的金融科技公司而言，Bedrock cross-region inference 是否“够用”。引用具体行为。
5. 一个来自巴黎的请求匹配到 us-east-1 的 prefix。你要路由它吗？写出策略。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Cache-aware routing | “smart LB” | 按 prefix-hash 匹配路由到持有 KV cache 的副本 |
| KV-cache events | “cache pub-sub” | 副本发布 block 添加/驱逐；router 建立索引 |
| Prefix hash | “cache key” | 用前 N 个 token 的哈希作为 router 查找键 |
| GORGO | “cross-region routing research” | arXiv 2602.11688；把网络延迟作为显式项 |
| Cross-region inference | “Bedrock CRI” | AWS 产品；可用性故障切换，不感知 TTFT |
| DR manifest | “the backup list” | 恢复所需的每个文件 —— 不只是权重 |
| Data residency | “GDPR boundary” | 关于哪个区域可以看到用户数据的法律约束 |
| RTT | “round-trip time” | 网络延迟；美欧 75 ms，美亚太 220 ms |
| LLM-aware LB | “cache-hit LB” | 作为一个产品品类的 cache-aware router |

## Further Reading

- [BentoML — Multi-cloud and cross-region inference](https://bentoml.com/llm/infrastructure-and-operations/multi-cloud-and-cross-region-inference)
- [arXiv — GORGO (2602.11688)](https://arxiv.org/html/2602.11688v1) —— 带网络延迟项的跨区域 KV-cache 复用。
- [TianPan — Multi-Region LLM Serving Cache Locality](https://tianpan.co/blog/2026-04-17-multi-region-llm-serving-data-residency-routing)
- [AWS Bedrock Cross-Region Inference](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html) —— 可用性故障切换文档。
- [vLLM Production Stack Router](https://github.com/vllm-project/production-stack) —— cache-aware router 源码。
