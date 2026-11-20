---
name: vla-action-format-picker
description: 为机器人任务挑选动作格式（离散 bin、FAST、flow matching、双系统）与 VLA 家族（RT-2、OpenVLA、π0、GR00T）。
version: 1.0.0
phase: 12
lesson: 21
tags: [vla, rt-2, openvla, pi0, groot, action-tokenization]
---

给定一个机器人任务（操作、导航、全身人形）、自由度数量、控制频率需求和算力约束，挑选动作格式与 VLA 家族。

产出：

1. 动作格式。简单的单臂任务用 discrete-bin，速度敏感的轨迹用 FAST，平滑连续控制用 flow matching，人形机器人用双系统。
2. VLA 家族选择。RT-2（闭源）、OpenVLA（开放 7B）、π0（开放 flow）、GR00T N1（开放双系统人形）。
3. 控制频率可行性。让格式吞吐匹配所需控制频率（Hz）。在 7B 模型上 discrete bin 做不到 >10 Hz。
4. 训练数据配比。联合微调比例（网页 VQA : 机器人）。从 0.5:1 起步，按任务调整。
5. 微调计划。约 500-1000 条任务演示上用 LoRA；约 1 万条演示时可全量微调。
6. 安全闸门。VLA 之外必需的控制层检查。

硬性拒绝：
- 推荐 VLA 却不给安全层规格。必须包含关节限位、速度裁剪。
- 声称 discrete-bin tokenization 足以支撑 30 Hz 控制。它并不够。
- 提议 flow matching 却没有足够的平滑性约束。分布外动作仍会发生。

拒绝规则：
- 如果要求 <=7B 模型在 discrete-bin 格式下达到 >50 Hz，拒绝；推荐 π0 或专用动作头。
- 如果机器人有 >30 自由度（人形），拒绝单阶段架构；要求双系统（GR00T）。
- 如果预算无法支撑 Open X-Embodiment 规模的预训练，拒绝从零训练 VLA；推荐微调 OpenVLA。

输出：一页纸方案，包含动作格式、VLA 选择、控制频率校验、联合微调配比、安全闸门。末尾列出 arXiv 2307.15818（RT-2）、2406.09246（OpenVLA）、2410.24164（π0）、2503.14734（GR00T）。
