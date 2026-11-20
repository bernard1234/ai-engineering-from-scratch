# Prefix-Cache 服务 —— RadixAttention 与 KV 复用

> 把 KV cache 当作存放于基数树（radix tree）中的一等、可复用资源，调度策略也随之改变：vLLM 采用 FCFS（先来先服务）调度，而 cache-aware 调度器会优先处理共享前缀更长的请求 —— 实际上就是按深度优先遍历基数树，让热门分支常驻 HBM。SGLang 正是围绕这一思路构建服务引擎的引擎。在 Llama 3.1 8B 上跑类似 ShareGPT 的 1K prompt，SGLang 达到约 16,200 tok/s，vLLM 约 12,500，领先约 29%。在前缀密集的 RAG 负载上，优势可达 6.4 倍。在形态类似声音克隆的负载上，缓存命中率超过 86%。2026 年已部署在 xAI、LinkedIn、Cursor、Oracle、GCP、Azure、AWS 的 400,000+ 块 GPU 上。陷阱在于：当前缀顺序不一致时，6.4 倍这个数字会消失 —— 顺序才是工程师手里的杠杆。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级基数树缓存 + cache-aware 调度器)
**Prerequisites:** 第 17 阶段，第 04 课（Serving Engine Internals），第 14 阶段（Agentic RAG）
**Time:** ~75 分钟

## Learning Objectives

- 画出 RadixAttention：前缀如何在基数树中存储，KV 块如何在同根分支的序列之间共享。
- 解释 cache-aware 调度，以及为什么 FCFS 在前缀密集流量上是错的。
- 给定前缀缓存命中率与 prompt 长度分布，计算某负载的预期加速比。
- 说出让 6.4 倍数字从纸面收益变成现实的 prompt 顺序纪律。

## 问题场景

经典服务把每个请求的 prompt 当作不透明整体。即便 5,000 个 RAG 请求都以同样的 2,000 token 系统 prompt 加同样的检索前言开头，vLLM 仍会把这段 2,000 token 前缀 prefill 5,000 次。GPU 一遍又一遍地做同样的工作。

观察结果：agentic 与 RAG 负载中的 prompt 几乎总是共享长前缀。系统 prompt、工具 schema、few-shot 示例、检索头、对话历史 —— 都在请求间重复。如果你把这段前缀的 KV cache 存一次并复用，就不必再次 prefill。

RadixAttention 做的正是这件事。token 被索引进一棵基数树；每个节点拥有从根到其路径上的 token 序列所对应的 KV 块。新请求沿树行走：任何 token 匹配的节点都复用该节点的 KV 块。prefill 成本变得与“新增”后缀成正比，而不是整条 prompt。

挑战在于调度。如果两个请求共享 2,000 token 前缀，而第三个只共享其中 200 token，你希望把这两个长共享请求放在一起服务，让长前缀留在 HBM。FCFS 恰好相反 —— 谁先到就先服务谁，可能在下一个长前缀请求到来之前就把热门分支逐出。

## 核心概念

### 把基数树当作 KV 索引

基数树（紧凑 trie）存储 token 序列。每个节点拥有一个 token 范围和为该范围计算出的 KV 块。子节点把序列延伸一个或多个 token。

```
root
 |- "You are a helpful assistant..."  (2,000 tokens, 124 KV blocks)
      |- "Context: <doc A>..."        (500 tokens, 31 blocks)
           |- "Question: Alice..."    (80 tokens, 5 blocks)
           |- "Question: Bob..."      (95 tokens, 6 blocks)
      |- "Context: <doc B>..."        (520 tokens, 33 blocks)
```

一个新请求带着系统 prompt + “Context: <doc A>” + “Question: Carol” 进来。调度器沿树行走：系统前缀匹配（复用 124 个块），doc-A 分支匹配（复用 31 个块），然后只为“Question: Carol”分配新块（4 个块）。prefill 成本：4 个块的新 token。没有这棵树时：160 个块。prefill 节省约 40 倍。

### Cache-aware 调度

如果缓存反复抖动，基数树支撑的复用就毫无意义。两条关键策略：

1. **深度优先派发**。从队列中挑下一个请求时，优先选择与当前运行集合同根分支的请求。这样能让热门分支保持驻留。
2. **在分支级别而非块级别做 LRU**。逐出整个分支（从最少使用的叶子开始），而不是单个块，使缓存的形状与基数树的形状一致。

FCFS 两条都违反。一个共享 2,000 token 的请求排在一个只共享 50 token 的请求后面，然后为了让 50 token 的那个进来，2,000 token 的分支被逐出。

### 应该记住的基准数字

- Llama 3.1 8B、H100、ShareGPT 1K prompt：SGLang 约 16,200 tok/s，vLLM 约 12,500（领先约 29%）。
- 前缀密集的 RAG（相同系统 prompt + 相同文档，问题不同）：SGLang 最高 6.4 倍。
- 声音克隆负载：前缀缓存命中率 86.4%。
- SGLang 客户的生产命中率：50-99%，取决于 prompt 纪律。
- 2026 年部署在 400,000+ 块 GPU 上。

### 顺序陷阱

6.4 倍这个数字依赖一致的 prompt 模板顺序。如果你的客户端在部分请求中按 `[system, tools, context, history, question]` 构造 prompt，在另一些请求中按 `[system, context, tools, history, question]` 构造，树就找不到共享前缀。在人眼里看起来是共享前缀的东西，对基数树来说是两条不同的序列。

工程师的杠杆：你的 prompt 模板就是缓存键。固定顺序。把一切不可变的内容（system、tools、schema）放最前。接着放检索上下文。用户问题放最后。不要把动态内容穿插进前缀。

研究中的真实案例：把动态内容移出可缓存前缀，仅一处改动就让某次部署的缓存命中率从 7% 升到 74%。

### RadixAttention 在哪里赢、在哪里输

赢的场景：
- RAG（相同检索前言，问题不同）。
- Agent（相同工具 schema，查询不同）。
- 带长系统 prompt 的聊天。
- 带重复前言的语音 / 视觉负载。

输的场景（吞吐回落到 vLLM 水平）：
- prompt 各不相同的单次生成（代码补全、无系统 prompt 的开放式聊天）。
- 每个请求都把独有内容穿插进前缀的动态 prompt。

### 为什么这是调度器问题，而不只是内核技巧

你完全可以把 KV 复用实现成一个内核技巧。SGLang 的洞见在于：只有当调度器让热门分支保持驻留，复用才划算。朴素的“有就复用”策略在混合负载下会把缓存搅乱。正是这棵以基数树为索引的调度器，把一个内核技巧变成了 29% 的生产优势。

### 与 vLLM 的交集

这两个系统并不是严格的竞争对手。2026 年 vLLM 加入了前缀缓存（`--enable-prefix-caching`）和一个 cache-aware 路由（用 Rust 实现的 vLLM Router）。差距缩小了，但没有完全消失 —— SGLang 的整个栈是 radix 优先的，vLLM 则是把它嫁接到既有架构上。以前缀复用为主的负载，SGLang 仍是默认选择。没有强前缀模式的通用服务，vLLM 依然持平或更好。

```figure
roofline
```

## Use It

`code/main.py` 实现了一个玩具级基数树 KV 缓存，以及带两种策略的调度器：FCFS 与 cache-aware。用同一负载分别跑两种策略，报告前缀缓存命中率与吞吐差值。然后跑一个“顺序打乱”的负载，演示 6.4 倍如何崩塌。

## Ship It

本课产出 `outputs/skill-radix-scheduler-advisor.md`。给定一份负载描述（prompt 模板形态、检索模式、并发租户数量），它会产出 prompt 顺序处方，以及是否采用 SGLang 的 go/no-go 结论。

## Exercises

1. 运行 `code/main.py`。在同一负载上比较 FCFS 与 cache-aware。差值来自哪里 —— prefill 节省、decode 节省，还是排队延迟？
2. 修改负载，让 prompt 随机排列 `[system, tools, context]`。重新运行。命中率会怎样变化？为什么？
3. 在 Llama 3.1 8B 上，计算把一个 2,000 token 系统 prompt 作为单个基数树分支常驻的 HBM 成本。与不做前缀复用的 16 序列批次相比如何？
4. 阅读 SGLang 的 RadixAttention 论文。用三句话解释为什么在前缀密集负载下，树形 LRU 逐出优于块形 LRU。
5. 某客户报告缓存命中率只有 8%。说出三个可能的原因，以及你会为每个原因运行的诊断。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| RadixAttention | “SGLang 那个东西” | 把 KV cache 索引为基数树，使共享前缀复用块 |
| Radix tree | “紧凑 trie” | 每个节点拥有一个 token 范围及其 KV 块的树 |
| Cache-aware scheduler | “热分支优先” | 优先选择与常驻分支共享的请求的调度器 |
| Prefix-cache hit rate | “prompt 有多少是免费的” | prompt token 中由复用 KV 块提供服务的比例 |
| FCFS | “先来先服务” | 破坏前缀局部性的默认调度 |
| Branch-level LRU | “逐出叶子” | 与基数树形状匹配的逐出策略 |
| Prompt template ordering | “缓存键” | prompt 各组成部分的顺序决定了树能共享什么 |
| System prompt pinning | “常驻前缀” | 把不可变的系统部分固定住，避免逐出抖动 |

## Further Reading

- [SGLang GitHub](https://github.com/sgl-project/sglang) —— 源码与文档。
- [SGLang 文档](https://sgl-project.github.io/) —— RadixAttention 与调度细节。
- [SGLang 论文 —— Efficiently Programming Large Language Models（arXiv:2312.07104）](https://arxiv.org/abs/2312.07104) —— 设计参考。
- [LMSYS 博客 —— SGLang with RadixAttention](https://www.lmsys.org/blog/2024-01-17-sglang/) —— 基准数字与调度器设计理由。
- [vLLM —— Prefix Caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/) —— vLLM 自己的类 radix 实现，供对比。
