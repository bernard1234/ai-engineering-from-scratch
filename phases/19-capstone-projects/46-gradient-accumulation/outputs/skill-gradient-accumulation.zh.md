---
name: gradient-accumulation
description: 通过缩放 micro-batch 损失并每个窗口只 step 一次 optimizer，在比设备内存更大的 effective batch 上训练。
version: 1.0.0
phase: 19
lesson: 46
tags: [training, batch-size, distributed, scaling]
---

## 何时使用

Effective batch 是平滑梯度、匹配学习率调度的杠杆。当你在一次 forward pass 中负担不起它时，这就是配方。

## 配方

1. 把 `micro_batch` 选为能装进内存并跑满加速器的最大尺寸。
2. 从学习率调度中确定 `effective_batch`。
3. 设置 `accum_steps = effective_batch // (micro_batch * world_size)`，并断言它能整除。
4. 每个 micro batch：`loss = criterion(model(x), y) / accum_steps; loss.backward()`。
5. 在非最后的 micro 上，进入 `model.no_sync()` 以在 DDP 中跳过梯度 all-reduce。
6. 在最后一个 micro batch 之后，运行一次 `optimizer.step()`。在下一个窗口之前清零梯度。
7. optimizer 状态每个 effective batch 前进一步；学习率调度每个 effective batch 走一格。

## 日志

每个 effective step 输出一条小的 JSON 记录，包含 `samples_per_sec`、`median_step_ms`、`sync_calls`、`accum_steps`、`effective_batch`。没有它，代价权衡就是不可见的。

## 失败模式

- 忘记 `/ accum_steps` 缩放：梯度会爆炸 N 倍。
- 在窗口中途 step：参数会漂移。
- 每个 micro batch 都同步：受限于网络却没有任何统计收益。
- 与 mixed precision unscaling 混用：只缩放未 unscale 的损失。
