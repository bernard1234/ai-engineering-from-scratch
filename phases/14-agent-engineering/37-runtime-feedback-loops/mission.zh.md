# Mission - Runtime Feedback Loop

## 目标
构建 `run_with_feedback`，包装 `subprocess.run`，捕获 stdout、stderr、exit code 和耗时，确定性截断输出，并追加一条下个 turn 和 verification gate 都读的 JSONL 记录。

## 输入
- 三条用来锻炼 runner 的 demo 命令：一条成功、一条失败、一条慢
- Token 预算：带 `...truncated N lines...` 标记的确定性头加尾

## 交付物
- 写入 `feedback_record.jsonl` 的 `run_with_feedback(command, agent_note)`
- 把 JSONL 流式读进 Python 列表的 loader
- 显示每条命令最后一条记录的 printer

## 验收标准
- `python3 code/main.py` 以零退出
- `feedback_record.jsonl` 跨重跑每条命令累积一条记录
- 一条 `exit_code: null` 的命令不能被 loop 标记为成功

## 范围之外
- Telemetry 管道（OTel、Langfuse）。Feedback 给下个 turn；telemetry 给操作员。
- 脱敏 pass 和轮转策略。本课的练习提示覆盖这些。

## 参考
- `docs/en.md` - 完整课程
- `code/main.py` - 参考实现
- `outputs/skill-feedback-runner.md` - 提取出的 skill