# LLM API 的负载测试——为什么 k6 和 Locust 会骗你

> 传统负载测试工具不是为流式响应、可变输出长度、token 级指标或 GPU 饱和设计的。两个陷阱会坑到大多数团队。GIL 陷阱：Locust 的 token 级测量在 Python GIL 下跑 tokenization，在高并发时与请求生成争抢；tokenization 积压随后抬高了上报的 inter-token latency——瓶颈是你的客户端，不是服务端。prompt 均一性陷阱：循环里发相同 prompt，只测到 token 分布上的一个点；真实流量的长度可变、prefix 匹配多样。LLMPerf 用 `--mean-input-tokens` + `--stddev-input-tokens` 修正了这一点。2026 年的工具格局：LLM 专用（GenAI-Perf、LLMPerf、LLM-Locust、guidellm）追求 token 级准确度；**k6 v2026.1.0** + **k6 Operator 1.0 GA（2025 年 9 月）**——流式感知、通过 TestRun/PrivateLoadZone CRD 做 Kubernetes 原生分布式，最适合 CI/CD gate；Vegeta 用于 Go 的恒定速率饱和测试；Locust 2.43.3 只有配合 LLM-Locust 扩展才支持流式。负载模式：steady-state、ramp、spike（autoscaling 测试）、soak（内存泄漏）。

**Type:** Build
**Languages:** Python (stdlib, 玩具级真实 prompt 生成器 + latency 采集器)
**Prerequisites:** 第 17 阶段，第 08 课（Inference Metrics）、第 03 课（GPU Autoscaling）
**Time:** ~75 分钟

## Learning Objectives

- 解释两个反模式（GIL 陷阱、prompt 均一性陷阱），它们让通用负载测试工具在 LLM API 上撒谎。
- 为给定目的选工具：LLMPerf（benchmark 运行）、k6 + 流式扩展（CI gate）、guidellm（大规模合成）、GenAI-Perf（NVIDIA 参考）。
- 设计四种负载模式（steady、ramp、spike、soak），并指出各自能抓到的失败模式。
- 用输入 token 的均值 + 标准差构建真实 prompt 分布，而不是固定长度。

## 问题场景

你用 k6 以 500 并发用户压测 LLM 端点。它扛住了。你上线了。生产里只有 200 个真实用户时服务却塌了——P99 TTFT 爆表，GPU 打满。

发生了两件事。第一，k6 发送的是 500 个完全相同的 prompt——你的请求合并和 prefix caching 让它看起来像是在处理 500 个并发 decode，实际上只处理了一个。第二，k6 并不会按人眼体验的方式追踪流式响应上的 inter-token latency；它看到的是一条 HTTP 连接，而不是以不同间隔到达的 500 个 token。

LLM 的负载测试自成一门学科。

## 核心概念

### GIL 陷阱（Locust）

Locust 使用 Python，并在客户端于 GIL 下跑 tokenization。高并发时 tokenizer 排在请求生成后面。上报的 inter-token latency 里包含客户端 tokenization 的积压。你以为服务端慢，其实是测试框架。

修正：LLM-Locust 扩展把 tokenization 移到独立进程，或者用编译型语言的 harness（k6、使用 tokenizers.rs 的 LLMPerf）。

### prompt 均一性陷阱

所有已知的负载测试工具都允许你配置一个 prompt。在 10,000 次迭代的循环中，每次都发送完全相同的 prompt。服务端每次都看到相同 prefix——prefix cache 命中率接近 100%，throughput 看起来很棒。

修正：从 prompt 分布中采样。LLMPerf 使用 `--mean-input-tokens 500 --stddev-input-tokens 150`——长度多样、内容多样。

### 四种负载模式

1. **Steady-state**——恒定 RPS 持续 30-60 分钟。抓：基线性能回归。
2. **Ramp**——15 分钟内把 RPS 从 0 线性升到目标。抓：容量拐点、预热异常。
3. **Spike**——RPS 突然放大 3-10 倍持续 2 分钟再回落。抓：autoscaling 延迟、队列饱和、冷启动影响。
4. **Soak**——steady-state 持续 4-8 小时。抓：内存泄漏、连接池漂移、observability 溢出。

### 2026 年的工具格局

**LLMPerf**（Anyscale）——Python 但 tokenization 由 Rust 支撑。均值/标准差 prompt。流式感知。性能测试的默认首选。

**NVIDIA GenAI-Perf**——NVIDIA 的参考实现。使用 Triton client；指标覆盖全面。注意它的 ITL 不含 TTFT；LLMPerf 的含 TTFT。两个工具对同一台服务端会给出不同的 TPOT。

**LLM-Locust**（TrueFoundry）——修复 GIL 陷阱的 Locust 扩展。熟悉的 Locust DSL + 流式指标。

**guidellm**——大规模合成 benchmark。

**k6 v2026.1.0** + **k6 Operator 1.0 GA（2025 年 9 月）**：
- k6 本身（Go，编译型，无 GIL）新增了流式感知指标。
- k6 Operator 使用 TestRun / PrivateLoadZone CRD 做 Kubernetes 原生分布式测试。
- 最适合 CI/CD gate 和 SLA 测试。

**Vegeta**——Go 编写，比 k6 简单。恒定速率的 HTTP 饱和测试。不感知 LLM，但适合 gateway / rate-limit 测试。

**Locust 2.43.3 原版**——对 LLM 有 GIL 陷阱。只有配合 LLM-Locust 扩展才可用。

### CI 中的 SLA gate

在 PR 上跑 k6：

- 在基线 RPS 下各跑 30-50 次迭代。
- Gate：P50/P95 TTFT、5xx < 5%、TPOT 低于阈值。
- 越界即中断构建。

### 真实的 prompt 分布

从真实流量样本构建（如果你有），或从公开分布构建（例如聊天用 ShareGPT prompt，代码用 HumanEval）。把均值 + 标准差喂给 LLMPerf。无论如何都要避免用单条 prompt 循环。

### 你应该记住的数字

- k6 Operator 1.0 GA：2025 年 9 月。
- k6 v2026.1.0：流式感知指标。
- 典型 LLMPerf 运行：并发 X 下 100-1000 个请求。
- 典型 CI gate：每个 PR 30-50 次迭代。
- 四种模式：steady、ramp、spike、soak。

```figure
load-pattern-waves
```

## Use It

`code/main.py` 用真实的 prompt 分布模拟负载测试，测量有效 TPOT，并演示均一 prompt 陷阱。

## Ship It

本课产出 `outputs/skill-load-test-plan.md`。给定工作负载与 SLA，选择工具并设计四种负载模式。

## Exercises

1. 运行 `code/main.py`。比较均一分布与真实分布——差距在哪里？
2. 为 CI gate 编写 k6 脚本：100 并发下 TTFT P95 < 800 ms，运行 5 分钟。
3. 你的 soak 测试显示内存每小时增长 50 MB。说出三个原因，以及用于区分它们的 instrumentation。
4. 从 10 RPS 到 100 RPS 的 spike 测试。若已部署 Karpenter + vLLM production-stack（第 17 阶段 · 03 + 18），预期恢复时间是多少？
5. GenAI-Perf 报告 TPOT=6ms；LLMPerf 在同一台服务端报告 TPOT=11ms。解释原因。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| LLMPerf | “那个 LLM harness” | Anyscale 的 benchmark 工具，流式感知 |
| GenAI-Perf | “NVIDIA 的工具” | NVIDIA 的参考 harness |
| LLM-Locust | “给 LLM 用的 Locust” | 修复 GIL 陷阱的 Locust 扩展 |
| guidellm | “合成 benchmark” | 大规模合成工具 |
| k6 Operator | “K8s 版 k6” | 基于 CRD 的分布式 k6 |
| GIL trap | “Python 客户端开销” | tokenization 积压抬高上报的 latency |
| Prompt-uniformity trap | “单 prompt 谎言” | 同一 prompt 循环命中 cache，抬高 throughput |
| Steady-state | “恒定负载” | N 分钟内 RPS 平稳 |
| Ramp | “线性爬升” | 在时长内从 0 升到目标 |
| Spike | “突发测试” | 突然放大再回落 |
| Soak | “长时测试” | 数小时以检测泄漏 |

## Further Reading

- [TianPan — Load Testing LLM Applications](https://tianpan.co/blog/2026-03-19-load-testing-llm-applications)
- [PremAI — Load Testing LLMs 2026](https://blog.premai.io/load-testing-llms-tools-metrics-realistic-traffic-simulation-2026/)
- [NVIDIA NIM — Introduction to LLM Inference Benchmarking](https://docs.nvidia.com/nim/large-language-models/1.0.0/benchmarking.html)
- [TrueFoundry — LLM-Locust](https://www.truefoundry.com/blog/llm-locust-a-tool-for-benchmarking-llm-performance)
- [LLMPerf](https://github.com/ray-project/llmperf)
- [k6 Operator](https://github.com/grafana/k6-operator)
