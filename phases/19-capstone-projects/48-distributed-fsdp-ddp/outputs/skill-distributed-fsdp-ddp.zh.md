---
name: distributed-fsdp-ddp
description: 用从零实现的 DDP 包装器，以及在 gloo 或 nccl 后端上的 FSDP 参数分片草图，拉起多 rank 训练。
version: 1.0.0
phase: 19
lesson: 48
tags: [distributed, ddp, fsdp, collectives]
---

## 何时使用

模型能装进一块设备，但你需要更高吞吐（DDP）。模型装不进一块设备（FSDP）。两种情况都是：同一套代码路径的多 rank 训练设置。

## 拉起进程组

```python
os.environ["MASTER_ADDR"] = "127.0.0.1"
os.environ["MASTER_PORT"] = str(port)
dist.init_process_group(backend="gloo", rank=rank, world_size=world_size)
```

`gloo` 是 CPU 后端；`nccl` 是 GPU 后端。两者实现相同的集合通信表面。

## 包裹模型

1. 在 rank 0 上，用你的 seed 构建模型。
2. 用 DDP 外壳包裹它。
3. 外壳的 `__init__` 对每个参数和缓冲区调用 `dist.broadcast(p.data, src=0)`。
4. 每次 `loss.backward()` 之后，trainer 调用 `sync_grads()`。
5. `sync_grads()` 调用 `dist.all_reduce(p.grad, op=SUM)` 和 `p.grad.div_(world_size)`。
6. 每个 rank 用相同的平均梯度执行 optimizer step。

## 参数分片（FSDP 草图）

1. 展平每个参数，填充到 `world_size` 的倍数。
2. 本地保留你的分片；释放其余部分。
3. forward 之前，`dist.all_gather(...)` 在每个 rank 上重建完整张量。
4. forward 之后，丢弃完整张量。

## 失败模式

- 跳过 broadcast：各 rank 从不同的初始化开始，静默分叉。
- 求和之后忘记相除：梯度被放大 world_size 倍，optimizer step 过大。
- 对 checkpoint 使用跨设备 rename：不是原子的；第 47 课同样的陷阱。
- 在同一次集合通信中混用 CPU 和 CUDA 张量：后端不匹配，run 挂起。
