# Mission - Reviewer Agent：将 Builder 与 Marker 分离

## 目标
构建一个 reviewer loop，以只读方式读取 builder 的产物，并产出一份跨五个维度打分的 `review_report.json`，总分 10 分，verdict 为 pass、soft_fail 或 hard_fail。

## 输入
- 打包前几课的 diff、state、feedback 和 verification verdict 的 `ReviewerInputs`
- Rubric 维度：problem fit、scope discipline、assumptions、verification quality、handoff readiness

## 交付物
- 每个维度一个打分函数（本课为 stub 级别、确定性）
- 带五个分数、总分和 verdict 的 `review_report.json` writer
- 两个 demo 用例：一个干净的改动，和一个「测试对了、问题错了」的改动

## 验收标准
- `python3 code/main.py` 以零退出
- 干净改动至少得 7 分，verdict 为 `pass`
- 错问题改动在至少一个维度上跌破 5 分，verdict 翻转为 `hard_fail`

## 范围之外
- 真实 LLM 调用。本课对每个维度做 stub；skill 之后再换入模型。
- 修改 diff。reviewer 读取、打分并报告。补丁是 builder 下一轮的工作。

## 参考
- `docs/en.md` - 完整课程
- `code/main.py` - 参考实现
- `outputs/skill-reviewer-agent.md` - 提取出的 skill
