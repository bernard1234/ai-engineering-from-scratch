# Capstone 84 — Refusal 评测

> 良性 prompt 上有用，与有害 prompt 上拒答，是两个指标，不是一个。两个都要测。

**Type:** Build
**Languages:** Python
**Prerequisites:** 第 18 阶段安全类课程、第 19 阶段 Track A 第 25 至 29 课
**Time:** ~90 分钟

## 问题场景

助手的安全评估会以两种相反的方式出错。模型拒答了本该回答的东西（over-refusal），以及模型回答了本该拒答的东西（under-refusal）。两者都是 bug。只测有害 prompt 上拒答率的团队，上线的是连化学作业都不肯帮忙的模型。只测有用性的团队，上线的是会讲解如何造成伤害的模型。正确的指标集把助手视为 prompt 安全性的二分类器，由被测策略决定每个 prompt 落在决策边界的哪一侧。

难点在于真实 LLM 在开发过程中是个移动靶。改一次 system prompt、改一次 temperature、改一次 tool，都会让两个指标同步移动。你需要一个基于 fixture 的评测器，底层配一个确定性的 mock LLM，这样一次代码改动带来的指标变化都有已知原因。本课的 mock LLM 是一张小的分发表：pattern、policy、output。第 87 课的 harness 之后用一个 HTTP 调用替换 mock，把真实模型接进来。度量框架本身不变。

本课构建评测框架。它产出四个数：under-refusal 率、over-refusal 率、校准度（模型自报的置信度是否与它的准确率相符），以及基于第 82 课 taxonomy 的按类别拆分。

## 核心概念

一次 refusal 评测有四个对象：带 `safe`/`unsafe` 标签的 prompt 集合；带有脚本化策略的 mock LLM；作用于模型输出的 refusal classifier（对 `I cannot`、`I will not`、`as a responsible` 这类短语做正则）；以及指标聚合器。

```mermaid
flowchart LR
  P[labeled prompt set] --> M[mock LLM]
  M --> R[refusal classifier]
  R --> A[aggregator]
  A --> UR[under-refusal rate]
  A --> OR[over-refusal rate]
  A --> CAL[calibration ECE]
  A --> CAT[per-category breakdown]
```

mock LLM 的策略刻意保持简单，以便测试可审计。默认的 `MockPolicyStrict` 对匹配任一禁止正则模式的 prompt 拒答，其余则回答。`MockPolicyOverCautious` 在宽得多的模式集上拒答，因此故意过度拒答。`MockPolicyLeaky` 只对最明显的情况拒答，因此故意欠拒答。这三种策略是框架应当检测出来的脚本化 bug。

under-refusal：模型在标签集标记为 `unsafe` 的 prompt 上做出了回答（没有拒答短语）。over-refusal：模型在标签集标记为 `safe` 的 prompt 上拒答了（出现拒答短语）。harness 还会计算 `accuracy = (TP + TN) / total`，其中 TP 是「unsafe prompt 被正确拒答」，TN 是「safe prompt 被正确回答」。

校准度使用期望校准误差（ECE），基于模型自报的置信度。mock LLM 可以选择在输出中带一个 `confidence:0.X` token，由 harness 解析。ECE 按置信度以十分之一为单位分箱，计算每箱的准确率，并按箱大小加权平均 `|conf - accuracy|`。一个自报 `confidence:0.9` 但只有 60% 时候答对的模型，在该箱上的 ECE 约为 0.3。ECE 与 over/under refusal 相互独立，因为它度量的是模型是否知道自己何时是对的。

按类别拆分把已标注的 prompt 与第 82 课的 taxonomy 产物做关联。每个 unsafe prompt 都带一个类别标签（六类之一）。harness 按类别报告 under-refusal 率，这样团队就能看到，例如，模型对 `instruction-override` 处理得很好，却在 `multi-turn-ramp` 上出问题。

```figure
ci-refusal-quadrant
```

## Build It

`code/mock_llm.py` 定义三种策略。每种策略是一个把 prompt 映射到响应字符串的可调用对象。响应中以内嵌 `[conf=0.X]` 的形式携带模型置信度。`code/prompts.py` 是一个已标注语料库：25 条 unsafe prompt（按 id 取自第 82 课 taxonomy），加上 30 条 safe prompt（日常良性请求，与第 83 课的良性集合不重叠，以保证两次评测彼此独立）。

`code/main.py` 运行评测器。refusal classifier 是一组拒答短语正则。聚合器返回一个 dict，包含 `under_refusal`、`over_refusal`、`accuracy`、`ece` 和 `per_category_under_refusal`。runner 会扫过全部三种 mock 策略，并写出对比报告。

## Use It

`python3 main.py`。demo 打印三种策略的对比表，写出 `outputs/refusal_eval_report.json`，并确认 `MockPolicyOverCautious` 的 over-refusal 最高、`MockPolicyLeaky` 的 under-refusal 最高。strict 策略位居两者之间，它就是回归基线。

## Ship It

`outputs/skill-refusal-evaluation.md` 记录了指标定义，这样报告的下游使用者不会误读这些数字。

## Exercises

1. 增加第四种 mock 策略，按 prompt 长度决定是否拒答。确认在编码类攻击（通常较短）上 under-refusal 会上升。
2. 用可靠性曲线（reliability curve）替换 ECE，并针对每种策略各画一条。标出哪些箱过度自信。
3. 增加一份按类别的 safe prompt 列表（良性 role-play、关于先前上下文的良性指令）。计算按类别的 over-refusal，检查 role-play 是否招来最多的错误拒答。

## Key Terms

| 术语 | 常见说法 | 精确含义 |
|---|---|---|
| under-refusal | 模型很有用 | 模型回答了被标记为 unsafe 的 prompt |
| over-refusal | 模型很安全 | 模型拒答了被标记为 safe 的 prompt |
| calibration | 模型很谦逊 | 自报置信度与观察到的准确率之间的差距，用期望校准误差概括 |
| accuracy | 质量 | safe/unsafe 二分类决策的 (TP + TN) / total |
| per-category breakdown | 一张图表 | 与第 82 课 taxonomy 类别关联后的 under-refusal 率 |

## Further Reading

第 85 课（输出分类器）和第 87 课（端到端 gate）会消费本课的度量框架。
