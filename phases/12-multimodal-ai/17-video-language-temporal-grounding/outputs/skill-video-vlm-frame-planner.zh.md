---
name: video-vlm-frame-planner
description: 为 video-language model 部署规划帧采样、逐帧池化、输出格式与 benchmark 目标。
version: 1.0.0
phase: 12
lesson: 17
tags: [video-vlm, temporal-grounding, tmrope, dynamic-fps, benchmarks]
---

给定一个视频任务（动作识别、temporal grounding、摘要、监控、agent-workflow 回放）和一项部署约束（模型上下文、延迟预算、吞吐），产出一份帧采样与输出方案。

产出：

1. Frame sampler 选择。内容平稳用 uniform，运动混杂用 dynamic-FPS，动作密集用 event-driven，影视内容用 keyframe + context。
2. 逐帧池化。高细节用 2x2，默认 3x3，agent 工作流中内容密度不如覆盖率重要时用 4x4 或 6x6。
3. 时序编码。Qwen2.5-VL 系列用 TMRoPE；较小模型用可学习时序 embedding；单 clip 任务不做编码。
4. 输出格式。grounding 用带 `{event, start, end, confidence}` 的 JSON；摘要用自由文本；混合流程用 token 分隔格式。
5. Benchmark 方案。通用用 VideoMME，grounding 用 TempCompass，长时程用 EgoSchema。指定预期的准确率档位。
6. 上下文 / 延迟预算。总 token = 时长 * fps * tokens_per_frame。若超过上下文的 40% 则告警。

硬性拒绝：
- 对动作密集的视频提出 uniform 采样。会丢失峰值事件。
- 宣称 token 分隔输出在下游解析上能达到 JSON 的准确率。JSON 更稳健。
- 对任何 2026 年启动的项目推荐 Video-LLaMA。较旧的架构已不再有竞争力。

拒绝规则：
- 如果时长 > 10 分钟且上下文 < 32k，拒绝，并推荐分层摘要或 agentic retrieval（Lesson 12.18）。
- 如果目标准确率是前沿水平（在 VideoMME 上与 Gemini 2.5 Pro 相差 2 分以内），拒绝开源 7B 模型，要求 32B+ 或闭源模型。
- 如果在 > 30 秒的 clip 上、7B 模型下目标 dynamic-FPS > 8，从延迟角度拒绝，并建议降低上限。

输出：一页纸的帧方案，包含 sampler、池化、时序编码、输出格式、benchmark 目标、上下文估算。结尾附上 arXiv 2502.13923（Qwen2.5-VL）与 2306.02858（Video-LLaMA）供对照阅读。
