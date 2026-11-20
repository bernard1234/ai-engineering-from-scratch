---
name: checkpoint-save-resume
description: 原子化、分片的 checkpoint，配合完整的 RNG 捕获，使被杀的 run 能在中途 epoch 恢复并保持相同的损失轨迹。
version: 1.0.0
phase: 19
lesson: 47
tags: [training, durability, resume, sharded-state]
---

## 何时使用

任何比集群墙钟上限更长的训练 run，任何必须挺过节点重启的 run，任何大到单个 payload 装不下的模型。

## payload 结构

```python
{
  "schema": "ckpt.v1",
  "model": model.state_dict(),
  "optimizer": opt.state_dict(),
  "scheduler": sched.state_dict(),
  "state": {"step": int, "epoch": int, "batch_in_epoch": int, "losses": [float, ...]},
  "rng": {"python": ..., "numpy": ..., "torch_cpu": ..., "torch_cuda": ...},
  "wall_saved_at": time.time(),
}
```

## 原子写入

1. 把 payload 写到与目标同目录的唯一临时文件。
2. `os.replace(tmp, target)` 原子地换过去。
3. 永远不要直接写目标文件名。

## 分片布局

- 每个分片一个 `model.shard-NNN.pt`，按键轮转或按参数组切分。
- `meta.pt` 承载 optimizer、scheduler、train state、RNG 以及分片清单。
- `index.json` 承载每个分片以及 `meta.pt` 的 `sha256`。
- loader 在合并之前校验每个哈希，并拒绝 checkpoint 目录之外的分片路径。
- 用 `torch.load(path, map_location="cpu", weights_only=True)` 加载每个文件。把 RNG 状态保持为普通列表，好让它能通过 weights-only loader。

## 中途 epoch 恢复

- 在 `step` 旁边保存 `(epoch, batch_in_epoch)`。
- 在恢复 epoch 的第一个 batch 之前恢复 RNG 状态。
- 把生成器快进过已消费的 batch。

## 失败模式

- 跨设备 rename：不是原子的，会丢掉上一个文件。把临时文件放在同一目录。
- 忘记 RNG：恢复后的损失与基线偏离。运行 demo 的断言。
- 忘记 optimizer 状态：下一步会猛冲。同样的 diff 会爆炸。
- 修剪错了 checkpoint：保留最近 K 个加上最好的那个。
- 用 `weights_only=False` 加载：`.pt` 文件是 pickle，所以不可信 checkpoint 会在加载时执行代码。
