# 发现契约

发现包含三个披露层级：

1. Catalog：读取 routing 所需的 `name`、`description`、作用域和路径。
2. 激活：在显式的大小预算下加载被选中 SKILL.md 的正文。
3. 执行支持：仅当需要时才加载直接点名的文件，如 `references/schema.md`。

Host 拥有作用域位置、优先级、冲突行为和预算。Catalog builder 必须在输出中让这些选择保持可见。

可移植的单层 reference 是 skill 目录中的普通文件，或某一个直接子目录中的普通文件。拒绝绝对路径、`..`、反斜杠、符号链接和更深的链。
