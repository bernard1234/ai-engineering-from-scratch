# 语音 Agent：Pipecat 与 LiveKit

> 2026 年，语音 agent 是一等公民的生产品类。Pipecat 给你一个基于 frame 的 Python 流水线（VAD → STT → LLM → TTS → transport）。LiveKit Agents 通过 WebRTC 把 AI 模型桥接到用户。高端技术栈的端到端生产延迟目标落在 450–600ms。

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 12 (Workflow Patterns)
**Time:** ~60 minutes

## 学习目标

- 描述 Pipecat 基于 frame 的流水线：DOWNSTREAM（源→汇）与 UPSTREAM（控制）。
- 说出规范的语音流水线各阶段，以及 Pipecat 支持哪些 transport。
- 解释 LiveKit Agents 的两个语音 agent 类（MultimodalAgent、VoicePipelineAgent）以及各自适用场景。
- 总结 2026 年的生产延迟预期，以及它们如何驱动架构选择。

## 问题

语音 agent 不是「文本循环 + 后加的 TTS」。延迟预算是严苛的（约 600ms），部分音频是默认状态，turn 检测本身是一个模型，transport 从电话 SIP 到 WebRTC 各不相同。要么你构建一个基于 frame 的流水线（Pipecat），要么你依赖一个平台（LiveKit）。

## 概念

### Pipecat（pipecat-ai/pipecat）

- Python 的基于 frame 的流水线框架。
- `Frame` → `FrameProcessor` 链。
- 两个流向：
  - **DOWNSTREAM** —— 源 → 汇（音频进，TTS 出）。
  - **UPSTREAM** —— 反馈与控制（取消、指标、barge-in）。
- `PipelineTask` 通过事件（`on_pipeline_started`、`on_pipeline_finished`、`on_idle_timeout`）和 observer（用于指标/tracing/RTVI）管理生命周期。

典型流水线：

```
VAD (Silero) → STT → LLM (context alternates user/assistant) → TTS → transport
```

Transports：Daily、LiveKit、SmallWebRTCTransport、FastAPI WebSocket、WhatsApp。

Pipecat Flows 增加了结构化对话（状态机）。Pipecat Cloud 是托管运行时。

### LiveKit Agents（livekit/agents）

- 通过 WebRTC 把 AI 模型桥接到用户。
- 关键概念：`Agent`、`AgentSession`、`entrypoint`、`AgentServer`。
- 两个语音 agent 类：
  - **MultimodalAgent** —— 通过 OpenAI Realtime 或等效方案直接音频。
  - **VoicePipelineAgent** —— STT → LLM → TTS 级联；提供文本级控制。
- 通过 transformer 模型做语义 turn 检测。
- 原生 MCP 集成。
- 通过 SIP 接电话。
- 通过 LiveKit Inference 免 API key 使用 50+ 模型；通过插件再支持 200+。

### 商业平台

Vapi（在优化过的高端技术栈上约 450–600ms）和 Retell（跨 180 次测试通话端到端约 600ms）都构建在这些之上。当你想要一个托管的语音技术栈、又不想养一个 WebRTC 团队时，选平台。

### 这个模式在哪里会出错

- **没有 barge-in 处理。** 用户打断；agent 继续说话。需要在 Pipecat 中用 UPSTREAM cancel frame，LiveKit 中也有等价物。
- **忽略 STT 置信度。** 低置信度的转写被当作真理喂给 LLM。按置信度把关或请求确认。
- **TTS 中途截断。** 当流水线在话语中途取消时，TTS 需要知道并切掉音频。
- **忽略延迟预算。** 每个组件增加 50–200ms。交付前先求和你的链路。

### 2026 年典型延迟

- VAD：20–60ms
- STT partial：100–250ms
- LLM first token：150–400ms
- TTS first audio：100–200ms
- Transport RTT：30–80ms

端到端 450–600ms 是高端。800–1200ms 是常态。超过 1500ms 会让人觉得坏了。

```figure
voice-pipeline
```

## Build It

`code/main.py` 是一个基于 frame 的玩具流水线，包含：

- `Frame` 类型（audio、transcript、text、tts_audio、control）。
- 带 `process(frame)` 的 `Processor` 接口。
- 一个五阶段流水线（VAD → STT → LLM → TTS → transport），以脚本化 processor 实现。
- 一个 UPSTREAM cancel frame 来演示 barge-in。

运行它：

```
python3 code/main.py
```

trace 展示正常流程，以及一次在话语中途停止 TTS 的 barge-in 取消。

## Use It

- 完全控制用 **Pipecat** —— 自定义 processor、Python 优先、可插拔提供商。
- WebRTC 优先部署和电话用 **LiveKit Agents**。
- 没有 WebRTC 团队的托管语音 agent 用 **Vapi / Retell**。
- 直接音频进/音频出用 **OpenAI Realtime / Gemini Live**（MultimodalAgent）。

## Ship It

`outputs/skill-voice-pipeline.md` 搭建一个 Pipecat 风格的语音流水线，带 VAD + STT + LLM + TTS + transport 以及 barge-in 处理。

## 练习

1. 给你的玩具流水线加一个指标 observer：统计每秒每阶段的 frame 数。延迟在哪里累积？
2. 实现置信度把关的 STT：低于阈值时，请求「你能重复一遍吗？」
3. 加语义 turn 检测：简单规则——如果转写以「？」结尾，就是 turn 结束。
4. 阅读 Pipecat 的 transport 文档。把标准库 transport 换成 SmallWebRTCTransport 配置（stub）。
5. 在同一查询上测量 OpenAI Realtime vs STT+LLM+TTS 级联。文本级控制带来了多少延迟成本？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Frame | 「事件」 | 流水线中类型化的数据单元（audio、transcript、text、control） |
| Processor | 「流水线阶段」 | 带 process(frame) 的处理器 |
| DOWNSTREAM | 「前向流」 | 源到汇：音频进，语音出 |
| UPSTREAM | 「反馈流」 | 控制：取消、指标、barge-in |
| VAD | 「语音活动检测」 | 检测用户是否在说话 |
| Semantic turn detection | 「智能话轮结束」 | 基于模型的判断用户已说完 |
| MultimodalAgent | 「直接音频 agent」 | 音频进、音频出；中间没有文本 |
| VoicePipelineAgent | 「级联 agent」 | STT + LLM + TTS；文本级控制 |

## 延伸阅读

- [Pipecat 文档](https://docs.pipecat.ai/getting-started/introduction) —— 基于 frame 的流水线、processor、transport
- [LiveKit Agents 文档](https://docs.livekit.io/agents/) —— WebRTC + 语音原语
- [Vapi](https://vapi.ai/) —— 托管语音平台
- [Retell AI](https://www.retellai.com/) —— 托管语音、延迟基准测试
