---
name: skill-contract-reviewer
description: 校验一个 Agent Skill 包，并在实现之前选择正确的 instruction、capability 或生命周期 primitive。
license: MIT
metadata:
  lesson: "22"
---

# Skill 契约审查器

当一个工作流即将变成可复用的 agent 工件时，使用此 skill。

1. 把 `SKILL_ROOT` 设为包含已安装 `SKILL.md` 的绝对目录。不要假设进程工作目录就是 bundle 所在处。
2. 把 `TARGET_ROOT` 设为原始工作区的绝对工作目录，并在该根目录下解析拟议的 skill 目录。
3. 阅读 `$SKILL_ROOT/references/contract.md`，校验可移植 `SKILL.md` 的身份字段。
4. 阅读 `$SKILL_ROOT/references/decision-model.md`，区分仓库上下文、可复用方法、外部能力、生命周期时机、确定性逻辑和隔离委派。
5. 在执行前，展示精确解析后的参数向量。运行 `python3 "$SKILL_ROOT/scripts/check_skill.py" "$TARGET_SKILL"`，其中 `TARGET_SKILL` 是 `TARGET_ROOT` 下拟议 skill 目录的绝对路径。
6. 检查 JSON 报告。在讨论 host 特有扩展之前，先修复每一个 error。
7. 把拟议的工件与 `$SKILL_ROOT/assets/task-shapes.json` 比较，返回最小的可组合 primitive 集合。

不要声称某个运行时扩展是可移植契约的一部分。不要把有效的 skill 视为可以运行脚本或访问工具的许可。

返回校验报告、被选中的 primitives，以及为每个选择解释一句话的说明。附上执行证据，包括解析后的脚本路径、解析后的目标路径、cwd、精确 argv 和退出码。如果 host 无法暴露其中某条观察，就把它标记为未验证，而不是凭空编造。
