# Mission - 智能体工作台：为什么有能力的模型仍然会失败

## 目标
把同一个小的仓库任务跑两遍，一遍纯提示词，一遍接入七个工作台面，并产出一份失败模式报告，把每个缺失的面映射到它所造成的症状。

## 输入
- 一个桩智能体和一个待验证的极小 FastAPI 风格 handler
- 七个面的列表（instructions、state、scope、feedback、verification、review、handoff）

## 交付物
- `code/main.py`，背靠背地运行两条流水线
- `failure_modes.json`，总结纯提示词运行
- 针对工作台运行的一句裁决

## 验收标准
- `python3 code/main.py` 以零退出
- 输出展示两次运行并排的日志
- `failure_modes.json` 列出每一个缺失的面及匹配的症状

## 范围之外
- 调用真实模型。桩有意做成基于规则的。
- 深入构建任何一个面。那是接下来十一节课要做的。

## 参考
- `docs/en.md` - 完整课程
- `code/main.py` - 参考实现
- `outputs/skill-workbench-audit.md` - 提取出的 skill
