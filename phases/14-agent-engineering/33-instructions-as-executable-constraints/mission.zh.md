# Mission - 将 Agent 指令作为可执行约束

## 目标
把散文式指令转成跨五类、机器可检查的规则，并产出一份 reviewer 能打分的 rule report。

## 输入
- `docs/agent-rules.md`，每条规则一个标题，每条带 slug、category、描述和一个 `check` 字段
- 一个故意违反两条规则的 demo agent run

## 交付物
- 把 `agent-rules.md` 加载进 dataclass 的解析器
- `rule_checker.py` 风格的函数，每个被引用的 `check` 一个
- 带每条规则 pass/fail 和聚合严重度的 `rule_report.json`

## 验收标准
- `python3 code/main.py` 以零退出
- 输出打印解析后的 rule set、run trace，以及每条规则的 pass/fail
- `rule_report.json` 抓住两处故意违规

## 范围之外
- 把 checker 接入 CI。本课止步于一份写出的 report。
- 框架 guardrail（OpenAI SDK、LangGraph interrupts）。rule set 是它们所实现的可读契约。

## 参考
- `docs/en.md` - 完整课程
- `code/main.py` - 参考实现
- `outputs/skill-rule-set-builder.md` - 提取出的 skill