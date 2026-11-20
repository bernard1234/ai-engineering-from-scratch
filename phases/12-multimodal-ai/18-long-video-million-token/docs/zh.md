# 百万 token 上下文下的长视频理解

> 一段 1 小时、24 FPS 的 4K 视频，经过 patch 和 embedding 之后，大约会产生 6000 万个 token。一期 2 小时的播客转写成文字是 30,000 个 token。一部完整的蓝光剧情长片，即便用激进的池化压缩，也有数十万 token。Google 的 Gemini 1.5（2024 年 3 月）以 1000 万 token 的上下文开启了这个时代，能在长达一小时的视频上做可靠的 needle-in-a-haystack 召回。LWM（Liu et al., 2024 年 2 月）展示了 ring attention 的扩展路径。LongVILA 和 Video-XL 进一步扩展了摄入能力。VideoAgent 用 agentic retrieval 取代了原始上下文。每种方案都是在算力、召回和工程复杂度上的不同取舍。本节课把它们并排解读。

**Type:** Build
**Languages:** Python（stdlib，needle-in-a-haystack 模拟器 + agentic-retrieval 路由器）
**Prerequisites:** Phase 12 · 17（video temporal tokens）
**Time:** ~180 分钟

## Learning Objectives

- 计算不同 FPS 与池化设置下长视频的视觉 token 总量。
- 解释三条扩展路径：暴力上下文（Gemini 1.5）、ring attention（LWM）、token 压缩（LongVILA / Video-XL）。
- 在准确率与延迟上比较原始上下文的 video VLM 与 agentic-retrieval 的 video VLM（VideoAgent）。
- 为一段 30 分钟的视频设计 needle-in-a-haystack 测试，并测量指定分钟处的召回率。

## 问题场景

Qwen2.5-VL 尺寸的 patch 在 384 原生分辨率下，单帧约 729 个 token。按 3x3 池化则是每帧 81 个 token。一段 30 分钟的片段按 1 FPS 是 1800 帧 = 145,800 个 token。2025 年的开源 VLM 装得下，但很紧张。按 2 FPS 就是 291,600 个 token——只有最大的上下文才放得下。

一段 2 小时的电影按 1 FPS 是 583k token。超出大多数 2026 年的开源模型；要么用 Gemini 2.5 Pro，要么做更激进的池化。

于是出现了三条扩展路径。

## 核心概念

### 路径 1：暴力上下文（Gemini 1.5、Claude Opus）

用硬件硬扛。把上下文扩展到数百万 token，在一次前向传播里处理所有内容。

Gemini 1.5 Pro 发布时是 1M token；Gemini 1.5 Ultra 到 10M；Gemini 2.5 Pro 在 2026 年能可靠处理数小时的视频。论文（arXiv:2403.05530）记录了在约 9.5M token 以内 needle-in-a-haystack 召回率达 99.7%。

工程实现：一套带内存层级（local + global + sparse）的定制 attention 实现，再加上为长上下文效率服务的 MoE 专家路由。细节没有完整公开。也不是开源的。

### 路径 2：Ring attention（LWM、LongVILA）

Ring attention 把长序列分布到多台设备上，形成一个"环"，每台设备持有一个分块。全序列上的 attention 通过以下方式完成：每台设备把自己的分块按环的形式发给下一台，计算部分 attention，再聚合结果。

LWM（Liu et al., 2024）用这种方式训练了一个 1M token 上下文的模型。训练算力随上下文长度线性增长，而非二次方——attention 的二次方开销被摊销到环上的各设备之间。

LongVILA（arXiv:2408.10188）把这一模式适配到 VLM 上。1400 帧视频、每帧 192 个 token = 268k 上下文，用 8 路并行上的 ring attention 训练。

### 路径 3：Token 压缩（Video-XL、LongVA）

比暴力上下文便宜：在 LLM 看到序列之前先做激进压缩。

Video-XL（arXiv:2409.14485）使用 visual summary token：每 N 帧组成的 clip 产生一个"summary"token，它对这 N 帧做 attention。推理时，LLM 每个 clip 只看到一个 summary token，上下文因此大幅缩小。

LongVA 用"long context transfer"技术把 LLM 上下文从 200k 扩展到 2M。先在长上下文文本上训练，再通过共享表示迁移到长上下文视频。

Token 压缩牺牲的是特定时间戳处的召回，换取可扩展性。模型大体知道发生了什么，但有时会错过确切的帧。

### 路径 4：Agentic retrieval（VideoAgent）

不要把整段视频喂给 LLM。相反，把视频当作数据库，用 LLM 去查询它。

VideoAgent（arXiv:2403.10517）：

1. LLM 读取问题。
2. LLM 向检索工具请求相关片段（"给我看有猫的片段"）。
3. 工具返回匹配的 clip 时间戳。
4. LLM 通过 VLM 读取这些片段。
5. LLM 组织答案，或提出后续查询。

这就是把 LLM-as-agent 模式应用到长视频上。推理更便宜（只编码相关片段），工程更难（检索质量成了瓶颈）。

### Needle-in-a-haystack 评测

标准的长上下文测试：在视频的随机位置插入一个独特的视觉或文本标记，然后提出一个需要回忆该标记的查询。

指标：Recall@k，跨视频长度和标记位置测量。

Gemini 2.5 Pro 在长达 90 分钟的视频上召回率 >99%。开源 72B 模型（Qwen2.5-VL-72B、InternVL3-78B）在 30 分钟时约 85-90%，超过 60 分钟后开始下降。

VideoAgent 在 2 小时以上可以追平甚至超过原始上下文模型，因为只要工具足够好，检索就能命中那根"针"。

### 该选哪条路径

对于 15 分钟的片段、要求前沿准确率：开源 72B + 原生上下文通常就够了。选 Qwen2.5-VL-72B。

对于 30 分钟到 1 小时的内容：开源用 LongVILA 或 Video-XL；闭源用 Gemini 2.5 Pro。质量门槛很关键——要前沿就选闭源。

对于 2 小时以上的内容：VideoAgent 或类似的检索模式。另一种做法是先摘要成更小的块，再喂入分层摘要。

### 2026 年的生产模式

在实践中，生产环境的长视频流水线是混合式的：

1. 对整段视频跑 dynamic-FPS 采样 + 激进池化（得到一个 100k token 的全局表示）。
2. 交给 72B VLM 生成全局摘要。
3. 如果用户提出细节问题，就以摘要作为索引跑 agentic retrieval。

这把用于全局理解的暴力上下文与用于局部细节的检索结合了起来。

```figure
mm-video-token-budget
```

## Use It

`code/main.py`：

- 计算从 1 分钟到 3 小时、不同 FPS + 池化下视频的 token 预算。
- 模拟一次 needle-in-a-haystack 运行：在随机时间戳注入标记，提一个问题，给召回打分。
- 包含一个 agentic-retrieval 路由器模拟器，挑选特定 clip 喂给下游 VLM。

跑一下预算表，感受规模上的差距。

## Ship It

本节课产出 `outputs/skill-long-video-strategy-planner.md`。给定视频时长和查询复杂度，它在暴力上下文、压缩与 agentic retrieval 之间做选择，并计算延迟与质量预期。

## Exercises

1. 一段 45 分钟的讲座，1 FPS，每帧 81 个 token。总 token 是多少？能装进哪些模型的上下文？

2. 设计一个 needle-in-a-haystack 测试：在第几分钟注入标记，确切的查询格式是什么？

3. 在 1 小时视频上比较暴力上下文的 Qwen2.5-VL-72B（80k 上下文）与 VideoAgent（Claude 3.5 + 检索）。召回上谁赢？延迟上谁赢？

4. Ring attention 的内存开销随序列长度线性增长、随设备数量线性增长。解释原因，以及如果去掉 ring-rotation 阶段会出什么问题。

5. 阅读 Gemini 1.5 第 5 节关于 needle-in-a-haystack 的内容。论文在 1M 与 10M token 边界处关于召回发现了什么？

## Key Terms

| 术语 | 常见说法 | 真实含义 |
|------|-----------------|------------------------|
| Brute context | "就是更多 token" | 把 LLM 上下文扩展到数百万 token，一次处理全部内容 |
| Ring attention | "LWM 式并行" | 每台设备持有一个分块并轮转的分布式 attention 模式 |
| Token compression | "摘要 token" | 在 LLM 之前用学习到的压缩器减少每个 clip 的 token |
| Needle-in-haystack | "NIH 测试" | 在随机位置插入一个独特标记，测试时让模型回忆它 |
| Agentic retrieval | "LLM 当查询规划器" | LLM 向检索工具请求相关片段，通过 VLM 阅读它们，再组织答案 |
| VideoAgent | "视频的检索模式" | 经典的 agentic-retrieval 设计：问题 -> 工具 -> clip -> 答案 |

## Further Reading

- [Gemini Team — Gemini 1.5 (arXiv:2403.05530)](https://arxiv.org/abs/2403.05530)
- [Liu et al. — LWM / RingAttention (arXiv:2402.08268)](https://arxiv.org/abs/2402.08268)
- [Xue et al. — LongVILA (arXiv:2408.10188)](https://arxiv.org/abs/2408.10188)
- [Shu et al. — Video-XL (arXiv:2409.14485)](https://arxiv.org/abs/2409.14485)
- [Wang et al. — VideoAgent (arXiv:2403.10517)](https://arxiv.org/abs/2403.10517)
