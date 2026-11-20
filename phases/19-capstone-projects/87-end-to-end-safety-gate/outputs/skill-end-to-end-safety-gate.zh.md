---
name: skill-end-to-end-safety-gate
description: 三检查点 safety gate，组合输入检测器、流式 token 过滤器、输出 classifier 与规则引擎，配一张确定性聚合表和逐请求 trace
version: 1.0.0
phase: 19
lesson: 87
tags: [safety, harness, composition]
---

# 端到端 Safety Gate

## 生命周期

1. pre-gen - 对 prompt 运行第 83 课的 detector
   - 若 confidence >= block_threshold：返回 refusal，输出 trace，停止
2. during-gen - 从模型流式读取，缓冲两个 chunk，扫描已知的有害续写
   - 若命中：终止迭代器，标记 trace，按 medium severity 处理
3. post-gen - 若无提前终止，对完整输出运行第 85 课的 classifier router 与第 86 课的 rules engine
4. aggregate - 取 pre、during、post.classifier、post.rules 中的最大 severity
5. apply - 映射为 block、redact、warn 或 allow

## 聚合表

| 信号状态 | 动作 |
|---|---|
| 任一 high severity | block |
| 任一 medium severity | redact |
| 任一 low severity | warn |
| 无任何信号 | allow |

## Trace 结构

```text
RequestTrace
  request_id: str
  prompt: str
  pre_gen: { category, confidence, fired[] }
  during_gen: { terminated_early, matched_pattern, partial_chunks }
  post_gen: { classifier_action, classifier_severity, rules_max_severity, rules_violations[] } | null
  final_action: block | redact | warn | allow
  final_output: str
  latency_ms: float
```

## 产出物

`outputs/gate_trace.json` 包含摘要与每个请求一条 trace，覆盖 50 条 taxonomy fixture 和 10 条良性 prompt。
