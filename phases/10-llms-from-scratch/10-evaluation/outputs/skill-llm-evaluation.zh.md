---
name: skill-llm-evaluation
description: 根据任务类型、预算和需求，选择正确的 LLM evaluation 策略的决策框架
version: 1.0.0
phase: 10
lesson: 10
tags: [evaluation, evals, benchmarks, llm-as-judge, elo, metrics]
---

# LLM Evaluation 策略

评估一个 LLM 系统时，用这套决策框架来选择正确的方案。

## 各类 eval 的适用场景

**Benchmarks（MMLU、HumanEval、SWE-bench）：** 你正在做初步的模型选型。你需要把 10 个候选模型缩到 3 个。benchmark 以零成本给出粗略排名。不要把 benchmark 当作最终评估。

**自定义 eval：** 你在为生产环境构建。你有具体任务和具体失败模式。自定义 eval 是唯一能预测真实世界表现的评估方式。原型阶段至少 50 个测试用例，生产环境 200+。

**LLM-as-judge：** 你的任务是开放式的（摘要、写作、对话）。exact match 和 token overlap 指标太死板。LLM-as-judge 每次判断的成本约为 $0.01，与人类判断的一致率约为 80%。始终使用评分细则（rubric），不要用含糊的 prompt。

**人工 eval：** 风险很高，且自动化指标之间存在分歧。人工 eval 是 ground truth，但每次判断的成本为 $0.10-$2.00。留给歧义案例和自动化指标的定期校准。

**基于成对比较的 ELO：** 你在同一任务上比较多个模型。成对比较比绝对打分更可靠，因为人类（以及 LLM judge）更擅长相对判断。

## 评分函数的选择

- **Exact match**：分类、实体抽取、答案已知的结构化输出
- **Token F1**：部分得分有意义的抽取任务
- **ROUGE-L**：摘要、翻译
- **BLEU**：机器翻译
- **LLM-as-judge**：开放式生成、对话质量、有用性
- **基于执行（execution-based）**：代码生成（运行代码，检查测试是否通过）
- **Schema 合规性**：结构化输出（JSON 是否符合 schema？）

## eval 设计中的危险信号

- eval 集小于 50 个用例：结果在统计上没有意义
- 没有边界案例：你测的只是 happy path 表现，而它永远高于真实世界
- 单一指标：不同指标讲述不同的故事，至少用两个
- 没有版本管理：没有版本化的 eval 集，你无法追踪改进
- eval 集污染：绝不要把 eval 示例放进微调数据或 few-shot prompt 中
- 只测一个模型：你需要一个基线（哪怕是简单启发式）作为对比

## eval 流水线检查清单

1. 精确定义任务（不是 "回答问题"，而是 "把支持工单分为 5 个类别"）
2. 在 happy path、边界案例和已知回归上创建测试用例
3. 选择 2-3 个适合该任务类型的评分函数
4. 根据生产需求设定 pass/fail 阈值
5. 自动化执行：用一条命令跑完整套件
6. 为一切做版本管理：测试用例、评分函数、prompt、模型版本
7. 每次变更都运行：prompt 更新、模型替换、代码部署
8. 追踪趋势：单个分数是噪声，趋势线才是信号
9. 每季度对照人工判断做一次校准
10. 每当发现生产故障就补充回归用例
