---
name: feedback-runner
description: 用确定性的 stdout/stderr/exit/duration 捕获包装 shell 命令，每条命令持久化一条 JSONL 记录，并在 feedback 缺失时拒绝推进 agent loop。
version: 1.0.0
phase: 14
lesson: 37
tags: [feedback, subprocess, runner, jsonl, loop-control]
---

给定一个在 agent loop 内运行 shell 命令的项目，产出 feedback runner 和它写出的 JSONL。

产出：

1. `tools/run_with_feedback.py`，暴露 `run_with_feedback(command: list[str], agent_note: str, timeout_s: float) -> FeedbackRecord`。
2. `feedback_record.jsonl` 位于 workbench 下的位置，每行一条记录。
3. `tools/feedback_loader.py`，返回当前任务最近 N 条记录。
4. 一个 `loop_can_advance(record) -> bool` 助手，agent loop 在宣称成功前调用它。
5. 测试覆盖：成功路径、非零 exit、超时、缺失二进制、确定性头/尾截断。

硬性拒绝：

- runner 里任何地方的 `shell=True`。只用 argv。
- 依赖墙钟或随机采样的截断。相同输入必须产生相同记录。
- 没有 `duration_ms` 的记录。慢 probe 是 workbench 卡死的第一个信号。
- 返回无界列表的 loader。封顶在最近 N 条或分页。

拒绝规则：

- 如果项目把 secret 经 stdout 管道传输，没有脱敏步骤就拒绝交付 runner。把本会被捕获的行摆在明面上。
- 如果项目有能无限挂起的命令，没有默认超时和显式覆盖列表就拒绝交付。
- 如果 runner 在带共享 state 的 worker 里运行，拒绝跳过 JSONL 追加周围的文件锁。多个写入者会撕裂文件。

输出结构：

```
<repo>/
├── feedback_record.jsonl
└── tools/
    ├── run_with_feedback.py
    ├── feedback_loader.py
    └── test_feedback_runner.py
```

结尾附上「接下来读什么」，指向：

- Lesson 38，消费这些记录的 verification gate。
- Lesson 39，给 run 打分时读取 feedback 的 reviewer agent。
- Lesson 23，一旦 feedback 稳固，加在 telemetry 侧的 OTel GenAI conventions。