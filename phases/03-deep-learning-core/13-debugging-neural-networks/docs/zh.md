# 调试神经网络

> 90% 的训练 bug 是同样的 5 件事：损失函数、梯度流、形状、设备、数值稳定性。

**Type:** Learn + Practice
**Languages:** Python (PyTorch + NumPy)
**Prerequisites:** Phase 3 Lessons 1-12 (全部)
**Time:** ~45 minutes

## Learning Objectives

- 建立系统的调试流程：单 batch 过拟合 → 梯度/激活检查 → 超参数扫描
- 用 detect_anomaly、梯度范数追踪、激活统计定位失败点
- 对常见症状（梯度消失/爆炸、NaN、过拟合/欠拟合）应用诊断树
- 避免 10 个最常见的初学者错误

## 核心概念

### 调试决策树

1. **单 batch 过拟合测试**（60 秒）：取 8–32 个样本训练 200 步。能到 100% 准确率吗？不能 → bug 在模型/损失/循环。
2. **梯度流检查**：每层打印梯度均值。全零 → 死网络或断开的图。
3. **激活统计**：每层打印激活的均值、标准差、零比例。ReLU 层 >50% 零激活是死神经元。
4. **学习率扫描**：试除以 10、当前、乘以 10。如果只有中间值工作，LR 是对的。
5. **简化一切**：1 层模型 + 100 样本 + 合成数据。能学吗？

### 10 个常见错误

1. CrossEntropyLoss 前加 softmax
2. BinaryCrossEntropyLoss 前加 sigmoid（用 BCEWithLogitsLoss）
3. 验证时忘调 model.eval()
4. 忘调 optimizer.zero_grad()
5. 数据在 CPU、模型在 GPU（device mismatch）
6. 训练循环里用 torch.no_grad()
7. num_workers 设太高（进程爆炸）
8. BatchNorm 但训练时没调 model.train()
9. 存整个 model 对象而不是 state_dict()
10. 忘了在优化器里传给 .to(device)

### 数值调试技巧

- `torch.autograd.set_detect_anomaly(True)`：找 NaN 梯度的来源
- `.register_forward_hook` / `.register_backward_hook`：在任意层打印值
- 梯度裁剪 `clip_grad_norm_`：防止爆炸
- 加 epsilon：`log(x + 1e-7)`, `x / (y + 1e-8)`

## Build It + Use It

（实际调试 demo）

## Exercises

## Key Terms

## Further Reading
