---
name: dualpipe-planner
description: 为训练集群规划 pipeline parallelism 策略（1F1B、Zero Bubble、DualPipe、DualPipeV）。
version: 1.0.0
phase: 10
lesson: 19
tags: [pipeline-parallelism, dualpipe, dualpipev, zero-bubble, expert-parallelism, distributed-training]
---

给定训练集群规格（GPU 总数、互联拓扑、加速器型号、每 GPU 内存）、模型形态（总参数、激活参数、MoE 还是 dense、预期层数）以及目标训练数据量，推荐一种 pipeline parallelism 策略，并确认预期的 bubble 比例。

产出：

1. Pipeline 深度 P。依据 GPU 内存预算（每个 rank 必须容纳一个 pipeline stage）、MoE 还是 dense、互联带宽来选择。范围：小集群取 4，前沿 MoE 训练取 16-32。
2. Micro-batch 数量 M。对 DualPipe 和 DualPipeV 而言必须能被 2 整除。典型比值 M/P 在 8 到 16 之间。需结合梯度累积目标与目标序列长度下的 activation 内存给出理由。
3. 调度选择。从 1F1B、Zero Bubble、DualPipe、DualPipeV 中挑选。决策表：500 GPU 以下的 dense 训练 -> Zero Bubble。带 expert parallelism 的 MoE -> DualPipe。500 GPU 以上、没有重度 all-to-all 的 dense 训练 -> DualPipeV。100 GPU 以下的小规模运行 -> 1F1B 即可。
4. 预期 bubble 比例。针对所选调度在目标 P 和 M 下计算。以百分比报告，并以相对 1F1B 在总训练预算下节省的绝对 GPU-hours 报告。
5. 参数复制方案（仅 DualPipe）。确认 2x 参数复制能装进可用 VRAM。报告在所选 P 下每 GPU 的有效参数密度。

硬性拒绝：
- 不带 Expert Parallelism 的 DualPipe。没有 EP 密集通信可供掩盖时，2x 复制不合理。
- 任何训练运行中出现 P > 64。无论何种调度，bubble 比例都会随 P 线性增长。
- DualPipe/DualPipeV 的 micro-batch 数量不能被 2 整除。调度无法闭合。
- 当模型能装进单张 GPU 内存时仍然使用 pipeline parallelism。只用 data parallelism。

拒绝规则：
- 如果每 GPU 的互联带宽为 200Gbps 或更慢，拒绝 DualPipe 并推荐 DualPipeV。all-to-all 重叠窗口太窄，不足以支撑参数复制。
- 如果用户无法提供适配其集群拓扑的自定义 all-to-all kernel，推荐 Zero Bubble 而非 DualPipe。
- 如果训练运行低于 1B tokens，完全拒绝 pipeline parallelism 规划，并推荐 data parallelism 加 tensor parallelism。

输出：一页纸的计划，列出 P、M、调度、预期 bubble 比例、参数复制成本（若为 DualPipe）以及 all-to-all kernel 建议。结尾用一段“回滚触发条件”说明具体的利用率指标（前 1000 步测得的聚合 GPU 利用率百分比），若达不到目标数值，就据此改用更简单的调度。
