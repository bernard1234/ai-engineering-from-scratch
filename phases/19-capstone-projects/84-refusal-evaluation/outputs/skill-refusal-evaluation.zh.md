---
name: skill-refusal-evaluation
description: 双向 refusal 指标，含校准度与基于已标注 prompt 语料库的按类别拆分
version: 1.0.0
phase: 19
lesson: 84
tags: [safety, evaluation, calibration]
---

# Refusal 评测

一份带 safe 与 unsafe 标签的 prompt 语料库会经过一个或多个模型策略。输出被分类为拒答或回答。框架返回：

- under-refusal：被标记为 unsafe 却得到回答的 prompt / unsafe 总数
- over-refusal：被标记为 safe 却被拒答的 prompt / safe 总数
- accuracy：（正确拒答 + 正确回答）/ 总数
- ECE：按自报置信度分箱的期望校准误差
- 按类别 under-refusal：与第 82 课 taxonomy 关联后的结果

## 接入真实模型

mock LLM 是一个可调用对象 `(prompt: str) -> str`。把它替换成返回模型输出、并内嵌置信度标签的 HTTP 包装（或者修改 `parse_confidence` 以读取你所用服务商暴露的任何字段）。其余一切保持不变。

## 产物

`outputs/refusal_eval_report.json` 包含各策略的指标。第 87 课读取这份报告来设定阈值。
