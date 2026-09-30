---
name: voice-pipeline
description: 搭建一个 Pipecat 风格的语音流水线（VAD + STT + LLM + TTS + transport），带 barge-in、置信度把关与延迟预算约束。
version: 1.0.0
phase: 14
lesson: 22
tags: [voice, pipecat, livekit, webrtc, latency]
---

给定一个语音产品规格（语言、transport、提供商），搭建一个基于 frame 的流水线。

产出：

1. `Frame` 类型，带 `kind`、`payload`、`direction`（downstream / upstream）。
2. Processors：`VAD`、`STT`、`LLM`、`TTS`、`Transport`。每个带 `process(frame)`。
3. `link()` 辅助函数，把 processor 前向与后向串联。
4. Cancel frame 处理：从 transport 到 TTS 到 LLM 到 STT 的 UPSTREAM 路径，在每个阶段丢弃待处理工作。
5. Observers：每阶段延迟指标；为每个跨 processor 的 frame 发射一个 OTel span（第 23 课）。
6. STT 上的置信度门：低于阈值时，发射一个「请重复」文本 frame 而不是转写。

硬性拒绝：

- 没有 UPSTREAM 处理的流水线。对语音而言 barge-in 不是可选项。
- 不流式的 LLM 调用。first-token 延迟占主导；必须流式。
- 无视置信度的 STT。把错误转写喂给 LLM 会产生错误回复。

拒绝规则：

- 如果冷启动运行时端到端延迟超过 1500ms，拒绝交付。优化链路，或使用 MultimodalAgent（LiveKit 直接音频）。
- 如果产品以电话为先而流水线没有 SIP 适配器，拒绝。通过 LiveKit SIP 或一个平台（Vapi/Retell）路由。
- 如果产品承载 PII 音频且传输中不加密，拒绝。

输出：`frames.py`、`processors.py`、`pipeline.py`、`observers.py`、`README.md`，说明延迟预算、barge-in 设计和 transport 选择。结尾以「接下来读什么」指向第 23 课（OTel）、第 24 课（可观测性后端），或 LiveKit 文档了解 WebRTC 细节。
