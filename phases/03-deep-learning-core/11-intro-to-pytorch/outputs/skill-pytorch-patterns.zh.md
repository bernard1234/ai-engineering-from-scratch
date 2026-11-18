---
name: skill-pytorch-patterns
description: PyTorch 训练、评估和部署的参考模式
version: 1.0.0
phase: 3
lesson: 11
tags: [pytorch, training, deep-learning, gpu, patterns]
---

## 规范训练循环

（代码逐字保留）

## 混合精度训练

（代码逐字保留）

使用场景：在支持 float16 的 GPU（V100、A100、H100、RTX 3090+）上训练。预期 ~1.5–2x 提速和 ~50% 内存节省。

## 梯度累积

（代码逐字保留）

使用场景：有效 batch size 需要比 GPU 内存允许的更大。loss 除以 accumulation_steps 以保持梯度尺度一致。

## 保存和加载

（代码逐字保留）

恢复训练时永远保存优化器状态。仅推理用，只存 `model.state_dict()`。

## 自定义 Dataset

（代码逐字保留）

## DataLoader 配置

（代码逐字保留）

| 参数 | 做什么 | 何时用 |
|------|--------|--------|
| num_workers=4 | 并行加载数据 | 多核机器上始终 |
| pin_memory=True | 页锁定 CPU 内存 | 在 GPU 上训练时 |
| drop_last=True | 丢弃不完整的最后 batch | 用 BatchNorm 时 |
| persistent_workers=True | workers 跨 epoch 保持存活 | num_workers > 0 时 |

## 学习率调度

（代码逐字保留）

OneCycleLR：大部分任务的最佳默认。warmup 到 max_lr 然后 cosine decay。**每个 batch** 之后调 `scheduler.step()`，不是每个 epoch。

## 权重初始化

（代码逐字保留）

## 推理模式

（代码逐字保留）

`torch.inference_mode()` 比 `torch.no_grad()` 更快，因为它完全禁用 autograd 而不只是抑制梯度计算。

## 常见错误检查清单

1. CrossEntropyLoss 之前加了 softmax（它内部已经包含 log_softmax）
2. 验证时忘了调 model.eval()
3. 忘了把 tensor 移到和模型相同的设备
4. 没调 optimizer.zero_grad()（梯度默认会累积）
5. 训练时用 torch.no_grad()（禁用梯度计算）
6. num_workers 设太高（产生太多进程，内存 thrash）
7. GPU 上训练时没开 pin_memory=True
8. 存整个 model 对象而不是 state_dict（重构就坏掉）
