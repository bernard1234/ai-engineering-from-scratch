# 服务引擎内部机制 —— PagedAttention、Continuous Batching、Chunked Prefill

> 现代服务引擎的吞吐并非来自某一项技巧，而是三个相互叠加的默认特性。PagedAttention 始终开启。Continuous batching 在两次 decode 迭代之间把新请求注入活跃批次。Chunked prefill 把长 prompt 切片，使 decode token 永远不会挨饿。三者全部开启，单个 H100 SXM5 上的 Llama 3.3 70B FP8 在 128 并发下可跑到 2,200-2,400 tok/s —— 比 vLLM 自身默认值高约 25%，是朴素 PyTorch 循环的 3-4 倍。本课会拆解 vLLM（这三项技术的参考实现引擎）的调度器与注意力内核，讲到你能画出图的程度，最后以 `code/main.py` 里一个玩具级连续批处理器收尾，它按照 vLLM 的方式调度 prefill 与 decode。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级连续批处理调度器)
**Prerequisites:** 第 17 阶段，第 01 课（Model Serving），第 11 阶段（LLM Engineering）
**Time:** ~75 分钟

## Learning Objectives

- 把 PagedAttention 解释为一种 KV cache 分配器：块、块表，以及为什么在生产负载下碎片率能保持在 4% 以下。
- 在迭代级别画出 continuous batching：已完成的序列如何离开批次、新序列如何加入，而无需清空整个批次。
- 用一句话描述 chunked prefill，并指出它保护的是哪个延迟指标（提示：是 TTFT 尾部，而非平均吞吐）。
- 在一次性开启所有优化之前，先对照你所使用版本的兼容性矩阵检查 vLLM 的特性组合。

## 问题场景

朴素的 PyTorch 服务循环一次只跑一个请求：tokenize、prefill、decode 直到 EOS、返回。只有一个用户时这没问题。到一百个用户，它就变成了一队耐心等待的人。显而易见的修法是静态批处理（static batching）：把每个请求补齐到窗口内最长的 prompt，把每次 decode 补齐到预期最长的输出，并让整个批次卡在最慢的序列上。你为永远用不到的 padding 付费，而快请求还要等慢请求。

vLLM 一次解决三个问题。PagedAttention 阻止 KV cache 碎片像传统连续分配那样吃掉 60-80% 的 GPU 内存。Continuous batching 让请求在每次 decode 迭代之间加入和离开批次，因此批次里始终装满了真实的工作。Chunked prefill 把 32k token 的 prompt 拆成约 512 token 的切片，与 decode 交错执行，因此一个长 prompt 不会把 GPU 上所有 decode token 都冻住。

2026 年的生产默认是三者全开。你需要理解每一项各自做什么，因为故障模式全都出在调度器上，而不是模型上。

## 核心概念

### 把 PagedAttention 当作虚拟内存系统

每个序列的 KV cache 为 `num_layers × 2 × num_heads × head_dim × seq_len × bytes_per_element`。对 8192 token 的 Llama 3.3 70B，BF16 下每个序列约占 1.25 GB。如果你为每个请求预保留 8192 个槽位，而平均请求只用到 1500 个 token，你就浪费了所保留 HBM 的约 82%。传统批处理支付的正是这种浪费。

PagedAttention 借用了操作系统虚拟内存的思路。KV cache 对每个序列都不再是连续的，而是按固定大小的块分配（默认 16 个 token）。每个序列有一张块表，把它逻辑上的 token 位置映射到物理块 ID。当序列增长超出已分配的块时，就再增加一个块。序列结束时，它的块回到池中。

碎片率从 60-80%（传统方式）降到 4% 以下（PagedAttention）。你不需要用开关来启用 PagedAttention —— 它是 vLLM 唯一提供的分配器。可调的是 `--gpu-memory-utilization`（默认 0.9），它告诉 vLLM 在加载权重和激活之后预留多少 HBM 给 KV 块。

### 迭代级别的 Continuous Batching

旧的“动态批处理”会等待一个窗口（比如 10 ms）来凑满一个批次，然后连续跑 prefill + decode + decode + decode，直到所有序列完成。快序列早早结束、空转等待，GPU 则在把慢的序列跑完。

Continuous batching 在每次 decode 步之间进行调度。我们把正在运行的序列集合称作 `RUNNING` 列表。每次迭代：

1. `RUNNING` 中刚命中 EOS 或 max_tokens 的序列被移除。
2. 调度器查看等待队列。如果有空闲的 KV 块，就接纳新序列（prefill 或恢复）。
3. 前向计算作用于此刻 `RUNNING` 中的所有序列，每个序列产出一个新 token。

批大小永远不会被补齐到固定数字。处于输出不同位置的序列共享一次融合的前向计算。在 2026 年的 vLLM 中，这被称为 `V1 scheduler`。关键不变量：调度器每次 decode 迭代运行一次，而不是每个请求运行一次。

### Chunked Prefill 保护 TTFT 尾部

Prefill 是计算受限的。在单个 H100 上，Llama 3.3 70B 处理 32k token 的 prompt 需要约 800 ms 的纯 prefill。prefill 运行期间，批次中其他所有序列的 decode token 都在等待。在服务循环里，一个长 prompt 的首 token 延迟（TTFT）会变成几十个其他用户的 token 间隔延迟（ITL）尖峰。

Chunked prefill 把 prefill 拆成固定大小的块（默认 512 个 token），并以块为单位调度。块与块之间，调度器可以让 decode 序列前进一个 token。你用一点点绝对的 prefill 延迟代价（每块几毫秒）换来低得多的 decode 抖动。在公开基准中，混合负载下的 P99 ITL 从约 50 ms 降到约 15 ms。

### 三个默认特性相互作用

这三个特性相互依赖。PagedAttention 给调度器提供了可权衡的细粒度 KV 资源。Continuous batching 需要这种细粒度资源，这样接纳一个新序列才不会引发全局重排。Chunked prefill 是调度器在同一个 `RUNNING` 列表上做出的决策 —— 它是又一条调度策略，而不是一个独立的系统。

你不需要记住每一个开关。你需要知道调度器在优化什么：在 KV 块预算约束下的 goodput，并受 chunked prefill 切片的约束。

### 检查兼容性矩阵

在一次性开启所有特性之前，先对照你的确切 vLLM 版本检查每一种特性组合，因为哪些能组合会随版本变化。在 v0.18.0 中，特性矩阵把 speculative decoding 标记为与 chunked prefill 和 prefix caching 兼容，而 speculative decoding 页面列出了两项已知不兼容：v0.15.0 及之前的 pipeline parallelism，以及 v0.10.0 及之前的 draft-model speculation。至于 draft 方法本身，2026 年的默认通常是 EAGLE-3（`"method": "eagle3"`），在第 17 阶段 · 05 中讲解。

### 应该记住的数字

- Llama 3.3 70B FP8、H100 SXM5、128 并发、三者全开：2,200-2,400 tok/s。
- 同一模型，vLLM 默认配置（无 chunked prefill）：约 1,800 tok/s。
- 同一模型，朴素 PyTorch 前向循环：约 600 tok/s。
- 生产负载下 PagedAttention 的 KV 碎片浪费：<4%。
- 混合负载下的 P99 ITL：启用 chunked prefill 约 15 ms，不启用约 50 ms。

### 调度器的样子

```
while True:
    finished = [s for s in RUNNING if s.is_done()]
    for s in finished: release_blocks(s); RUNNING.remove(s)

    while WAITING and have_free_blocks_for(WAITING[0]):
        s = WAITING.pop(0)
        allocate_initial_blocks(s)
        RUNNING.append(s)

    # schedule prefill chunks + decode in one batch
    batch = []
    for s in RUNNING:
        if s.in_prefill:
            batch.append(next_prefill_chunk(s))   # e.g. 512 tokens
        else:
            batch.append(decode_one_token(s))     # 1 token

    run_forward(batch)                            # one fused GPU call
```

`code/main.py` 就是这段循环，用标准库 Python 写成，token 数量和前向延迟都是模拟的。运行它可以看到 chunked prefill 如何在长 prefill 期间让 decode 序列保持存活。

```figure
tensor-parallel
```

## Use It

`code/main.py` 模拟一个 vLLM 风格的调度器，特性可以开关。运行后可以看到：

- `NAIVE` 模式：一次一个请求，无批处理。
- `STATIC` 模式：补齐并等待，传统批处理。
- `CONTINUOUS` 模式：迭代级别的准入与释放。
- `CONTINUOUS + CHUNKED` 模式：prefill 切片与 decode 交错执行。

输出会显示总吞吐（每虚拟秒的 token 数）、TTFT 均值以及 P99 ITL。在混合流量下，`CONTINUOUS + CHUNKED` 那一行应当全面领先。

## Ship It

本课产出 `outputs/skill-vllm-scheduler-reader.md`。给定一份服务配置（batch size、KV 内存利用率、chunked prefill 大小、speculative 配置），它会产出调度器诊断，指出三个默认特性中哪一个成了瓶颈，以及该调什么。

## Exercises

1. 运行 `code/main.py`。在长短请求混合的负载上比较 `STATIC` 与 `CONTINUOUS`。吞吐差距来自哪里 —— prefill 效率、decode 效率，还是尾部延迟？
2. 修改玩具调度器，加入 `--max-num-batched-tokens`。在跑 Llama 3.3 70B FP8 的 H100 上，合适的取值是多少？（提示：它是 KV 块大小和空闲块数量的函数，而非裸 HBM。）
3. 重读 vLLM v0.18.0 的发布说明。哪些开关组合互斥？把它们列出来。
4. 对一条包含 1,000 个请求的 trace（输出 token 均值 1,500、标准差 600），分别计算 (a) 按每请求 8192 上限连续分配、(b) 使用 16 token 块的 PagedAttention 两种情况下的 KV cache 碎片浪费。
5. 用一段话解释为什么 chunked prefill 能改善 P99 ITL，但单独使用时并不改善吞吐。实践中的吞吐收益来自哪里？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| PagedAttention | “KV 那个技巧” | KV cache 的固定大小块分配器；碎片率 <4% |
| Block table | “页表” | 每个序列从逻辑 token 位置到物理 KV 块的映射 |
| Continuous batching | “更聪明的动态批处理” | 每次 decode 迭代都做一次准入/释放决策 |
| Chunked prefill | “prefill 切分” | 把长 prefill 切成 512 token 的片，与 decode 交错执行 |
| TTFT | “首 token 时间” | prefill + 排队 + 网络；长 prompt 下由 prefill 主导 |
| ITL | “token 间隔延迟” | 相邻 decode token 之间的时间；由 batch size 主导 |
| Goodput | “满足 SLO 的吞吐” | 每个请求仍满足 TTFT 与 ITL 目标时的 token/秒 |
| V1 scheduler | “新调度器” | vLLM 2026 的调度器；以 chunked prefill 运行 continuous batching |
| `--gpu-memory-utilization` | “内存旋钮” | 加载权重和激活后，预留给 KV 块的 HBM 比例 |

## Further Reading

- [vLLM 文档 —— Speculative Decoding](https://docs.vllm.ai/en/latest/features/spec_decode/) —— 关于 chunked prefill 与 speculative decoding 兼容性的官方来源。
- [vLLM 发布说明（NVIDIA）](https://docs.nvidia.com/deeplearning/frameworks/vllm-release-notes/index.html) —— 2026 年的发布节奏及版本相关行为。
- [vLLM 博客 —— PagedAttention](https://blog.vllm.ai/2023/06/20/vllm.html) —— 最早的那篇文章，至今仍定义了如何看待这个分配器。
- [PagedAttention 论文（arXiv:2309.06180）](https://arxiv.org/abs/2309.06180) —— 碎片分析与调度器设计。
- [Aleksa Gordic —— Inside vLLM](https://www.aleksagordic.com/blog/vllm) —— 详细的 V1 调度器讲解，附火焰图。
