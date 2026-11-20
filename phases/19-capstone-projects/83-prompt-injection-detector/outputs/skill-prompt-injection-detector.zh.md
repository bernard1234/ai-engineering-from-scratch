---
name: skill-prompt-injection-detector
description: 分层 detector 流水线，对任意 prompt 返回类别与置信度，并带可度量的 precision 与 recall
version: 1.0.0
phase: 19
lesson: 83
tags: [safety, detector, prompt-injection]
---

# Prompt Injection 检测器

这里的 detector 是从 prompt 到 verdict 的函数。verdict 携带一个来自第 82 课 taxonomy 的类别，以及 `[0, 1]` 区间内的置信度。

## 流水线

1. Normalize - 去掉零宽字符，还原同形异义字符（homoglyph），解码 base64/hex，折叠 leet 黑话数字，并借助常用词检查尝试 rot13。
2. Substring 规则 - 手写匹配串，例如 `ignore previous`、`from now on you are`、`decode this base64`。
3. Regex 规则 - token 级模式，例如 `\bignor\w*\s+(all|prior|previous|earlier)\b`。

聚合过程保留每个类别的最高分，返回分数最大的类别；若没有任何规则触发，则返回 `benign`。

## 新增一条规则

编辑 `code/rules.py`。一条规则是一个字典，包含 `name`、`category`（六个 taxonomy 类别之一）、`score`（0 到 1 的浮点数），以及 `substring` 或 `regex` 之一。重新运行 `main.py`，观察它对按类别 precision 和 recall 的影响。

## 产物

`outputs/detector_report.json` 是按类别的指标文件。第 87 课的端到端 gate 读取它来为置信度设定阈值。
