# 异步与 Hogwild! 推理

> Speculative decoding（Phase 10 · 15）在单个序列内部并行化 token。多 agent 框架跨整个序列并行，但强制要求显式的协调（投票、子任务切分）。Hogwild! 推理（Rodionov 等，arXiv:2504.06261）做的是另一件事：让同一个 LLM 的 N 个实例并行地跑在一个**共享**的 key-value cache 上。每个 worker 都能立刻看到其他每个 worker 生成的 token。现代推理模型——QwQ、DeepSeek-R1——可以在没有任何微调的情况下通过这个共享 cache 自我协调。这条路线是实验性的，但它开辟了一个与 spec decode 正交的全新推理并行轴。本课用 stdlib Python 实现一个双 worker 的 Hogwild! 模拟器，并解释为什么这种共享 cache 协作会从现有模型的推理能力中自然涌现。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 10 · 12 (inference optimization), Phase 10 · 15 (speculative decoding)
**Time:** ~60 分钟

## Learning Objectives

- 描述三种常见的并行 LLM 拓扑（投票、子任务、Hogwild!），并指出每一种针对的问题。
- 说出 Hogwild! 的核心设置：多个 worker、一个共享 KV cache、通过自我提示涌现出的协调。
- 把 Hogwild! 的墙钟加速比表达为 worker 数量 `N`、任务级并行度 `p` 与协调开销 `c` 的函数并计算它。
- 在一个玩具问题上实现双 worker 的 Hogwild! 模拟器，并观察涌现出的任务分工。

## 问题场景

现代 LLM 通过产生很长的推理链来解决难题——5000 token 的逐步逻辑是常见的，在深度数学问题上出现数万 token 也不稀奇。在 70B 模型上以 35 token/秒解码，50k token 就是 24 分钟。这谈不上交互性。

Speculative decoding（Phase 10 · 15）通过在单个序列内部并行化，能带来 3-5 倍的加速。再往上，自回归解码的顺序依赖就是硬天花板。每个新 token 都依赖此前每一个 token。

显而易见的问题：我们能否跨序列并行？在同一个问题上跑同一模型的多个副本，让它们协作、让它们分工？

先前的工作有：投票集成（跑 N 个模型，取多数答案）、树思维（branch-and-recombine 推理路径）以及多 agent 框架（给每个 agent 分配一个子任务，再用一个协调者）。这些在特定任务领域都有帮助。它们也都会引入显式的协调机制——投票规则、分支剪枝逻辑、agent 间消息协议。

Hogwild! 推理走的是另一条路。N 个 worker 共享一个 KV cache。每个 worker 都能立刻看到其他每个 worker 生成的 token，就像那是它自己的上下文一样。这些 worker——没有经过任何训练或微调——自己琢磨出如何分工。现代推理模型（QwQ、DeepSeek-R1、Claude 家族的推理模式）能读共享 cache，并说出类似“我看到 worker 2 已经处理了基本情况，那我来做归纳步”这样的话。

加速比取决于工作负载，截至 2026 年 4 月仍是实验性的。但这个想法值得了解，因为它开辟了一个新的推理并行轴。

## 核心概念

### 设置

初始化 N 个 worker 进程，都运行同一个 LLM。不是每 worker 一个 KV cache，而是维护**一个**共享 cache。当 worker `i` 生成 token `t_j` 时，该 token 被写入共享 cache 的下一个位置。当 worker `k` 走下一步时，它读取 cache 的当前状态（其中包含全部 N 个 worker 到目前为止生成的一切）。

在每个 step 时刻，worker 们竞争写入 token。没有逐 worker 的位置索引——cache 是一个单一的增长序列。顺序由写入到达的时间决定。

### 为什么协调会涌现

这些 worker 共享一个提示词。通常类似“你是共同解决这个问题的 N 个实例之一。每个实例读取共享内存，可以看到其他实例写了什么。避免重复劳动。”提示词加上共享 cache 就足够了。推理模型读取 cache，注意到问题的哪些部分已经被尝试过，并（通常但不总是）转向尚未探索的部分。

Hogwild! 论文（Rodionov 等，2025）报告了这样的观察：

- worker 会制定计划并通过 cache 与其他 worker 沟通。
- worker 会注意到其他 worker 推理中的错误并把它们指出来。
- 当某个计划失败时，worker 会调整并给出替代方案。
- 当被提示检查冗余时，worker 会检测到冗余并转向。

这一切都不需要微调。涌现行为来自模型本就具备的推理能力。

### 命名的由来

论文的名字戏仿了 Hogwild! SGD（Recht 等，2011），一个异步更新的优化器。类比是：SGD 的异步 worker 都写入一个共享参数向量；Hogwild! 推理的 worker 都写入一个共享 KV cache。两者都依赖经验上的收敛，而不是同步保证。

### RoPE 让这件事可行

旋转位置嵌入（RoPE，Su 等 2021）通过 Q 和 K 向量中的旋转来编码位置信息。由于位置是旋转而不是烘死的偏移量，一个 token 的位置可以移动而不必重新计算 KV cache 条目。当 worker `i` 在位置 `p` 写入共享 cache 时，读取该位置的其他 worker 可以直接使用缓存条目——无需重新旋转。

在学习位置或绝对位置的模型中，Hogwild! 需要在每次并发写入时做 cache 失效。RoPE 让 cache 保持稳定。

### 墙钟时间数学

设 `T_serial` 为一个 worker 独自解决该问题的时间。设 `p` 为任务级可并行的比例。设 `c` 为每步的协调开销（读取被扩展的 cache、决定写什么）。

单 worker 时间：`T_serial`。
若协调免费，N-worker Hogwild! 时间：`T_serial * ((1 - p) + p / N)`。这是经典的 Amdahl。
带上协调开销：`T_serial * ((1 - p) + p / N) + c * steps_per_worker`。

要让一个 worker 有产出，`c` 必须相对每步解码时间足够小。在生成 5k+ token 的推理模型上，worker 能承受数百个 token 的协调开销而仍然划得来。在短聊任务上，协调占据主导，Hogwild! 比串行更差。

### 具体例子

推理问题：10k token 的思维链。假设该问题有 `p = 0.7` 的可并行内容（不同的证明策略、不同的情况分析），每个 worker 的协调开销为 `c = 200` token。取 `N = 4` 个 worker：

- 串行时间：10000 个解码步。
- Hogwild! 时间：10000 * (0.3 + 0.7 / 4) + 200 * 4 = 10000 * 0.475 + 800 = 5550 个解码步。
- 加速比：10000 / 5550 = 1.8x。

这有点保守。但在更长的推理问题（50k token）上，协调开销被摊薄，加速比会推到 2.5-3x。Hogwild! 之于推理，相当于那种让你能自然地写多线程代码的语言里的线程级并行。

### 何时应当选择 Hogwild!

- 长推理问题（数千 token），且任务可以跨独立的子目标并行化。
- 已被训练成逐步思考的推理模型。非推理模型无法很好地自我协调。
- 单节点部署，VRAM 足以容纳共享 cache 加上 N 个 worker 进程。cache 是共享的，但每个 worker 有自己的 activation 显存。

### 何时不要用

- 简短的交互式聊天。协调开销占主导。
- 无法并行化的任务（单一线性证明、单次编译）。N=1 就是上限。
- 非推理模型。不会涌现出协调。
- 多节点部署。共享 cache 需要非常快的跨 worker 同步。节点内没问题；跨节点是延迟灾难。

### 实验状态

截至 2026 年 4 月，Hogwild! 是一种研究方法，有开源的 PyTorch 实现。尚未发生生产采用。三个障碍：

1. 跨并发进程的共享 KV cache 管理是相当棘手的工程。
2. 涌现的协调依赖任务；benchmark 仍在建设中。
3. 与 speculative decoding 已经交付的相比，加速比偏保守，两者可以组合，但组合后的工程又是另一层。

值得了解。值得实验。还不值得拿产品去赌。

```figure
continuous-batching
```

## Build It

`code/main.py` 实现了一个玩具版的 Hogwild! 模拟器：

- 两个 worker 进程，每个都是一个确定性的“LLM”，以已知概率产出若干 token 类别之一（work-token、observe-token、coordinate-token）。
- 一个共享 cache（就是一个 token 列表），两个 worker 都读写它。
- 一套简单的协调逻辑：当一个 worker 看到另一个已在某个类别产出了足够多的 work token，它就换一个类别。

模拟器运行固定的步数预算，并报告：

- 产出的 work-token 总数。
- 总墙钟时间（worker 步数）。
- 相对单 worker 的有效加速比。
- 哪个 worker 写了哪个 token 的轨迹。

### 第 1 步：共享缓存

一个两个 worker 都追加的列表。在真实实现中要用简单锁（Python 的 `threading.Lock`）；我们用计数器模拟。

### 第 2 步：worker 循环

每个 worker 在每一步：

- 读取当前的共享 cache。
- 根据已经存在的内容决定要写哪一类 token。
- 写入一个 token。

### 第 3 步：协调启发式

如果类别 X 在 cache 中已经有 K 个 token，而 worker 原本打算写类别 X，那它就切换到类别 Y。这是对推理模型行为“注意到这件事已被覆盖，改做别的”的玩具替身。

### 第 4 步：实测加速比

用 N=1 个 worker 和 N=2 个 worker 运行模拟器，总步数预算相同。统计产出的 work-token。由于协调驱动的任务分工，N=2 产生的 work-token 应约为 1.5-1.8 倍。

### 第 5 步：给协调加压

降低协调启发式的敏感度。再跑一次。观察在没有良好协调的情况下，N=2 冗余地产生相同的 token，加速比跌到 1 以下。这与论文的观察一致：只有当 worker 具备自我协调的推理能力时，这个技巧才奏效。

## Use It

截至 2026 年 4 月，Hogwild! 在生产中的集成仍是研究级的。Yandex/HSE/IST 的参考实现基于 PyTorch，面向 DeepSeek-R1 和 QwQ 模型的单节点多进程部署。

务实的采用路径：

1. 剖析你的推理任务工作负载。测量探索性 token（多种策略、情况分析、搜索）与线性 token 的比例。
2. 如果探索占主导，跑一个双 worker 的 Hogwild! 实验。测量墙钟时间的改善。
3. 如果改善低于 1.3x，你处在协调主导的区间。回退到单 worker。
4. 如果改善超过 1.5x，推到 N=4 再测。收益递减通常在 N=4-8 附近出现。

与 speculative decoding 组合：每个 Hogwild! worker 可以独立使用 spec decode。两个加速比（大致）相乘，让 3x 的 spec decode 与 1.8x 的 Hogwild! 组合成相对朴素单 worker 解码的有效 5.4x。

## Ship It

本课产出 `outputs/skill-parallel-inference-router.md`。给定一份推理工作负载画像（token 预算、任务并行画像、模型家族、部署目标），它在投票、树思维、多 agent、Hogwild! 以及 speculative decoding 策略之间做路由。

## Exercises

1. 用默认设置运行 `code/main.py`。确认 N=2 的 Hogwild! 配置在相同墙钟时间内比 N=1 基线产出更多 work-token。

2. 降低协调启发式的强度（设置 `coordination_weight=0.1`）。重新运行。显示加速比崩溃。解释原因：当 worker 无法协调时，它们会重复劳动。

3. 计算一个 50k token 推理任务在 `p=0.8, c=500`、N=4 个 worker 下的预期 Hogwild! 加速比。对一个 1k token 聊天任务在 `p=0.3, c=200`、N=4 下做同样的计算。为什么一个是赢，另一个是亏？

4. 阅读 Hogwild! 论文的 Section 4（初步评估）。找出作者报告的两个失败模式。描述一个更好的协调提示词可能如何缓解每一个。

5. 在玩具中把 Hogwild! 与 speculative decoding 组合：每个 worker 内部使用 2-token 的 spec-decode。报告乘性加速比。当两个 worker 都想扩展同一个共享 cache 前缀时，会出现什么记账问题？

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Hogwild! | “并行 worker，共享 cache” | 同一个 LLM 的 N 个实例在一个共享 KV cache 上并发运行；通过自我提示涌现协调 |
| Shared KV cache | “协调媒介” | 一个所有 worker 都读写的单一增长 KV 缓冲区；让 token 在 worker 间立即可见 |
| Emergent coordination | “不需要训练” | 具备推理能力的 LLM 可以读取共享 cache 并分工，无需任何微调或显式协议 |
| Coordination overhead (c) | “用来定位自己的 token” | 每个 worker 读取被扩展的 cache 并决定做什么的花费；相对总解码时间必须保持足够小 |
| Parallelizable fraction (p) | “哪些可以并行跑” | 任务级并行度：总工作量中并非本质串行的比例 |
| RoPE enables Hogwild! | “旋转位置是平移不变的” | 因为位置是旋转，写入共享 cache 不需要重新计算此前的 token |
| Voting ensemble | “跑 N 个，取多数” | 最简单的并行推理拓扑；适合分类，对长文本推理不太有用 |
| Tree of thought | “分支并剪枝” | 探索多条分支并剪枝的推理策略；显式的协调逻辑 |
| Multi-agent framework | “分配子任务” | 每个 agent 获得一个角色；一个协调者来统筹；协议开销沉重 |

## Further Reading

- [Rodionov et al. — Hogwild! Inference: Parallel LLM Generation via Concurrent Attention (arXiv:2504.06261)](https://arxiv.org/abs/2504.06261) —— Hogwild! 论文，在 QwQ 与 DeepSeek-R1 上的初步评估
- [Recht, Re, Wright, Niu — Hogwild!: A Lock-Free Approach to Parallelizing Stochastic Gradient Descent (arXiv:1106.5730, NeurIPS 2011)](https://arxiv.org/abs/1106.5730) —— 最初的 Hogwild!，命名来源
- [Su et al. — RoFormer: Enhanced Transformer with Rotary Position Embedding (arXiv:2104.09864)](https://arxiv.org/abs/2104.09864) —— RoPE，使共享 cache 推理可行的那个性质
- [Yao et al. — Tree of Thoughts: Deliberate Problem Solving with Large Language Models (arXiv:2305.10601)](https://arxiv.org/abs/2305.10601) —— 与 Hogwild! 正交的树思维推理策略
- [Leviathan et al. — Fast Inference from Transformers via Speculative Decoding (arXiv:2211.17192)](https://arxiv.org/abs/2211.17192) —— speculative decoding，与 Hogwild! 组合的序列内并行
- [Hogwild! reference PyTorch implementation](https://github.com/eqimp/hogwild_llm) —— 论文实验的唯一权威来源
