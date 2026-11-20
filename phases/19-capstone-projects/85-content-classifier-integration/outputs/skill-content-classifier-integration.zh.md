---
name: skill-content-classifier-integration
description: 三个输出侧 classifier（toxicity、PII、instruction-leakage），共用一个 severity router，支持 block、redact、warn、log 四种动作
version: 1.0.0
phase: 19
lesson: 85
tags: [safety, classifier, output-filter]
---

# 内容分类器集成

三个 classifier，一个 router，四种动作。

## Verdict 结构

```text
ClassifierVerdict
  name: str
  severity: none | low | medium | high
  score: float in [0, 1]
  findings: list[str]
```

## 动作表

| 严重程度 | 动作 | 效果 |
|---|---|---|
| high | block | 输出被替换为一条 policy refusal |
| medium | redact | 按顺序应用各 classifier 的 redactor |
| low | warn | 交付输出并追加一条软提示 |
| none | log | 原样交付输出，记录 verdict |

## 各 classifier 的行为

- toxicity - 带空白边界与小范围左窗口否定检查的骚扰词；替换为 `[redacted-language]`
- pii - 邮箱、电话、SSN、经 Luhn 校验的信用卡、IPv4；SSN 与信用卡会升级 severity；每种形态都替换为标签
- instruction-leakage - 与已知 system prompt 做 trigram 余弦比较；severity 随重叠度上升；替换掉首行 system prompt

## 产出物

`outputs/classifier_report.json` 为每个用例携带 action verb、severity、脱敏后的输出以及完整的 verdict 列表。
