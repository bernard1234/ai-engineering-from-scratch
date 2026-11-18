# PyTorch 入门

> PyTorch 是研究界的默认深度学习框架。这一课让你会用它。

**Type:** Learn + Use
**Languages:** Python (PyTorch)
**Prerequisites:** Phase 3 Lessons 1-10 (全部核心概念 + 迷你框架)
**Time:** ~60 minutes

## Learning Objectives

- 创建 tensor、在 GPU/CPU 之间移动、autograd 追踪
- 用 nn.Sequential 或自定义 nn.Module 构建模型
- 写规范训练循环：forward → loss → backward → step → zero_grad
- 用 DataLoader + Dataset 加载数据，DataParallel/DDP 多 GPU

## 核心概念

### 五个核心组件

1. **Tensor**：多维数组，和 NumPy 类似但在 GPU 上跑，autograd 追踪
2. **nn.Module**：模型基类。自定义模型继承它，在 `__init__` 定义层，`forward` 定义数据流
3. **nn.Parameter**：自动注册到模块，优化器能访问
4. **autograd**：反向传播，跟踪操作链计算梯度
5. **Optimizer**：封装更新规则的 SGD/Adam 等

### 训练循环骨架

```python
model.train()
for batch in dataloader:
    optimizer.zero_grad()
    loss = criterion(model(x), y)
    loss.backward()
    optimizer.step()
```

### 验证循环骨架

```python
model.eval()
with torch.no_grad():
    for batch in val_loader:
        # compute metrics
```

### 常见陷阱

- CrossEntropyLoss 之前别加 softmax（它内部已经做了）
- BinaryCrossEntropyLoss 之前别加 sigmoid（用 BCEWithLogitsLoss 代替）
- 推理前别把 model.eval() 忘了（影响 BatchNorm 和 Dropout）
- 训练循环里别调 torch.no_grad()
- 数据和模型要在同一设备（.to(device)）

## Build It + Use It

（PyTorch 实际代码示例）

## Exercises

## Key Terms

## Further Reading
