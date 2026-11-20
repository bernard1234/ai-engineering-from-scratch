---
name: skill-catalog-builder
description: 在显式的发现作用域上构建有界的 Agent Skill catalog，并在加载指令正文之前报告冲突。
license: MIT
metadata:
  lesson: "24"
---

# Skill catalog 构建器

当 agent host 需要在多个 skill 目录之间做确定性发现时，使用此 skill。

1. 阅读 `references/discovery-contract.md`。
2. 查看 `assets/scope-policy.json` 中的示例 host 策略；不要假设它的顺序是通用的。
3. 运行 `python3 scripts/build_catalog.py project=PATH user=PATH`，作用域按优先级从高到低排列。
4. 在激活 skill 之前，检查 JSON 中的 `collisions` 和 `omitted` 数组。
5. 只加载被选中 SKILL.md 的正文。仅当正文点名某个直接 reference 时才加载它。

绝不要在发现期间执行打包的脚本。绝不要按偶然的文件系统顺序来选择同优先级的重复项。

返回 catalog 预算、选中的条目、冲突解析结果和省略项。
