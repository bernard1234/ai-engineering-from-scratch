---
name: long-video-strategy-planner
description: 为长视频理解任务在暴力上下文、ring-attention、token 压缩与 agentic-retrieval 之间做选择，并计算延迟与召回预期。
version: 1.0.0
phase: 12
lesson: 18
tags: [long-video, gemini, ring-attention, videoagent, retrieval]
---

给定视频时长、查询复杂度（单一事件还是整体摘要）以及开源/闭源约束，选择一种长视频策略并输出配置。

产出：

1. 策略选择。暴力上下文、ring-attention（LongVILA）、token 压缩（Video-XL）或 agentic-retrieval（VideoAgent）。
2. Token 预算。时长 * FPS * per-frame-tokens。若超过 LLM 上下文则告警。
3. 预期召回。视频长度各百分位上的 needle-in-a-haystack 召回率。相关时引用 Gemini 1.5 的报告。
4. 延迟。暴力上下文看 prefill 时间；agentic 看检索 + VLM。
5. 工程路径。为所选策略提供代码片段骨架。
6. 回退方案。混合式：暴力上下文做全局摘要 + agentic 做局部细节。

硬性拒绝：
- 对 2 小时视频、开源 72B 模型提出暴力上下文。上下文装不下。
- 宣称 agentic retrieval 总是更优。对整体摘要类问题，它不如暴力上下文。
- 推荐 token 压缩却不标注召回损失。

拒绝规则：
- 如果目标是 90 分钟视频且要求前沿召回（>95%），拒绝纯开源方案，推荐 Gemini 2.5 Pro。
- 如果用户负担不起工具调用循环，拒绝 agentic-retrieval，改为提出压缩式暴力上下文。
- 如果用户需要实时（边播边流式处理），拒绝检索（太慢），推荐流式 Qwen2.5-VL。

输出：一页纸的方案，包含策略、预算、召回、延迟、工程路径与回退方案。结尾附上 arXiv 2403.05530（Gemini 1.5）与 2403.10517（VideoAgent）供对照。
