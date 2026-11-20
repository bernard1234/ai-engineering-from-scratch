# Omni 模型：Qwen2.5-Omni 与 Thinker-Talker 拆分

> GPT-4o 在 2024 年 5 月的产品演示之所以具有颠覆性，不是因为底层模型，而是因为产品形态——一种语音界面：你说话，模型看到摄像头看到的东西，并在 250ms 内回话。整个开源生态在此后 2024 和 2025 年的余下时间里竞相追赶这个产品面。Qwen2.5-Omni（2025 年 3 月）是开源设计的参照：一个 Thinker（大型文本生成 Transformer）加一个 Talker（并行的语音生成 Transformer），二者通过流式 speech token 相连。Mini-Omni 把它简化，Moshi 在延迟上追平，GLM-4-Voice 把它扩展到中文。本课解读 Thinker-Talker 架构，以及让流式实时对话得以成立的那份延迟预算。

**Type:** Build
**Languages:** Python（stdlib，流式流水线延迟模拟器 + VAD 循环）
**Prerequisites:** Phase 12 · 19（audio-LLM）、Phase 12 · 16（any-to-any）
**Time:** ~180 分钟

## Learning Objectives

- 把推理流水线拆成 Thinker（文本推理）与 Talker（语音合成），并解释为什么并行流式能成立。
- 逐组件地为一个对话交互计算首字节音频延迟（TTFAB）预算。
- 描述 TMRoPE 在 Thinker 内部对视觉、音频、文本做的时间对齐位置编码。
- 说出三种实时对话模式：半双工、轮次交替、全双工。

## 问题场景

一个实时语音助手必须在很短的时间内做很多事：

1. 听用户。实时的语音 tokenization、voice activity detection（VAD）来判断用户何时说完。
2. 可选地看。摄像头输入 2-4 FPS，与音频一起流式送进 Thinker。
3. 思考。以对话历史为条件组织一个回复。
4. 说话。合成音频 token，解码为 waveform，流式送到用户的扬声器。

每一步都在增加延迟。对话感要求总往返 < 500ms——低于这个值，用户就不再察觉卡顿。GPT-4o 声称约 250ms。Moshi 约 160ms。Qwen2.5-Omni 约 350-500ms。

每个组件都必须流式。任何环节都不能"全部攒批、最后再解码"。

## 核心概念

### Thinker 与 Talker

Qwen2.5-Omni 的拆分：

- Thinker：一个 7B-80B 的文本生成 Transformer。消费交错的文本 + 图像 + 音频 token。输出代表"要说什么"的文本 token。
- Talker：一个更小的语音生成 Transformer（200M-1B）。消费 Thinker 输出的文本 token 以及近期的语音上下文 token。输出离散 speech token（residual-VQ 索引）。
- 语音 decoder：一个流式 waveform decoder（SNAC、MoVQGAN 家族），实时把 speech token 变成音频采样点。

这个拆分至关重要。Thinker 必须够大，推理才够好。Talker 可以很小，因为它的工作是局部的——把文本转成 speech token。更大的 Talker 并不会更有表现力；只会更慢。

两者并行运行：

1. Thinker 输出文本 token t_i。
2. Talker 消费 t_i（通过流式），并输出 speech token s_i, s_{i+1}, ..., s_{i+k}。
3. 语音 decoder 一边接收 speech token 一边输出音频采样点。
4. 当 Thinker 推进到文本 token t_{i+3} 时，Talker 已经把 t_0..t_{i+2} 的音频流式送出了。

### TMRoPE——时间对齐的多模态位置

Thinker 需要整合图像帧（比如以 4 FPS 到达）、音频帧（以 50 帧/秒到达）以及来自对话历史的文本。朴素的序列顺序（先全部图像、再全部音频、最后文本）会丢失时间对齐。

TMRoPE 给每个 token 分配绝对时间戳。视觉 token 在 t=2.3s。音频 token 在 t=2.32s。用户说"stop"的文本 token 在 t=2.35s。RoPE 按时间戳旋转注意力；模型把它们视为在时间上同时发生。

正是这套基础设施让"他一边打招呼一边挥手"这类情形得以工作——模型在同一概念时刻看到视频帧和音频。

### 流式语音合成

speech token 必须流式输出。Mini-Omni（Xie & Wu，2024）提出了"语言模型可以在流式中边听边说边思考"：Thinker 的输出 token 与 Talker 的输出 token 交织在同一序列里。Thinker 一旦确定下一个文本 token，Talker 就立即触发。没有批次边界。

Moshi（Défossez 等，2024 年 10 月）是最快的开源实现。单张 A100 上 160ms TTFAB。架构：单个 7B Transformer 在交替位置上输出文本 token 和 speech token，用一个"inner monologue"把思考流与说话流分开。这实际上是把 Thinker + Talker 融合进一个模型，并配以精心设计的训练。

### VAD 与轮次交替

voice activity detection 在输入端运行。两种模式：

- 半双工：用户说话，模型听。模型说话，用户听。通过 VAD 静音检测（约 200ms）实现清晰的交接。
- 全双工：双方可以同时说话。模型可以附和（"uh-huh"）或打断。难得多。Moshi 支持这一模式。

Qwen2.5-Omni 默认支持半双工，通过静音阈值实现轮次交替。全双工需要应用层自行处理。

### Qwen3-Omni（2025 年 11 月）

继任者。Qwen3-80B Thinker、更大的 Talker、改进的 TMRoPE-v2。延迟接近 GPT-4o 的 250ms。开放权重。OmniBench 上的 benchmark 与 Gemini 2.0 Live 相当。

### 生产环境延迟预算

对一次典型的流式交互：

- 麦克风 -> 音频 token：40-80ms。
- Prefill（prompt + 历史）：7B 上是 100-200ms，70B 上要多得多。
- Thinker 首个文本 token：40ms。
- Talker 处理首个文本 token：20ms。
- 首批 speech token 确定：40ms。
- Residual-VQ 解码：30ms。
- 语音 waveform 解码：50-80ms。

TTFAB 合计：7B 上 320-510ms，70B 上 600-900ms。前沿质量通常意味着 70B+；这就是前沿模型延迟差距的来源。

### Token 速率算术

在 16kHz 语音、50 Hz 基础 speech token 的情况下，每秒输出需要 50 个 speech token。Talker 必须达到 ≥50 tok/s 才能跟上。在 H100 上典型的 LLM 吞吐为 30-80 tok/s，一个小型（200-300M）Talker 足够快；7B 的 Talker 则会掉队。

这就是为什么需要专门的小型 Talker 模型，而不是"直接用主模型"。

```figure
l5-thinker-talker
```

## Use It

`code/main.py`:

- 用模拟的 token 输出速率仿真一条 Thinker-Talker 流水线。
- 为可配置的模型尺寸和麦克风采样率计算 TTFAB。
- 用 VAD 静音阈值演示半双工轮次交替。

## Ship It

本课产出 `outputs/skill-omni-streaming-budget.md`。给定一个实时语音产品的目标 TTFAB 和功能集（视觉输入、双语、全双工），它在 Qwen2.5-Omni、Qwen3-Omni、Moshi 或 Mini-Omni 中做选择，并给出 Thinker/Talker 的规模。

## Exercises

1. 你的目标 TTFAB 是 300ms。在 7B Thinker 和 300M Talker 上，写出每个组件的延迟。

2. Qwen2.5-Omni 使用 TMRoPE。描述在这样一个 prompt 下模型看到什么：用户从 t=1s 开始说话，摄像头在 t=1.2s 捕捉到一个手势。

3. 全双工支持要求模型在听的同时输出音频。提出一种能教会它这一点的训练数据格式。

4. 阅读 Moshi 论文第 4 节。描述"inner monologue"的分离方式，以及它为什么避开了 Thinker-Talker 拆分。

5. 计算吞吐预算：要在 16kHz 语音、50 个基础层 token/秒的条件下跟上，Talker 必须以多快的速度输出 token？

## Key Terms

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Thinker | "Reasoning brain" | 产出"要说什么"的大型文本生成 Transformer |
| Talker | "Speech-generating mouth" | 从 Thinker 的文本产出离散 speech token 的小型 Transformer |
| TTFAB | "Latency budget" | Time-to-first-audio-byte：从用户说完到第一个音频采样点输出 |
| TMRoPE | "Time-aligned RoPE" | 在视觉、音频、文本上使用绝对时间戳的位置编码 |
| Half-duplex | "Turn-taking" | 用户与模型轮流；VAD 静音检测判断用户说完 |
| Full-duplex | "Simultaneous" | 模型可以同时说话和聆听；具备附和能力 |
| Inner monologue | "Moshi separation" | 思考流与说话流交织的单模型设计 |

## Further Reading

- [Xu et al. — Qwen2.5-Omni (arXiv:2503.20215)](https://arxiv.org/abs/2503.20215)
- [Qwen Team — Qwen3-Omni (arXiv:2509.17765)](https://arxiv.org/html/2509.17765v1)
- [Xie & Wu — Mini-Omni (arXiv:2408.16725)](https://arxiv.org/abs/2408.16725)
- [Défossez et al. — Moshi (arXiv:2410.00037)](https://arxiv.org/abs/2410.00037)
- [Zeng et al. — GLM-4-Voice (arXiv:2412.02612)](https://arxiv.org/abs/2412.02612)
