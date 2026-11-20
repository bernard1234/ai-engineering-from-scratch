---
name: checkpointing-planner
description: 给定训练配置与 HBM 预算，为每一层选择 activation recomputation 策略（none / selective / full / offload）。
version: 1.0.0
phase: 10
lesson: 34
tags: [gradient-checkpointing, activation-recomputation, selective-checkpoint, fsdp-offload, training-memory]
---

给定训练配置（层数 L、hidden size d、序列长度 S、microbatch B、每个值的 dtype 字节数、attention kernel、tensor-parallel degree TP、pipeline-parallel degree PP、若为 MoE 则还有 expert-parallel degree EP）以及在扣除权重与优化器状态后的每 rank HBM 预算，输出：

1. 逐层策略。对栈中每一族层（embedding、attention、FFN、MoE expert、norm、output head）选择 none、selective、full 或 offload。当 S 超过 4_096 时，attention 默认给 selective；残差流与 norm 默认 none；仅当该层 activations 的实测 PCIe 传输时间低于其实测 recompute 时间时，FFN 才默认 offload。
2. 分段大小 k。若启用 full checkpointing，层成本均匀时取 k 为 round(sqrt(L))，当 activation 内存主导预算时取更小的 k。以 forward FLOPs 的 (1/k) 报告额外 FLOP 百分比。
3. FlashAttention 交互。确认 attention kernel 是否已经重算 softmax。若是，selective attention checkpointing 收益很小；降为 none。按名称说明 kernel（FlashAttention-2/3、xFormers memory-efficient、vanilla）。
4. TP / PP 方案。对 TP，说明 recompute 时需要 gather 或 rescatter 的 activations，以及每步新增的通信字节。对 PP，确认哪些 pipeline stage 端到端做 checkpoint，使反向 microbatches 在回流前释放 activation 内存。
5. 预算计算。预测该策略前后的 activation 内存（每 rank 的 MB）。以 fwd+bwd 的百分比预测 FLOP 开销。拒绝任何在留 10% 余量下仍装不进 HBM 预算的方案。

当仅对 attention 做 selective 就能闭合预算时，拒绝对每一层做 full checkpointing；剖析显示相同内存节省下 FLOP 开销是 selective 的数倍，且确切比例依工作负载而定。当该层 activations 在目标 PCIe 链路上的实测传输时间超过其实测 recompute 时间时，拒绝 offload；此时 recompute 胜出。当所选框架不对 amax 历史做快照时，对 FP8 训练拒绝“到处 checkpoint”；recompute 会漂移 scale，并静默污染梯度。

示例输入：“L=64, d=8192, S=8192, B=1, bf16, FlashAttention-3, TP=8, PP=4，扣除权重后每 rank 的 HBM 预算 32 GB，MoE 含 8 个 expert 且 EP=8。”

示例输出：
- 逐层策略：attention selective、FFN none、MoE expert full、embedding none、output head offload。
- 分段大小：仅在 MoE 上启用 full，k=8；expert 路径的 FLOP 开销为 12%，其他处为 0。
- FlashAttention 交互：FA-3 已重算 softmax；在层包装层做 selective，而非 kernel 内部。
- TP / PP 方案：recompute 时对 attention 输入做 TP gather，每步额外通信 0.3 GB；PP 各 stage 对完整 forward 做 checkpoint；PP stage 3 保留其 activations 以供最终 backward。
- 预算计算：无策略时 activations 38 GB，有策略时 11 GB。总 FLOP 开销为 fwd+bwd 的 7.5%。
