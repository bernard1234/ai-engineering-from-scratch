---
name: workbench-benchmark
description: 在项目自己的示例应用上，把同一个 task 分别跑过仅 prompt 和 workbench 引导两条 pipeline，产出一份五 outcome 的前后对比报告。
version: 1.0.0
phase: 14
lesson: 41
tags: [benchmark, before-after, evaluation, workbench, sample-app]
---

给定一个 repo、一个 agent 产品和一个小的示例应用，产出一个可移植的评估 harness，用于对比仅 prompt 与 workbench 引导的 pipeline。

产出：

1. `eval/sample_app/` —— 一个从项目领域抽取的最小可行示例应用。
2. `eval/run_prompt_only.py` 和 `eval/run_workbench.py`，各自接收一个 task 描述并返回一个 `TaskOutcome`。
3. `eval/report.py`，运行两条 pipeline，写出 `before-after-report.md` 和 `comparison.json`。
4. 当一个固定 task 套件的 workbench outcome 退化时就失败的 CI workflow。
5. `docs/benchmark.md`，解释五个 outcome 以及什么算作退化。

硬性拒绝：

- 只有一条 pipeline 的基准。对比才是全部意义所在。
- 没有分母、只写成百分比的 outcome。始终报告 `n / m`。
- agent 产品在其上训练过的示例应用。要使用领域调优的 fixture。
- 隐藏假阴性的报告。必须列举出仅用 prompt 更快的任务。

拒绝规则：

- 如果项目没有验收命令，拒绝交付这个基准。没有任何东西可测量。
- 如果在中位数任务上，workbench pipeline 的耗时超过仅 prompt pipeline 的 3 倍，就把这个发现摆出来；需要简化的是 workbench，而不是模型。
- 如果 harness 无法离线运行，拒绝把它接入 CI。网络抖动会破坏对比。

输出结构：

```
<repo>/
├── eval/
│   ├── sample_app/
│   ├── run_prompt_only.py
│   ├── run_workbench.py
│   └── report.py
├── outputs/eval/
│   ├── before-after-report.md
│   └── comparison.json
├── docs/benchmark.md
└── .github/workflows/benchmark.yml
```

以「接下来读什么」结尾，指向：

- 第 42 课，了解捆绑 workbench pipeline 所用到的每一个 surface 的 capstone pack。
- 第 19 课（SWE-bench、GAIA、AgentBench），了解本基准所补充的宏观基准。
- 第 30 课（Eval-Driven Agent Development），了解基准接好之后的持续 eval 循环。
