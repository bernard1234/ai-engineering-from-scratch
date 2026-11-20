# 视频-语言模型：时序 token 与 grounding

> 视频不是一叠照片。一段 5 秒的片段里包含因果顺序、动作动词和事件时序，这些是图像模型无法表示的。Video-LLaMA（Zhang et al., 2023 年 6 月）发布了第一个具备音视频 grounding 能力的开源 video-LLM。VideoChat 和 Video-LLaVA 把这一模式推广开来。到 2025 年，Qwen2.5-VL 的 TMRoPE 已经追平了前沿闭源模型。每个系统解决时序 token 的方式都不同——per-clip 的 Q-former、per-frame 的 concat-pool、per-token 的 TMRoPE。本节课解读这些模式，构建一个 uniform 与 dynamic 对照的 frame sampler，并在 temporal grounding 任务上做评估。

**Type:** Build
**Languages:** Python（stdlib，frame sampler + temporal-grounding evaluator）
**Prerequisites:** Phase 12 · 08（LLaVA-OneVision）
**Time:** ~180 分钟

## Learning Objectives

- 解释为什么时序位置编码会独立于视觉 encoder 改变 video VLM 的性能。
- 在 tokens-per-second 与 grounding 准确率两个维度上比较 uniform、dynamic-FPS 和 event-driven 三种帧采样方式。
- 描述 Q-former-per-clip（Video-LLaMA）、pooled-per-frame（Video-LLaVA）与 M-RoPE-per-token（Qwen2.5-VL）三种设计。
- 说出四个视频 benchmark 的名字：VideoMME、TempCompass、EgoSchema、Video-MMMU。

## 问题场景

一段 1 分钟、30 FPS 的视频有 1800 帧。以每帧 196 个视觉 token 计算（224 分辨率下的 ViT-B），就是 352k token——比 2024 年任何 LLM 的上下文都大。

存在三种削减策略：

1. 对帧做子采样（视内容而定，1-8 FPS）。
2. 对每帧的 patch token 做激进池化（3x3 或 4x4 双线性池化）。
3. 用 Q-former 压缩：吃进一个 16 帧的 clip，输出 64 个 token。

每种取舍都不一样。子采样丢失时序细节。池化丢失空间细节。Q-former 两样都丢一点，但省下 token。

时序位置编码是另一个维度：模型怎么知道第 5 帧在第 6 帧之前？可选项包括简单的一维时序 RoPE（Video-LLaMA）、可学习的时序 embedding（Video-LLaVA），以及 TMRoPE（Qwen2.5-VL，完整 3D）。

## 核心概念

### Video-LLaMA：每个 clip 一个 Q-former + 音频分支

Video-LLaMA（2023）是第一个开源 video-LLM。架构：

- 2 FPS 的 16 帧 clip（即 8 秒）。
- 逐帧 ViT 特征 -> Video Q-former 对全部 16 帧做 cross-attention -> 32 个可学习 query -> LLM。
- 并行的音频分支：波形 -> ImageBind 音频 encoder -> Audio Q-former -> 32 个 query -> LLM。

优势：音视频联合推理。劣势：clip 长度固定，无法做任意时间点的 grounding。

### VideoChat 与 Video-LLaVA

VideoChat 保留了 Video-LLaMA 的思路，但去掉了音频并做了简化。Video-LLaVA（Lin et al., 2023）在图像和视频帧上训练同一个视觉 encoder（"先对齐再投影"），得到统一表示。两者都是冻结 CLIP encoder + MLP + LLM。

两者都处理不了长视频。两者都是 8-16 帧的系统。

### Qwen2.5-VL 与 TMRoPE

Qwen2.5-VL 引入了 TMRoPE——Temporal-Modality Rotary Position Embedding。每个 patch token 携带一个 (t, h, w) 位置，其中 t 是真实时间戳（而非帧索引）。

与简单时序 embedding 的关键区别：

- 是绝对时间，不是索引。模型看到的是"在 4.2 秒处"，不是"在第 15 帧"。
- 是逐 token 旋转，不是逐 clip。每个视觉 token 按自己的时间戳独立旋转。
- 兼容动态 FPS。如果你这里按 2 FPS 采样、那里按 4 FPS 采样，TMRoPE 原生就能处理这种不均匀间隔。

TMRoPE 支持"猫是在第几秒跳起来的？"这类查询。模型可以输出"在 4.2 秒"。Video-LLaMA 只能回答"在片段靠前的位置"。

### 帧采样策略

Uniform：在时长内均匀采 N 帧。简单，但会错过运动峰值。

Dynamic FPS：根据运动强度自适应采样。光流或帧差法挑出高运动片段做更密的采样。Qwen2.5-VL 就是用这种方式训练的。

Event-driven：跑一个轻量检测器，在动作发生的地方多采。VideoAgent 用了这种方式。

Keyframe + context：在镜头边界处采样，再加几帧相邻帧。用于影视类内容。

### 逐帧池化

在 1 FPS、每帧 576 token 的情况下，一段 5 分钟的片段是 172,800 token。Qwen2.5-VL-72B 的 128k 上下文装得下，但很贵。

3x3 双线性池化会降到每帧 64 token -> 5 分钟共 19,200 token。这是大多数任务的最佳区间。

对 agent 工作流可以更激进（6x6 -> 每帧 16 token），因为那里空间细节没那么重要。

### 四大视频 benchmark

- VideoMME：综合视频理解，短 + 中 + 长。
- TempCompass：细粒度时序推理，"之前" / "之后"类问题。
- EgoSchema：长时程第一人称视频。
- Video-MMMU：多模态多学科视频问答。

一次完整的 video-VLM 评测会覆盖这四项。它们压测的是不同维度——TempCompass 全是关于顺序，EgoSchema 是关于 3 分钟以上的推理，VideoMME 则跨越各种时长。

### Grounding 的输出格式

temporal grounding 的输出格式：

- 自由文本："猫大约在第 4 秒跳起来。"好解析但不精确。
- 结构化 JSON：`{"event": "jump", "start": 4.1, "end": 4.3}`。Qwen2.5-VL 就是按这个训练的。
- 基于 token：在答案中穿插特殊的 `<time>4.1</time>` token。这是 Qwen2.5-VL 的内部格式。

基于 token 的方式对下游使用最精确。Qwen2.5-VL 的 JSON 输出格式可以直接解析。

### 2026 年的最佳实践

2026 年做 video VLM：

- Encoder：SigLIP 2 搭配 M-RoPE 或 TMRoPE（Qwen2.5-VL）。
- 帧采样：dynamic FPS（视运动情况取 1-4），并设最大帧数上限。
- 逐帧池化：3x3 双线性。
- 输出：含时间与事件字段的结构化 JSON。
- Benchmark：通用用 VideoMME + TempCompass；长时程用 EgoSchema。

```figure
video-temporal-patches
```

## Use It

`code/main.py` 包含：

- uniform 与 dynamic-FPS 两种 frame sampler。
- 一个玩具版的 temporal-grounding evaluator：给定时刻 T 的"ground truth"事件和模型输出，按容差打分。
- 跨 Video-LLaMA（16 帧，Q-former）、Video-LLaVA（8 帧，MLP）、Qwen2.5-VL（dynamic FPS + TMRoPE）的对比。

## Ship It

本节课产出 `outputs/skill-video-vlm-frame-planner.md`。给定一个视频任务（监控、动作识别、temporal grounding、摘要），它挑选 frame sampler、池化倍数、输出格式和预期的准确率档位。

## Exercises

1. 对于一段 3 分钟的烹饪演示，选择 uniform 还是 dynamic FPS？用 token 数量给出理由。

2. TMRoPE 具体多做了什么，是简单的时序 embedding 表做不到的？

3. 为 temporal grounding 写一个 VLM 能学会输出的 JSON schema。要包含错误情况。

4. 阅读 Video-LLaVA 第 3 节关于"Alignment Before Projection"的内容。为什么这比分别训练图像 encoder 和视频 encoder 更好？

5. 根据 VideoMME 排行榜，截至 2026 年最强的开源模型与最强的闭源模型之间差距是多少？这个差距中有多少可归因于时序编码，多少归因于基础 LLM 规模？

## Key Terms

| 术语 | 常见说法 | 真实含义 |
|------|-----------------|------------------------|
| Temporal grounding | "时间定位的答案" | VLM 输出某个事件发生的具体时间戳区间 |
| TMRoPE | "时间-多模态 RoPE" | 带绝对时间戳的 3D 旋转位置编码，Qwen2.5-VL 使用 |
| Dynamic FPS | "运动感知采样" | 在高运动片段多采帧，在静止片段少采帧 |
| Frame pooling | "逐帧空间压缩" | 在送进 LLM 之前用双线性插值减少每帧的 patch 数 |
| Video Q-former | "clip 压缩器" | 把 N 帧映射为 K 个可学习 query 的 cross-attention 瓶颈 |
| VideoMME | "视频评测集" | 覆盖短/中/长视频的综合 benchmark，2500+ 样本 |

## Further Reading

- [Zhang et al. — Video-LLaMA (arXiv:2306.02858)](https://arxiv.org/abs/2306.02858)
- [Li et al. — VideoChat (arXiv:2305.06355)](https://arxiv.org/abs/2305.06355)
- [Lin et al. — Video-LLaVA (arXiv:2311.10122)](https://arxiv.org/abs/2311.10122)
- [Qwen Team — Qwen2.5-VL (arXiv:2502.13923)](https://arxiv.org/abs/2502.13923)
- [Lin et al. — VILA-1.5 (arXiv:2312.07533)](https://arxiv.org/abs/2312.07533)
