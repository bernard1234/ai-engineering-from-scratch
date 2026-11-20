# 音频语言模型：从 Whisper 到 Audio Flamingo 3 的演进弧线

> Whisper（Radford 等，2022 年 12 月）终结了语音识别这一课题——68 万小时弱监督多语种语音、一个简单的 encoder-decoder Transformer、一个让之后每一次 ASR 发布都引用它的 benchmark。但识别不等于推理。问"这段录音里有哪些乐器"、"说话人表达了什么情绪"、"第 3 分钟发生了什么"，需要的是音频理解，而不是转写。Qwen-Audio、SALMONN、LTU 以及 NVIDIA 的 Audio Flamingo 3（AF3，2025 年 7 月）逐步搭起了这层栈：保留 Whisper 级的 encoder，挂上 Q-former，在音频-文本指令数据上训练，再加进 chain-of-thought 推理。本课走一遍这条演进弧线。

**Type:** Build
**Languages:** Python（stdlib，log-Mel 频谱图 + 音频 Q-former 骨架）
**Prerequisites:** Phase 6（语音与音频）、Phase 12 · 03（Q-Former）
**Time:** ~180 分钟

## Learning Objectives

- 从 waveform 计算 log-Mel 频谱图：加窗、FFT、滤波器组、log 变换。
- 比较 encoder 的几种选型：Whisper encoder、BEATs、AF-Whisper 混合方案。各自在什么情况下胜出。
- 搭一个音频 Q-former：N 个可学习 query 对频谱图 patch 做 cross-attention。
- 解释级联式（Whisper 再 LLM）与端到端音频-LLM 训练的区别：为什么端到端在推理上扩展性更好。

## 问题场景

语音识别已经被 Whisper 解决。音频的 OCR 已是商品。但"商品"止步于转写。如果模型无法对它听到的内容进行推理——时间、说话人、情绪、音乐结构、环境声音——单靠转写撑不起产品功能。

三条显而易见的路线：

1. 级联：Whisper 转写，LLM 在 transcript 上推理。适用于纯语音场景。在音乐、环境音频、多说话人重叠、情绪上失效。

2. 端到端音频-LLM：音频 encoder 把音频 token 直接送进 LLM，跳过转写。保留声学信息（情绪、说话人、环境）。需要新的训练数据。

3. 混合：音频 encoder + 文本 decoder，既能转写也能推理。Qwen-Audio 和 Audio Flamingo 走这条路线。

## 核心概念

### Log-Mel 频谱图：输入特征

每个音频 encoder 都从同一个特征开始：log-Mel 频谱图。

1. 重采样到 16 kHz。
2. 短时傅里叶变换，25ms 窗，10ms hop。
3. 取 FFT 结果的幅度。
4. 应用 Mel 滤波器组（通常是 80 个、在 0-8000 Hz 上对数间隔的滤波器），把频率 warp 到感知刻度。
5. 做 log 压缩（log(1 + x)）以处理动态范围。

结果：一个形状为 (T, 80) 的二维数组，其中 T 是时间帧数。对一个 30 秒片段、100 Hz 帧率：(3000, 80)。

### Whisper 的 encoder

Whisper 的 encoder 是一个 12 层 ViT 风格 Transformer，把 log-Mel 频谱图当作时间帧序列来处理。输出：每个时间帧一个 hidden state 向量。

就 ASR 而言，Whisper 的 decoder 是一个 cross-attention Transformer，以 encoder 输出为条件生成文本 token。标准 encoder-decoder。

对 ALM（音频-LLM）而言，你要的是把 encoder 输出作为另一个 LLM 的输入。模式是：Whisper encoder 冻结，Q-former 可训练，LLM 冻结或微调。

### BEATs 与音频专用 encoder

Whisper 是在语音主导的数据上训练的。它在音乐和环境音频上更弱。

BEATs（Chen 等，2022）是一个在 AudioSet 上训练的自监督 Transformer。在相同参数量下，它对音乐和环境声音的捕捉优于 Whisper。

AF-Whisper（Audio Flamingo 3 的混合方案）：把 Whisper + BEATs 特征拼接作为音频输入。Whisper 承载语言信号，BEATs 承载声学信号。

### 音频 Q-former

与 BLIP-2 的视觉 Q-former 相同的模式。固定数量的可学习 query（通常是 32 或 64）对音频 encoder 的输出帧做 cross-attention。这些 query 变成由 LLM 消费的音频 token。

训练对齐阶段：只训 Q-former，在音频-文本对（AudioCaps、Clotho）上用对比损失 + captioning 损失。指令阶段：端到端，解冻 LLM，在指令数据上训练。

### 演进弧线——SALMONN、Qwen-Audio、AF3

SALMONN（Tang 等，2023）：Whisper + BEATs + Q-former + LLaMA。第一个具备严肃推理能力的开源音频-LLM。在 MMAU 上的 benchmark 显示综合分约 0.55。

Qwen-Audio（Chu 等，2023）：架构相似，在更丰富的数据集上训练，为多轮对话调优。MMAU 约 0.60。

LTU——Listen, Think, Understand（Gong 等，2023）：显式推理数据，聚焦对音频片段的 chain-of-thought。规模更小但更聚焦。

Audio Flamingo 3（Goel 等，2025 年 7 月）：当前开源 SOTA。8B LLM 主干（Qwen2 7B）、Whisper-large encoder 拼接 BEATs、64-query Q-former，在 100 万+ 音频-文本指令对上训练。MMAU 0.72，在某些子任务上追平闭源前沿模型。

AF3 还为音频引入了按需 chain-of-thought：模型可以选择性地在最终回答前输出思考 token（"让我先辨认一下乐器：……"）。开启思考后，复杂推理任务的准确率提升 3-5 个点。

### 级联 vs 端到端

级联流水线：

1. Whisper 把音频转写为 → 文本。
2. LLM 在文本上推理。

对"总结这期播客"完美适用。但在以下场景失效：
- "这首歌的情绪是什么？"——情绪在声音里，不在文字里。
- "是谁在说话，Alice 还是 Bob？"——需要说话人识别。
- "爆炸发生在第几秒？"——时间 grounding 在文本中丢失。
- "这是真实音频还是生成的？"——deepfake 检测需要声学特征。

端到端保留声学信号。Qwen-Audio 和 AF3 原生处理音乐、环境和情绪。

### 2026 年的生产配方

对一个新的音频理解产品：

- 选级联，如果：目标是转写，没有音乐，不需要情绪推断。
- 选 AF3 / Qwen-Audio 家族，如果：涉及音乐、情绪、多说话人或复杂音频推理。

级联更便宜也更简单。端到端能力更强。

### MMAU——音频推理 benchmark

MMAU（Massive Multimodal Audio Understanding）是 2024-2025 年的音频推理 benchmark：

- 10,000 个音频-文本 QA 对，覆盖语音、音乐、环境声音。
- 覆盖分类、时间推理、因果推理、开放式 QA。
- 测试的正是级联流水线系统性缺失的那些能力。

开源 SOTA（AF3）为 0.72；闭源前沿约 0.78（Gemini 2.5 Pro、Claude Opus 4.7）。这个差距小于 VideoMME 的开源对闭源差值，说明音频-LLM 正在成熟。

```figure
audio-text-ctc
```

## Use It

`code/main.py`:

- 用 stdlib 实现 log-Mel 频谱图计算：加窗、朴素 DFT、Mel 滤波器组。
- 音频 Q-former 骨架：给定 encoder 输出帧，计算 Q、K、V、注意力，并输出 N 个 token。
- 在一个玩具任务上做级联与端到端的对比。

## Ship It

本课产出 `outputs/skill-audio-llm-pipeline-picker.md`。给定一个音频任务（转写、音乐标注、情绪推断、多说话人 diarization、环境分类），它在级联、端到端 AF3 或混合方案之间做出选择。

## Exercises

1. 计算一个 30 秒片段在 16kHz、25ms 窗、10ms hop、80 个 Mel bin 下的 log-Mel 频谱图维度。换成 48kHz 会怎么变？

2. 为什么 Whisper 在音乐上表现不佳？BEATs 捕捉了哪些 Whisper 没捕捉到的音频特征？

3. 64 个 query 的音频 Q-former 对比 32 个：在什么任务复杂度下 64 个才划算？32 个又为哪些场景省下了算力？

4. 阅读 AF3 第 4 节关于按需思考的部分。提出三个 chain-of-thought 帮助最大的音频任务。

5. 用 AF3 的输出实现一个最小 diarization 流水线。你如何标示说话人的切换？

## Key Terms

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Log-Mel spectrogram | "Mel features" | Mel 滤波器组之后得到的二维（时间、频率）对数幅度数组 |
| Audio Q-former | "Audio Perceiver" | 从音频 encoder 输出到定长 query 的 cross-attention 瓶颈，query 再喂给 LLM |
| Cascaded | "ASR-then-LLM" | Whisper 转写、文本 LLM 推理的流水线；会丢失声学信息 |
| End-to-end | "Audio-LLM" | 音频特征经 Q-former 直接进入 LLM；保留声学信号 |
| BEATs | "Audio AudioSet encoder" | 在 AudioSet 上训练的自监督 Transformer；在音乐 + 环境声音上很强 |
| MMAU | "Audio reasoning bench" | 覆盖语音、音乐、环境的 1 万条 QA 对；2024 年的评测标准 |
| On-demand thinking | "Audio CoT" | 模型可选择性在最终回答前输出推理 token，准确率提升 3-5 个点 |

## Further Reading

- [Radford et al. — Whisper (arXiv:2212.04356)](https://arxiv.org/abs/2212.04356)
- [Chu et al. — Qwen-Audio (arXiv:2311.07919)](https://arxiv.org/abs/2311.07919)
- [Goel et al. — Audio Flamingo 3 (arXiv:2507.08128)](https://arxiv.org/abs/2507.08128)
- [Tang et al. — SALMONN (arXiv:2310.13289)](https://arxiv.org/abs/2310.13289)
- [Gong et al. — LTU (arXiv:2305.10790)](https://arxiv.org/abs/2305.10790)
