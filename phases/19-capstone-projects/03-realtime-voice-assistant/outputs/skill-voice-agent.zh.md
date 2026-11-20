---
name: voice-agent
description: 构建一个实时语音 agent，首音输出低于 800ms，支持 barge-in 处理和对话中途的工具使用。
version: 1.0.0
phase: 19
lesson: 03
tags: [capstone, voice, webrtc, livekit, pipecat, asr, tts, streaming]
---

给定一个领域（客户支持、日程安排、零售助理），部署一个 WebRTC 语音 agent，让端到端首音输出保持在 800ms 以内，同时能处理 barge-in、工具调用和丢包。

构建计划：

1. 搭起一个 LiveKit Agents 1.0 room，配一个流式传输麦克风音频的 web client。加上 Twilio PSTN 网关以覆盖电话。
2. 运行流式 ASR（托管的 Deepgram Nova-3，或在 g5.xlarge 上的 faster-whisper Whisper-v3-turbo）。订阅部分转写与最终转写。
3. 在 20ms 帧上运行 Silero VAD v5。语音结束时，用 LiveKit turn-detector 对最新的部分转写打分；只有 VAD 静音 >= 500ms 且完成度得分 >= 0.6 时才提交 turn 结束。
4. 流式调用 LLM（GPT-4o-realtime、Gemini 2.5 Flash Live，或级联 Claude Haiku 4.5）。在 200ms 内把首个 token 交给 TTS。
5. 流式 TTS（Cartesia Sonic-2 或 ElevenLabs Flash v3）。首个音频块必须在首个 LLM token 后的 200ms 内离开服务器。
6. Barge-in：当 VAD 在 SPEAKING 或 THINKING 期间检测到新的用户语音，取消 TTS、丢弃剩余的 LLM 输出、重新武装 ASR。发布一个 `tts_canceled` span。
7. 工具旁路：并发运行函数调用；如果延迟 > 300ms，就发出一个确认填充语，让音频流永不中断。
8. 录制 100 通通话。测量对比留出转写的 WER、Hamming VAD benchmark 上的误截断率、首音输出 p50、NISQA MOS，以及 3% 丢包下的行为。
9. 用合成主叫在单台 g5.xlarge 上压 50 路并发通话；报告持续的首音输出 p95。

Assessment rubric:

| Weight | Criterion | Measurement |
|:-:|---|---|
| 25 | 端到端延迟 | 100 通录制通话的首音输出 p50 低于 800ms |
| 20 | 轮流对话质量 | Hamming VAD benchmark 上误截断率低于 3% |
| 20 | 工具使用正确性 | 对话中途的工具调用返回正确数据且不卡住音频 |
| 20 | 丢包下的可靠性 | 注入 3% 丢包时的 WER 与轮流稳定性 |
| 15 | Eval harness 完整性 | 公开配置下可复现的测量结果 |

Hard rejects:

- 非流式流水线（批处理 ASR、批处理 TTS）达不到延迟目标。
- 任何不立刻取消 TTS 缓冲的 barge-in 策略。延迟取消会造成最严重的用户体验回退。
- 同步阻塞 LLM 流的工具调用。它们必须在旁路上运行。

Refusal rules:

- 拒绝在没有 VAD 或 turn-detector 的情况下部署。固定超时的轮流机制会产生不可接受的截断率。
- 拒绝在未说明是人评还是 NISQA 代理值的情况下报告 MOS。
- 拒绝在少于 100 通录制通话、且未公开通话 trace 的情况下报告“p50 延迟低于 X”。

Output：一个 repo，包含 LiveKit agent worker、PSTN 网关配置、100 通通话的 eval harness、一个公开的 Langfuse voice 仪表盘、与一个托管竞品（Retell、Vapi 或直接使用 OpenAI Realtime API）的并排对比，以及一篇关于你观察到的三大轮流对话失败及其检测器调参修复的说明。
