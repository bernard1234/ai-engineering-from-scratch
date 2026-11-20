# DualPipe 并行

> DeepSeek-V3 在 2,048 张 H800 GPU 上训练，MoE 专家散布在多个节点之间。跨节点专家 all-to-all 通信每消耗 1 GPU 小时的计算，就要配上 1 GPU 小时的通信。GPU 有一半时间在空转。DualPipe（DeepSeek，2024 年 12 月）是一种双向 pipeline，把前向与反向计算与它们触发的 all-to-all 通信重叠起来。bubble 缩小，吞吐上升，而保存两份模型参数副本（这正是“dual”这个名字的来源）的开销，在 Expert Parallelism 本就把专家分散到各个 rank 的情况下其实很便宜。本课是一篇 Learn 类型的讲解，说明 DualPipe 实际做了什么，以及为什么 Sea AI Lab 的 DualPipeV 改进以略显紧张的 bubble 为代价，去掉了 2 倍的参数开销。

**Type:** Learn
**Languages:** Python (stdlib, schedule simulator)
**Prerequisites:** Phase 10 · 05 (distributed training, FSDP, DeepSpeed), Phase 10 · 14 (open-model architectures and MoE)
**Time:** ~60 分钟

## Learning Objectives

- 说出 DualPipe 一个前向-反向 chunk 的四个组成部分，以及为什么每一部分都有自己的重叠窗口。
- 解释大规模下的 pipeline bubble 问题，以及“bubble-free”在实践中和在宣传中分别意味着什么。
- 为 8 个 PP rank 和 16 个 micro-batch 手工推演一份 DualPipe 调度表，并确认前向流与反向流彼此填满了对方的空闲时段。
- 说出 DualPipeV（Sea AI Lab，2025）做出的权衡：在 Expert Parallelism 不活跃时，它以略大的 bubble 为代价去掉了 2 倍的参数复制。

## 问题场景

在 2k 张 H800 GPU 上训练一个 671B 的 MoE 模型，会撞上三个相互叠加的瓶颈：

1. **显存压力。** 每张 GPU 持有模型的一个切片。序列长度 8k、61 层、128 个 head 的 activation 显存是巨大的。
2. **pipeline bubble。** 传统的 pipeline parallelism（GPipe、1F1B）在等待自己阶段的输入或梯度时让 GPU 空转。在 8 个阶段下，即使采用 1F1B 调度，大约 12% 的 GPU 时间也可能是 bubble。
3. **跨节点 all-to-all。** 带 expert parallelism 的 MoE 把专家分散到各节点。每一次前向都会触发一次 all-to-all 把 token 分发给对应的专家，再来一次把结果组合起来。在 2k GPU 的规模下，这很容易变成 1:1 的计算通信比。

这三者各有独立的解法：显存问题用 gradient checkpointing，pipeline bubble 用 Zero Bubble（Sea AI Lab，2023），all-to-all 用 expert-parallel 通信 kernel。DualPipe 做的是让它们协同起来。该调度在单个前向-反向 chunk 内部重叠计算与通信，同时从 pipeline 两端注入 micro-batch，并利用由此得到的调度把 all-to-all 藏在计算窗口里。

论文报告的结果：pipeline bubble 近乎消除，DeepSeek-V3 的 14.8T token 训练过程中 GPU 利用率超过 95%。

## 核心概念

### pipeline parallelism 回顾

把一个 N 层的模型切分到 P 个设备上。设备 `i` 持有第 `i * N/P .. (i+1) * N/P - 1` 层。一个 micro-batch 向前流过设备 0 到 P-1，再从 P-1 反向流回 0。每个设备只有在上一个设备送来它的输出之后才能开始自己的前向阶段，只有在下游设备送来上游梯度之后才能开始反向。

GPipe（Huang 等，2019）一次只调度一个 micro-batch，浪费了大部分 GPU 时间。1F1B（Narayanan 等，2021）为多个 micro-batch 交错安排前向与反向。Zero Bubble（Qi 等，2023）把反向拆成两部分——对输入的求导（B）和对权重的求导（W）——并调度它们来填充 bubble。经过 Zero Bubble 之后，pipeline 已经相当紧凑了。

DualPipe 是下一步。它在此之上加了两点想法：

### 思路一：chunk 分解

每个前向 chunk 被拆成四个组成部分：

- **Attention。** Q/K/V 投影、attention、输出投影。
- **All-to-all dispatch。** 把 token 发送给对应专家的跨节点通信。
- **MLP。** MoE 专家计算。
- **All-to-all combine。** 把专家输出带回来的跨节点通信。

一个反向 chunk 则为上述每一项加上对应的梯度版本。DualPipe 这样调度它们：all-to-all dispatch 与下一个 chunk 的 attention 计算并行发生，all-to-all combine 与再下一个 chunk 的 MLP 计算并行发生。

### 思路二：双向调度

大多数 pipeline 调度从 stage 0 注入 micro-batch，并向 stage P-1 流动。DualPipe 从**两端**同时注入 micro-batch。stage 0 看到从它这里出发的前向 micro-batch；stage P-1 也看到从它这里出发的前向 micro-batch。两股流在中间相遇。

要让这一点成立，设备 `i` 必须同时持有 pipeline 靠前的第 `i` 层**和**靠后的第 `P - 1 - i` 层。这就是 DualPipe 中“dual”的部分：每个设备为它需要服务的模型层保存两份副本（每个方向各一份）。在 DeepSeek-V3 的规模下，这是 2 倍的参数复制开销。它能被接受，是因为 Expert Parallelism 已经把 MoE 专家摊得如此之薄，把非专家层复制两份只是小菜一碟。

关键在于，一个方向上的前向流与另一个方向上的反向流，正好在原单向调度会出现 bubble 的地方重叠。bubble 就消失了。

### 手工推演一份调度表

考虑 P = 4 个 rank、8 个 micro-batch，分为 4 个前向 / 4 个反向。时间从左向右推进；每一行是一个设备 rank。

```
           Time →
rank 0:  F1 F2 F3 F4  F5R F6R F7R F8R  B1 B2 B3 B4  ...
rank 1:     F1 F2 F3  F4/F5R F6R F7R   B1 B2 ...
rank 2:        F1 F2  F3/F5R F4/F6R    B1 ...
rank 3:           F1  F2/F5R F3/F6R    ...
```

读一下“F4/F5R”这个记号：rank 1 在同一个时间片里，既在跑 micro-batch 4 的前向（在 pipeline 中自左向右流），又在跑 micro-batch 5 的前向（自右向左流）。这就是“双向”在操作层面的含义。

在 rank 2 上交叉流重叠得更早，在 rank 0 和 P-1 上重叠得最晚。在调度的稳定中段，每个 rank 都在跑 X 方向的前向，同时与 Y 方向的反向重叠。计算资源是忙碌的。前向需要的 all-to-all dispatch 藏在反向计算里。all-to-all combine 藏在前向计算里。bubble 被挤了出去。

### bubble 核算

标准 1F1B 的 pipeline bubble（每个 rank 浪费的时间）：

```
bubble_1F1B = (P - 1) * forward_chunk_time
```

Zero Bubble 的改进把它压低了，但没有降到零。DualPipe 在稳定阶段，如果 micro-batch 数量能被 pipeline 深度的两倍整除，bubble 就是零。在稳定阶段之外（预热与收尾），会有一些 bubble，但它不会随 micro-batch 数量的增加而增长——这是论文着重强调的一个关键性质。

用宣传口径说：“bubble-free”。用技术口径说：bubble 不随 micro-batch 数量增长。Sea AI Lab 的后续分析（DualPipeV / Cut-in-half）表明，只有在 Expert Parallelism 不是瓶颈时才能实现完整的零 bubble；在由 EP 驱动的 all-to-all 场景下，总会有一些调度上的妥协。

### DualPipeV —— 改进版

Sea AI Lab（2025）观察到，当 EP 通信重叠不是重点时，2 倍的参数复制是浪费的。他们的 DualPipeV 调度把双向注入折叠成一种“V 形”调度，运行在单份参数副本上。bubble 比 DualPipe 略大，但显存节省相当可观。DeepSeek 在他们的开源 DualPipe 实现中把 DualPipeV 采纳为 EP 关闭模式。

权衡如下：

| 特性 | DualPipe | DualPipeV | 1F1B | Zero Bubble |
|---------|---------|-----------|------|------------|
| 每设备参数副本数 | 2 | 1 | 1 | 1 |
| bubble 随 micro-batch 的变化 | 恒定 | 小幅增长 | 增长 | 增长 |
| 计算-通信重叠 | 完整 | 部分 | 极少 | 部分 |
| 适用场景 | EP 密集的 MoE | 稠密或 EP 较轻 | 基线 | 任意 pipeline |

### 对一次 14.8T token 训练意味着什么

DeepSeek-V3 的预训练在 2,048 张 H800 GPU 上消耗了 14.8T token，大约 2.8M GPU 小时。如果用朴素的 1F1B，其中 12-15% 会损失在 pipeline bubble 上——340-420K GPU 小时，足够训练一个完整的 70B 模型。DualPipe 把这部分大部分收了回来。在没有内部日志的情况下很难直接量化它的贡献，但论文的论断是整个训练平均 GPU 利用率超过 95%。

对较小的训练（1k GPU 以下），DualPipe 是过度设计——pipeline bubble 相对总成本更小，而且稠密模型训练很少撞上 all-to-all 瓶颈。对数千 GPU 规模的前沿 MoE 训练，它实际上是必需的。

### 它在技术栈中的位置

- 与 **FSDP**（Phase 10 · 05）互补。FSDP 把模型参数分片到各 rank；DualPipe 把计算调度到各 rank。两者可以组合。
- 兼容 **ZeRO-3** 的梯度分片。两份副本的记账工作需要与 ZeRO 的分片梯度配合。
- 需要针对特定集群拓扑调优的**自定义 all-to-all kernel**。DeepSeek 的开源 kernel 是参考实现。

```figure
expert-capacity
```

## Use It

`code/main.py` 是一个 pipeline 调度模拟器。它接收 `(P, n_micro_batches, schedule)`，打印 1F1B、Zero Bubble、DualPipe 和 DualPipeV 各自的稳定阶段利用率。它是一个教学工具——这些数字与论文中的定性结论相符，但它们并不构成对生产实测加速比的宣称。

这个模拟器的价值在于：用不同的 P 和 micro-batch 数量运行它，观察 1F1B 的 bubble 占比如何增长，而 DualPipe 的不会。

真实训练任务的集成考虑：

- 选择一个能干净整除你的 micro-batch 数量的 pipeline-parallel 深度。
- 确保你的 expert-parallel mesh 支持双向 all-to-all。DeepSeek 的 kernel 是参考实现。
- 第一次做时，预计要在调度本身烧掉一周的调试时间。记账非常琐碎。
- 监控每个 rank 的 GPU 利用率，而不只是总量。DualPipe 的收益来自收紧那些拖后腿的 rank。

## Ship It

本课产出 `outputs/skill-dualpipe-planner.md`。给定一份训练集群规格（GPU 数量、拓扑、互联、模型形状），它会推荐一种 pipeline parallelism 策略、应使用的调度算法，以及目标规模下的预期 bubble 占比。

## Exercises

1. 在 `(P=8, micro_batches=16, schedule=dualpipe)` 和 `(P=8, micro_batches=16, schedule=1f1b)` 上运行 `code/main.py`。计算 GPU 利用率的差值，并把它表达为每百万 token 训练回收的 GPU 小时数。

2. 手工画出 `(P=4, micro_batches=8, schedule=dualpipe)` 的调度表。在每个时间片上标注 micro-batch ID 和方向。找出第一个没有 bubble 的时间片。

3. 阅读 DeepSeek-V3 技术报告（arXiv:2412.19437）的 Figure 5。找出 DualPipe 前向 chunk 内部 all-to-all dispatch 的重叠窗口。解释计算调度如何把它隐藏起来。

4. 计算 DualPipe 的 2 倍参数开销：一个是 P=8 个 pipeline 阶段的 70B 稠密模型，另一个是 P=16 个 pipeline 阶段的 671B MoE 模型。说明为什么 MoE 情形的开销比例上更小（大部分参数是专家，分散在一个大的 EP 组上）。

5. 把 DualPipe 与 Chimera（2021 年的一个竞争性双向调度器）做比较。以论文的 Section 3.4 为参考，指出 DualPipe 新增而 Chimera 不具备的两个具体性质。

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Pipeline bubble | “每个 rank 的空闲时间” | 因为 pipeline 某个阶段在等待输入或梯度而浪费掉的 GPU 周期 |
| 1F1B | “默认 pipeline 调度” | 一个前向 / 一个反向交错调度；DualPipe 击败的基线 |
| Zero Bubble | “Sea AI Lab 2023” | 把反向拆成 B（输入梯度）和 W（权重梯度）；几乎完全收紧了 pipeline |
| DualPipe | “DeepSeek-V3 调度” | 双向 pipeline + 计算-通信重叠；bubble 不随 micro-batch 数量增长 |
| DualPipeV | “Cut-in-half” | V 形改进版，去掉 2 倍参数复制，代价是 bubble 略大 |
| Chunk | “pipeline 工作单元” | 一个 micro-batch 通过一个 pipeline 阶段的一次前向或反向 |
| All-to-all dispatch | “把 token 发给专家” | 把 token 路由到其分配的 MoE 专家的跨节点通信 |
| All-to-all combine | “把专家输出带回来” | MLP 之后收集专家输出的跨节点通信 |
| Expert Parallelism (EP) | “专家分散在 GPU 上” | 把 MoE 专家分片到各 rank，使不同 GPU 持有不同专家 |
| Pipeline Parallelism (PP) | “层分散在 GPU 上” | 把模型层分片到各 rank；DualPipe 调度的正是这个维度 |
| Bubble fraction | “浪费的 GPU 时间” | (bubble_time / total_time)；DualPipe 力图压向零的那个比例 |

## Further Reading

- [DeepSeek-AI — DeepSeek-V3 Technical Report (arXiv:2412.19437), Section 3.3.2 and Figure 5](https://arxiv.org/abs/2412.19437) —— DualPipe 的主要参考
- [DeepSeek — DualPipe GitHub repository](https://github.com/deepseek-ai/DualPipe) —— 开源参考实现，包含 DualPipeV（Cut-in-half）模式
- [Qi et al. — Zero Bubble Pipeline Parallelism (arXiv:2401.10241, Sea AI Lab 2023)](https://arxiv.org/abs/2401.10241) —— Zero Bubble 前身
- [Sea AI Lab — DualPipe could be better without the Dual](https://sail.sea.com/blog/articles/63) —— 影响了 DeepSeek EP 关闭模式的 DualPipeV 分析
- [Narayanan et al. — PipeDream / 1F1B (arXiv:1806.03377, 2018-2021)](https://arxiv.org/abs/1806.03377) —— DualPipe 对比的 1F1B 调度
- [Huang et al. — GPipe (arXiv:1811.06965, 2018)](https://arxiv.org/abs/1811.06965) —— 最初的 pipeline parallelism 论文与 bubble 问题
