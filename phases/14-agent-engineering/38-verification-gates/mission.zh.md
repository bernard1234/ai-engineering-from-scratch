# Mission - Verification Gate

## 目标
把 `verify(task_id, artifacts)` 实现为作用于 scope report、rule report、feedback log 和 diff 的纯确定性函数，每次任务收尾产出一份 `verification_report.json`。

## 输入
- 为 `scope_report.json`、`rule_report.json`、`feedback_record.jsonl` 和 diff 准备的 stub loader
- 检查表：验收已运行、验收零退出、scope 干净、无 `null` exit、所有 block 级规则通过

## 交付物
- 一个纯 `verify(task_id, artifacts) -> VerdictReport`
- 一个显示每项检查结果和最终 pass/fail 的 printer
- 三个写盘 demo 场景：干净通过、scope creep、缺失验收

## 验收标准
- `python3 code/main.py` 以零退出
- 干净通过场景报告 `passed: true`；另外两个报告 `passed: false`
- 每个场景在 `outputs/verification/` 下写一份单独的 `verification_report.json`

## 范围之外
- LLM-as-judge 逻辑。gate 保持确定性；定性判断属于 lesson 39 的 reviewer。
- 签名覆盖审计日志。练习提示以那种方式扩展 gate。

## 参考
- `docs/en.md` - 完整课程
- `code/main.py` - 参考实现
- `outputs/skill-verification-gate.md` - 提取出的 skill