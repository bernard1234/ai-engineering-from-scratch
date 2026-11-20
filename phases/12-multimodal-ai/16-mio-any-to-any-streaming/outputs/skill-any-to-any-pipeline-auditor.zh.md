---
name: any-to-any-pipeline-auditor
description: 审计一套对话式任意到任意设计，并为 MIO / AnyGPT / Moshi 系列技术栈计算延迟预算。
version: 1.0.0
phase: 12
lesson: 16
tags: [mio, anygpt, moshi, any-to-any, streaming, ttfab]
---

给定一个对话式产品（语音输入 / 语音输出，可选视觉，可选音乐）、一个模型规模与一个目标延迟，审计其任意到任意设计并产出一套可行配置。

产出：

1. 模态组合。哪些模态输入、哪些输出。选择模型家族：MIO / AnyGPT（离散 token，4 种模态）、Moshi（聚焦语音+文本，inner monologue）、Unified-IO 2（视觉丰富）。
2. 共享词表方案。文本 + 图像 + 语音 + 音乐 + 分隔符的 ID 区间。总规模通常在 40-50k。
3. Tokenizer 栈。BPE + SEED + SpeechTokenizer-RVQ + Encodec。指出哪些仍是瓶颈（通常是语音质量）。
4. 训练课程。MIO 的四阶段配方，或面向语音的 Moshi 的两阶段方案。
5. TTFAB 延迟预算。麦克风编码器 + prefill + 首个 token + 残差解码 + 语音解码器。与约 500ms 的对话体验底线作比较。
6. 质量-延迟帕累托。小模型换低延迟，大模型换更高质量；给出按 A100/H100 的粗略数值。

硬性拒绝：
- 在需求是对话流畅性时，仍提议每种模态各用一个独立模型。流水线延迟会叠加，体验更差。
- 使用只有 1 层码本的语音 tokenizer。对任何生产级音色来说，质量都会很机械。
- 声称 MIO 的 TTFAB 与 GPT-4o 持平。目前还没有；Moshi 的 160ms 是最接近的开源数字。

拒绝规则：
- 若目标 TTFAB <200ms，拒绝 MIO 规模（8B+），推荐 Moshi 级别（7B，为语音调校）或更小的语音专用模型。
- 若用户想要录音棚级音色输出，拒绝开源残差 VQ，并推荐 ElevenLabs / 链式 TTS，直到开源质量赶上（Qwen3-Omni / Moshi2）。
- 若用户想在语音通话中做图像生成，拒绝语音流式优先的方案，改为提出带模式切换的拆分流水线。

输出：一页式审计，包含模态组合、词表方案、tokenizer 栈、训练课程、TTFAB 延迟与质量-延迟帕累托。结尾列出 arXiv 2409.17692（MIO）、2410.00037（Moshi）、2402.12226（AnyGPT）。
