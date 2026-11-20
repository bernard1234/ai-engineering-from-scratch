---
name: prompt-distributed-training-planner
description: 根据模型规模和可用硬件规划一次分布式训练
version: 1.0.0
phase: 10
lesson: 5
tags: [distributed-training, fsdp, deepspeed, tensor-parallelism, pipeline-parallelism, scaling]
---

# 分布式训练规划器

当你为大语言模型规划分布式训练时，用这个框架确定并行策略、内存预算、通信开销和预期吞吐。

## 输入要求

请提供：
- **模型规模**（参数数量，单位十亿）
- **目标训练 tokens**（单位万亿）
- **可用 GPU**（类型：A100/H100/H200，数量，互联方式：NVLink/InfiniBand）
- **GPU 显存**（A100/H100 为 80GB，H200 为 141GB）
- **节点**（每节点 GPU 数、节点数）
- **预算约束**（最高成本（美元）、最长 wall-clock 时间）

## 第 1 步：内存预算

计算每个组件占用的单 GPU 内存：

| 组件 | 公式 | FP16 | FP32 |
|-----------|---------|------|------|
| 权重 | params x bytes_per_param | params x 2 | params x 4 |
| Adam optimizer（m + v） | params x 4 x 2 | 始终 8 bytes/param | 8 bytes/param |
| 梯度 | params x bytes_per_param | params x 2 | params x 4 |
| Activations（估算） | seq_len x batch x hidden x layers x 2 | 视情况 | 视情况 |

如果总量超过 GPU 显存，就需要分片。按顺序尝试：
1. ZeRO-1（只分片 optimizer）—— 通信最便宜
2. ZeRO-2（+ 梯度）—— 中等通信
3. FSDP/ZeRO-3（+ 权重）—— 通信最多但内存节省最大
4. 如果 activations 仍然太大，加入 activation checkpointing
5. 如果单层无法放进一张 GPU，加入 tensor parallelism

## 第 2 步：并行策略

### 决策树

1. **单层能放进一张 GPU 吗？**
   - 不能：你需要 tensor parallelism。设 TP = 2、4 或 8（节点内）。
   - 能：跳过 tensor parallelism。

2. **完整模型（含分片）能放进一个节点的 GPU 上吗？**
   - 不能：你需要 pipeline parallelism。设 PP = 节点数 / 组数。
   - 能：跳过 pipeline parallelism。

3. **剩下多少 GPU 用于 data parallelism？**
   - DP = total_gpus / (TP x PP)

4. **data parallel 组内用什么分片级别？**
   - 从 FSDP（ZeRO-3）开始。如果通信成为瓶颈，降到 ZeRO-2 或 ZeRO-1。

### 典型配置

| 模型规模 | GPU 总数 | TP | PP | DP | 分片 |
|-----------|-----------|----|----|-----|----------|
| 7B | 8 | 1 | 1 | 8 | FSDP |
| 13B | 16 | 2 | 1 | 8 | FSDP |
| 70B | 64 | 8 | 1 | 8 | FSDP |
| 70B | 128 | 8 | 2 | 8 | FSDP |
| 405B | 16,384 | 8 | 16 | 128 | FSDP |

## 第 3 步：通信分析

估算每个训练 step 的通信量：

- **Data parallel（all-reduce）**：每 step 2 x gradient_size x (N-1)/N
- **FSDP（all-gather + reduce-scatter）**：每 step 约 3 x weight_size x (N-1)/N（高于 DP）
- **Tensor parallel（每层 all-reduce）**：每 step 2 x activation_size x num_layers（需要 NVLink）
- **Pipeline parallel（point-to-point）**：每个 stage 边界 activation_size（极小）

如果通信时间超过计算时间的 20%，该策略就是通信受限的。解决方案：
- Gradient accumulation（降低 all-reduce 频率）
- 让通信与计算重叠（FSDP 默认这样做）
- 增大 micro-batch 大小（改善计算与通信的比例）
- 切换到通信更少的分片阶段

## 第 4 步：吞吐与成本估算

**每个训练 step 的 FLOPS：**
- 前向：约 2 x params x tokens_per_batch
- 反向：约 4 x params x tokens_per_batch（前向的 2 倍）
- 总计：约 6 x params x tokens_per_batch

**训练时间：**
- total_flops = 6 x params x total_tokens
- time_seconds = total_flops / (num_gpus x gpu_tflops x 1e12 x utilization)
- 典型利用率：35-45%（已计入通信、pipeline 气泡、内存开销）

**成本：**
- total_gpu_hours = num_gpus x time_seconds / 3600
- cost = total_gpu_hours x cost_per_gpu_hour

## 第 5 步：校验清单

启动之前：

1. 单 GPU 内存符合硬件上限（留 10% 余量）
2. 有效 batch size 符合目标（per_gpu_batch x DP x gradient_accumulation_steps）
3. 通信与计算之比低于 20%
4. Pipeline 气泡占比低于 15%（micro-batch 足够多）
5. 学习率已按有效 batch size 缩放
6. checkpoint 频率考虑了失败概率（大规模训练每 1-2 小时保存一次）
7. 已设置 gradient clipping（大模型通常为 1.0）
8. warmup 步数与总步数成比例（通常为总量的 0.1-1%）

## 危险信号

- **TP > 8**：跨节点的 tensor parallelism（走 InfiniBand）几乎总是比 pipeline parallelism 慢
- **Pipeline stage > 32**：即使有很多 micro-batch，气泡开销也会变得显著
- **有效 batch size > 10M tokens**：收益递减；可能损害收敛
- **利用率低于 30%**：通信受限 —— 重新评估并行策略
- **13B 以上没有 activation checkpointing**：你会在反向传播时耗尽内存
- **每 GPU batch 很小时没有 gradient accumulation**：梯度噪声增大；累积到有效 batch 256+ 个样本
