---
name: lm-eval-harness
description: 最小的语言模型评测 harness，包含 JSONL 任务规格、五个指标、可替换 adapter 以及 leaderboard JSON 输出。
version: 1.0.0
phase: 19
lesson: 49
tags: [evaluation, metrics, leaderboard, harness]
---

## 何时使用

在固定的一组任务上比较两个模型、两个 checkpoint 或两个 prompt 模板。任何要交付、需要长期监控的东西。

## 任务规格

每个样本一行 JSONL：

```json
{"id": "ex-001", "prompt": "...", "targets": ["..."], "metric": "exact_match", "extras": {}}
```

一个文件里的所有样本共享同一个指标。文件名就是任务名。

## 指标

| 指标 | 签名 | 用途 |
|--------|-----------|---------|
| exact_match | 归一化小写 + 空白，判断相等 | 算术、事实性答案 |
| substring_contains | 目标必须出现在归一化后的预测中 | 带锚词的自由生成 |
| multiple_choice | 首字母匹配 | A/B/C/D 风格的问题 |
| rouge_l | 对分词文本计算 LCS F1 | 摘要、复述 |
| code_exec | 在 io_pairs 上运行预测的 `f`，统计匹配数 | 代码生成 |

所有指标返回 [0.0, 1.0] 中的浮点数。任务分数是平均值。

## Adapter

```python
class Adapter(Protocol):
    name: str
    def generate(self, prompts: list[str]) -> list[str]: ...
```

adapter 是唯一模型相关的代码。

## Leaderboard JSON

schema 字符串、时间戳、各任务分数与延迟、总体平均值。比较 run 时包含逐样本记录，让预测级别的回归可见。

## 失败模式

- 指标返回 [0, 1] 之外的值：总体分数变得无法解释。
- 一个任务文件里混用指标：断言触发；每个文件只保留一个指标。
- code_exec 没有受限命名空间：任意代码执行。
- 没有 schema 字符串：格式演进会破坏下游仪表盘。
