# Mission - Capstone：交付一个可复用的 Agent Workbench Pack

## 目标
把前面的十一课组装成一个带版本号的 `outputs/agent-workbench-pack/` 目录，并配一个能把它幂等地铺进任何目标 repo 的安装器。

## 输入
- 来自第 32 到 40 课的 schema、脚本和文档
- pack 布局：`AGENTS.md`、`docs/`、`schemas/`、`scripts/`、`bin/`、`README.md`、`VERSION`

## 交付物
- 填充了完整布局的 `outputs/agent-workbench-pack/`
- `bin/install.sh`（或 `bin/install.py`），没有 `--force` 就拒绝覆盖
- `VERSION` 文件，外加描述什么留下、什么出局的 `README.md`

## 验收标准
- `python3 code/main.py` 以零退出码结束并打印 pack 树
- 重复运行组装器是幂等的
- 对全新目标执行 `bin/install.sh` 后留下一个可用的 workbench：state、board、rules、scope、init、runner、gate、reviewer、handoff 各就各位

## 范围之外
- 每个项目的 task 内容。task 属于目标 repo 的 board，不属于 pack。
- 厂商 SDK 调用。pack 按设计是框架无关的。

## 参考
- `docs/en.md` - 完整课程
- `code/main.py` - 参考实现
- `outputs/skill-workbench-pack.md` - 抽取出的 skill