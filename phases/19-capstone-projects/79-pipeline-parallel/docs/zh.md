# Pipeline Parallel 与 Bubble 分析

> Tensor parallel 把矩阵乘法切分到多个 rank 上。Pipeline parallel 则把模型切分到多个 rank 上，每个 rank 一个阶段。Microbatch 依次流过 pipeline。首尾那段空转时间就是 bubble，把它压到最小就是这门手艺的全部。

**Type:** Build
**Languages:** Python
**Prerequisites:** 第 19 阶段 Track C 第 42 至 49 课
**Time:** ~90 分钟

## Learning Objectives

- 把一个顺序模型切成 N 个阶段，并在 N 个 rank 上模拟前向 pipeline。
- 用 GPipe 调度（先只用 forward 填满，再做 backward）让 M 个 microbatch 流过 pipeline，并计算 bubble 比例。
- 将 bubble 与 Megatron-LM、PipeDream 所用的 interleaved 1F1B 调度作对比。
- 论证阶段划分：每阶段计算量相等比每阶段参数数量相等更重要。

## 问题场景

一个 70B 参数模型单是 fp16 权重就要 140 GB 内存，没有消费级 GPU 装得下。ZeRO-3 把参数分片到多个 rank 上，但每次 forward 仍需要每个 rank allgather 出完整的一层，每层要付 log(N) 跳的代价。Pipeline parallel 走的是另一条路：把模型切成 N 个阶段，每个 rank 放一个阶段。第 1 层在 rank 0 上完成 forward 后把激活张量交给 rank 1；rank 1 跑第 2 层再交给 rank 2；依此类推。Backward 反方向流动。因为每个 rank 只持有一个阶段，内存线性下降；代价是计算变成串行，这就是 bubble 问题。

Bubble 是 pipeline 两端的空转时间：开始时要等第一个 microbatch 抵达最后一个阶段，结束时又要等最后一个 microbatch 回传排空。在 M 个 microbatch、N 个阶段的设定下，每个阶段的 bubble 比例是 (N-1)/(M+N-1)。M=8、N=4 时是 27%；M=64、N=4 时是 4.5%。每一步的 microbatch 越多，bubble 越小，而这意味着每个 microbatch 的 batch size 要小——正是这一约束决定了 microbatch 的设计。

## 核心概念

```mermaid
flowchart LR
  R0[rank 0: stage 0 / layer 0] --> R1[rank 1: stage 1 / layer 1]
  R1 --> R2[rank 2: stage 2 / layer 2]
  R2 --> R3[rank 3: stage 3 / loss]
  R3 -.backward.-> R2
  R2 -.backward.-> R1
  R1 -.backward.-> R0
```

### GPipe 调度

先用全部 M 个 microbatch 把 pipeline 前向填满，再开始任何 backward；然后反向排空。每个 microbatch 的激活值都必须保留到它的 backward 时刻，因此内存随 M 线性增长。前向耗时 M+N-1 个周期，后向再耗 M+N-1 个周期。每阶段的有效工作是 2M 个周期，每阶段的 bubble 是 2(N-1) 个周期。当每次 forward 和 backward 各占一个单位时间时，bubble 比例为 (N-1)/(M+N-1)。取 M 远大于 N 即可把 bubble 藏起来。

### 1F1B 调度

交错执行：一旦某个 microbatch 的 forward 抵达最后一个阶段，立刻开始它的 backward，让它一路流回。该调度在每个阶段交替执行一次 forward 和一次 backward。Bubble 仍是 N-1，但激活内存由 pipeline 深度决定，而不是由 microbatch 数量决定。生产 pipeline 用的是 1F1B（Megatron、PipeDream）。本课先实现较简单的 GPipe，把 1F1B 留作练习。

### 为什么每阶段计算量相等很重要

如果阶段 0 耗时 50 ms、阶段 1 耗时 100 ms，那么每个周期都被阶段 1 卡住。其他阶段每个周期空转 50 ms 等阶段 1 放行。参数数量相等是错误的维度：transformer 的计算量由每层的 attention 加 MLP 主导，而 embedding 层参数很多、计算很少。阶段划分应当让每阶段的 FLOPs 相等，而不是让每阶段的权重相等。

### Microbatch 与 batch 的区别

一条 pipeline 跑 M 个大小为 B 的 microbatch。有效 batch size 是 M*B。pipeline 一步结束时的 gradient 是在这 M*B 个样本合成的 batch 上的 gradient。Bubble 比例取决于 M，优化器看到的是 M*B。调 M 就是在 bubble（M 越大越低）与每 microbatch 内存（GPipe 下 M 越大激活内存越高）之间做权衡。

```figure
cd-pipeline-bubble
```

## Build It

`code/main.py` 实现了：

- `PipelineStage`：一个小型 `nn.Module`，持有一个阶段的参数，并暴露 `forward(activation)`。
- `Pipeline(stages, num_microbatches)`：在模拟的阶段上编排 GPipe 调度，每阶段使用模拟的墙钟时间。
- `bubble_fraction(num_stages, num_microbatches)`：闭式公式 (N-1)/(M+N-1)。
- 一个 4 阶段的 demo，打印逐 microbatch 的时间线以及实测的 bubble 比例。

运行它：

```bash
python3 code/main.py
```

输出：一张阶段 × microbatch 的甘特图，以及与闭式预测对照的 bubble 百分比。

## 实战中的生产模式

三种模式让 pipeline parallel 达到可以上线的程度。

**激活 checkpointing 与 pipeline 天然搭配。** GPipe 上有 M 个 microbatch 同时在飞，激活内存就是单个 microbatch 的 M 倍。激活 checkpointing 在 backward 时重算 forward，以计算换内存；二者结合才让 pipeline 在长序列上可行。

**阶段均衡要靠测量，不能靠假设。** 生产团队会跑一遍 profiling，在目标硬件上测量每层的实际计算量（FLOPs 与墙钟时间），再据此划分。Megatron-LM 的 `--num-layers-per-stage` 参数接受一个列表，以便在阶段之间单层成本不同时允许层数不均。

**Send-recv 调度必须避免死锁。** 如果每个阶段都先 send 后 recv，pipeline 会在链路上死锁。标准做法是交错：偶数 rank 的阶段先 send 再 recv，奇数 rank 的阶段先 recv 再 send。本课显式安排了各 rank 的顺序，让这个模式清晰可见。

## Use It

生产实现：

- **Megatron-LM。** 大规模 pipeline parallel 的参考实现。使用 1F1B，并支持 tensor + pipeline + data parallel 组合。
- **DeepSpeed Pipeline。** 与 ZeRO 集成；ZeRO-1 + pipeline 是最大的开源模型常用的组合。
- **PyTorch Pipe。** PyTorch 原生的 pipeline wrapper，建立在 `torch.distributed.pipeline.sync.Pipe` 之上。

## Ship It

第 80 课把各阶段的参数分片写进分片 checkpoint。第 81 课在端到端 demo 中把 DDP + ZeRO + pipeline 组合起来（在思路层面；demo 出于运行时间的考虑让 pipeline 保持模拟）。

## Exercises

1. 实现 1F1B，验证 bubble 比例与 GPipe 相同，但激活内存有上界。
2. 在更深的模型上测量真实的每阶段耗时，并按实测墙钟时间重新均衡各阶段。
3. 加入跨 pipeline microbatch 的 gradient 累积，检查所得 gradient 等于等价的全 batch forward 的 gradient。
4. 让 pipeline 搭配激活 checkpointing，测量内存下降与计算代价。
5. 把 pipeline 与 DDP 结合（每个 pipeline rank 在一个数据并行组内被复制），并推演这个二维调度。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Pipeline | "沿深度做模型并行" | 每个 rank 一个阶段，激活值逐阶段流动 |
| Bubble | "pipeline 空转时间" | 首尾共 (N-1) 步，期间部分阶段无事可做 |
| Microbatch | "batch 的切片" | 一个 forward/backward 单位；M 增大时 bubble 缩小 |
| GPipe | "先填满再排空" | 全部 M 次 forward 之后才开始 backward；激活内存高 |
| 1F1B | "交错调度" | 每阶段一次 forward 一次 backward；激活内存有界 |

## Further Reading

- [Huang et al, GPipe: Efficient Training of Giant Neural Networks](https://arxiv.org/abs/1811.06965)
- [Narayanan et al, PipeDream: Generalized Pipeline Parallelism for DNN Training](https://arxiv.org/abs/1806.03377)
- [Megatron-LM pipeline parallel docs](https://github.com/NVIDIA/Megatron-LM)
- 第 19 阶段第 76 课 —— 调度所用的 send/recv 原语
- 第 19 阶段第 78 课 —— ZeRO 与 pipeline 正交，且常被组合使用
