# Capstone 03 — 实时语音助手（ASR → LLM → TTS）

> 一个手感对的语音 agent，端到端延迟低于 800ms，知道你已经说完了，能处理 barge-in，还能在不停顿音频的情况下调用工具。Retell、Vapi、LiveKit Agents 和 Pipecat 在 2026 年都达到了这条线。它们的做法形状一致：流式 ASR、turn 检测器、流式 LLM、流式 TTS，全部通过 WebRTC 串起来，每一跳都有激进的延迟预算。构建一个这样的系统，测量 WER、MOS 和误截断率，并在丢包环境下运行它。

**Type:** Capstone
**Languages:** Python（agent + pipeline）、TypeScript（web client）
**Prerequisites:** 第 6 阶段（speech and audio）、第 7 阶段（transformers）、第 11 阶段（LLM engineering）、第 13 阶段（tools）、第 14 阶段（agents）、第 17 阶段（infrastructure）
**Phases exercised:** P6 · P7 · P11 · P13 · P14 · P17
**Time:** 30 小时

## 问题场景

语音是 2025-2026 年演进最快的 AI UX 品类。技术天花板每个季度都在下降。OpenAI Realtime API、Gemini 2.5 Live、Cartesia Sonic-2、ElevenLabs Flash v3、LiveKit Agents 1.0 和 Pipecat 0.0.70 都把 800ms 内的首音输出变得触手可及。但门槛不只是延迟，而是交互手感：不打断用户、不被用户打断、能从一句话中途的插话中恢复、在对话中途调用工具而不卡住音频、能在抖动的移动网络上活下来。

你没法靠拼接三次 REST 调用达到这个水平。架构是端到端的流水线式流式处理。把它造出来，失败模式就会显现：为电话音频调好的 VAD 被背景电视声触发，turn 检测器在等一个永远不会到来的句号，TTS 在发声前缓冲了 400ms。这个 capstone 就是要在负载下逐个修掉这些问题，并发布一份延迟与质量报告。

## 核心概念

流水线有五个流式阶段：**audio in**（来自浏览器或 PSTN 的 WebRTC）、**ASR**（来自 Deepgram Nova-3 或 faster-whisper 的流式部分转写）、**turn detection**（VAD 加一个小的 turn 检测模型，读取部分转写来判断是否说完）、**LLM**（一旦判定 turn 结束就立刻流式输出 token）、**TTS**（在首个 LLM token 之后约 200ms 内开始流式输出音频）。

三个横切关注点。**Barge-in**：当用户在 agent 说话时开口，TTS 取消、ASR 立即接管。**工具使用**：对话中途的函数调用（天气、日历）必须在旁路上运行而不卡住音频；如果延迟超过 300ms，agent 预先插入一个确认词（“稍等一下……”）。**背压**：在丢包情况下，部分转写被暂存，VAD 提高语音门限，agent 避免在消息未被确认时抢话。

度量门槛是量化的。在 15 dB SNR 的 Hamming VAD benchmark 上 WER 低于 8%。100 通实测通话的首音输出 p50 低于 800ms。误截断率低于 3%。TTS 的 MOS 高于 4.2。单台 g5.xlarge 上 50 路并发通话。这些数字就是交付物。

## 架构

```
browser / Twilio PSTN
        |
        v
   WebRTC / SIP edge
        |
        v
  LiveKit Agents 1.0  (or Pipecat 0.0.70)
        |
   +----+--------------+--------------+-----------------+
   |                   |              |                 |
   v                   v              v                 v
  ASR              VAD v5         turn-detector     side-channel
(Deepgram         (Silero)          (LiveKit)        tools
 Nova-3 /         speech-gate    completion score    (weather,
 Whisper-v3)      per 20ms        on partials        calendar)
   |                   |              |
   +--------+----------+--------------+
            v
        LLM (streaming)
     GPT-4o-realtime / Gemini 2.5 Flash /
     cascaded Claude Haiku 4.5
            |
            v
        TTS streaming
     Cartesia Sonic-2 / ElevenLabs Flash v3
            |
            v
     audio back to caller
            |
            v
   OpenTelemetry voice traces -> Langfuse
```

## 技术栈

- 传输：LiveKit Agents 1.0（WebRTC）加 Twilio PSTN 网关；Pipecat 0.0.70 作为备选框架
- ASR：Deepgram Nova-3（流式，首个部分转写低于 300ms）或自托管的 faster-whisper Whisper-v3-turbo
- VAD：Silero VAD v5 加 LiveKit turn-detector（读取部分转写的小型 transformer）
- LLM：紧耦合场景用 OpenAI GPT-4o-realtime，或 Gemini 2.5 Flash Live，或级联 Claude Haiku 4.5（流式 completion，独立音频通路）
- TTS：Cartesia Sonic-2（首字节最低）、ElevenLabs Flash v3，或开源的 Orpheus 用于自托管
- 工具：天气/日历/预订走 FastMCP 旁路；工具耗时 > 300ms 时 agent 预先发出填充语
- 可观测性：OpenTelemetry voice span、带音频回放的 Langfuse voice trace
- 部署：自托管 Whisper + Orpheus 用单台 g5.xlarge（24GB VRAM）；最低延迟则用托管 API

```figure
ce-voice-latency
```

## Build It

1. **WebRTC 会话。** 起一个 LiveKit room 和一个流式传输麦克风音频的 web client。在服务端挂一个加入 room 的 agent worker。

2. **ASR 流式化。** 把 20ms 的 PCM 帧喂给 Deepgram Nova-3（或在 GPU 上的 faster-whisper）。订阅部分转写与最终转写。记录每个部分转写的延迟。

3. **VAD 与 turn 检测器。** 在帧流上跑 Silero VAD v5。在语音结束事件上，用最新的部分转写触发 LiveKit turn-detector。只有当 VAD 判定静音 500ms 且 turn 检测器的完成度得分 > 0.6 时，才提交“turn 结束”。

4. **LLM 流。** turn 结束时，带上进行中的对话加最终转写发起 LLM 调用。流式输出 token。拿到首个 token 就交给 TTS。

5. **TTS 流。** Cartesia Sonic-2 回流音频块。首个音频块必须在首个 LLM token 之后 200ms 内离开服务器。把块推入 LiveKit room；客户端通过 WebRTC 抖动缓冲播放。

6. **Barge-in。** 当 VAD 在 TTS 播放时检测到新的用户语音，立刻取消 TTS 流，丢弃剩余的 LLM 输出，重新武装 ASR。发布一个 `tts_canceled` span。

7. **工具旁路。** 把天气和日历注册为 function-calling 工具。被调用时并发发起调用；如果 300ms 内未返回，让 LLM 说出“稍等，我看一下”作为填充语；工具返回后再继续。

8. **Eval harness。** 录制 100 通通话。计算 WER（对比留出转写）、误截断率（用户说到一半 TTS 被取消）、首音输出 p50、TTS MOS（人工或 NISQA），以及抖动丢包测试（丢弃 3% 的数据包）。

9. **负载测试。** 用合成主叫在单台 g5.xlarge 上压 50 路并发通话。测量持续的首音输出 p95。

## Use It

```
caller: "what is the weather in tokyo tomorrow"
[asr  ] partial @280ms: "what is the"
[asr  ] partial @540ms: "what is the weather"
[turn ] completion score 0.82 at @820ms; commit
[llm  ] first token @960ms
[tool ] weather.tokyo tomorrow -> 68/52 partly cloudy @1140ms
[tts  ] first audio-out @1040ms: "Tokyo tomorrow will be partly cloudy..."
turn latency: 1040ms user-stop -> audio-out
```

## Ship It

`outputs/skill-voice-agent.md` 是交付物。给定一个领域（客户支持、日程安排或自助终端），它搭起一个 LiveKit agent，ASR/VAD/LLM/TTS 流水线按度量门槛调校。评分标准：

| Weight | Criterion | How it is measured |
|:-:|---|---|
| 25 | 端到端延迟 | 100 通录制通话的首音输出 p50 低于 800ms |
| 20 | 轮流对话质量 | Hamming VAD benchmark 上误截断率低于 3% |
| 20 | 工具使用正确性 | 对话中途的工具调用返回正确数据且不卡住音频 |
| 20 | 丢包下的可靠性 | 注入 3% 丢包时的 WER 与轮流稳定性 |
| 15 | Eval harness 完整性 | 公开配置下可复现的测量结果 |
| **100** | | |

## Exercises

1. 在 g5.xlarge 上把 Deepgram Nova-3 换成 faster-whisper v3 turbo。测量延迟与 WER 差距。指出 CPU 与 GPU 的取舍在哪里起作用。

2. 加一个打断仲裁策略：用户在一次工具调用期间插话时 agent 怎么办？比较三种策略（硬取消、完成工具后停止、排队到下一轮）。

3. 跑一个对抗性的 turn 检测测试：让用户在句中长时间停顿。调整 VAD 静音阈值和 turn 检测器分数阈值，以在不超过 900ms 的前提下把误截断降到最低。

4. 通过 Twilio 把同一个 agent 部署到 PSTN。比较 PSTN 与 WebRTC 的首音输出。解释抖动缓冲与编解码器的差异。

5. 为非英语语言（日语、西班牙语）加上语音活动检测。对比 Silero VAD v5 与语言特异性微调模型的误触发率。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Turn detection | “话说完的判定” | 给定 VAD 静音与部分转写，判断用户已说完的分类器 |
| Barge-in | “打断处理” | VAD 检测到新的用户语音时在播放中途取消 TTS |
| First-audio-out | “延迟” | 从用户停止说话到首个音频包离开服务器的时间 |
| VAD | “语音门” | 把音频帧分类为语音或静音的模型；2026 年的默认是 Silero VAD v5 |
| Jitter buffer | “音频平滑” | 客户端缓冲，短暂持有数据包以吸收网络抖动 |
| Filler | “确认词” | 工具较慢时 agent 发出的短句，以避免沉默 |
| MOS | “平均意见分” | 感知语音质量评分；NISQA 是自动化代理指标 |

## Further Reading

- [LiveKit Agents 1.0](https://github.com/livekit/agents) — 参考 WebRTC agent 框架
- [Pipecat](https://github.com/pipecat-ai/pipecat) — 备选的 Python 优先流式 agent 框架
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime) — 集成式语音模型的参考
- [Deepgram Nova-3 documentation](https://developers.deepgram.com/docs) — 流式 ASR 参考
- [Silero VAD v5](https://github.com/snakers4/silero-vad) — VAD 参考模型
- [Cartesia Sonic-2](https://docs.cartesia.ai) — 低延迟 TTS 参考
- [Retell AI architecture](https://docs.retellai.com) — 生产级语音 agent 架构
- [Vapi.ai production stack](https://docs.vapi.ai) — 另一个生产参考
