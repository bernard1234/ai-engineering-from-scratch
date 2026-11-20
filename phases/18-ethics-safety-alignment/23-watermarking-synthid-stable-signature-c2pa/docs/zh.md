# 水印 — SynthID、Stable Signature、C2PA

> 三项技术构成了 2026 年 AI 生成内容 provenance 的结构。SynthID（Google DeepMind）——图像水印于 2023 年 8 月推出，文本+视频于 2024 年 5 月推出（Gemini + Veo），文本于 2024 年 10 月通过 Responsible GenAI Toolkit 开源，2025 年 11 月随 Gemini 3 Pro 推出统一的多媒体检测器。文本水印以不可察觉的方式调整下一 token 采样概率；图像/视频水印能经受压缩、裁剪、滤镜、帧率变化。Stable Signature（Fernandez et al., ICCV 2023, arXiv:2303.15435）——微调 latent diffusion 解码器，使每个输出都包含一条固定消息；裁剪后（内容 10%）的生成图像在 FPR<1e-6 下检测率 >90%。后续论文“Stable Signature is Unstable”（arXiv:2405.07145, 2024 年 5 月）——微调能在保持质量的同时移除水印。C2PA——加密签名的、防篡改的元数据标准（C2PA 2.2 Explainer 2025）。水印与 C2PA 互补：元数据可被剥离但承载更丰富的 provenance；水印能经受转码但承载的信息更少。

**Type:** Build
**Languages:** Python (stdlib, token 水印嵌入 + 检测)
**Prerequisites:** 第 10 阶段，第 04 课（sampling），第 01 阶段，第 09 课（information theory）
**Time:** ~75 分钟

## Learning Objectives

- 描述 token 级水印（SynthID-text 风格）及其可检测的机制。
- 描述 Stable Signature 以及 2024 年攻破它的移除攻击。
- 陈述 C2PA 的作用，以及它为何与水印互补。
- 描述关键局限：模型特定的信号、改写下的鲁棒性，以及保义攻击（arXiv:2508.20228）。

## 问题场景

2023-2024 年间，deepfake 与 AI 生成内容大规模进入政治与消费场景。水印是提议中的技术 provenance 信号：在生成时打标，之后检测。2025 年的证据：没有哪种水印是无条件鲁棒的，但与 C2PA 元数据分层组合后，这一组合提供了可用的 provenance 叙事。

## 核心概念

### 文本水印（SynthID-text 风格）

Kirchenbauer et al. 2023 的机制，由 Google 产品化：

1. 在每个解码步骤，对前 K 个 token 做哈希，把词表伪随机地划分为“绿”集与“红”集。
2. 通过给绿色 logits 加上 δ 来使采样偏向绿色集。
3. 生成结果中的绿色 token 比随机情况下更多。

检测：对每个前缀重新哈希，统计生成中的绿色 token，计算 z 分数。水印文本的 z 分数 >0，人类文本约为 0。

性质：
- 对读者不可察觉（δ 足够小，质量损失轻微）。
- 在能访问词表划分函数的情况下可检测。
- 对改写不鲁棒——重写文本会破坏信号。

SynthID-text 于 2024 年 10 月通过 Google 的 Responsible GenAI Toolkit 开源。

### Stable Signature（图像）

Fernandez et al. ICCV 2023。微调 latent diffusion 解码器，使每张生成图像都包含一条嵌入在 latent 表征中的固定二进制消息。用神经解码器从 latent 中解码检测。裁剪到内容 10% 的图像在 FPR<1e-6 下检测率 >90%。

2024 年 5 月的“Stable Signature is Unstable”（arXiv:2405.07145）：对解码器做微调可在保持图像质量的同时移除水印。生成后的对抗性微调很便宜；水印的对抗鲁棒性有限。

### SynthID 统一检测器（2025 年 11 月）

与 Gemini 3 Pro 一同推出：一个多媒体检测器，在一个 API 中读取来自文本、图像、音频和视频的 SynthID 信号。统一了 Google 的 provenance 技术栈。

### C2PA

Coalition for Content Provenance and Authenticity。加密签名的、防篡改的元数据标准。C2PA 2.2 Explainer（2025）。C2PA manifest 记录 provenance 主张（谁创建、何时、经过哪些变换），由创建者的密钥签名。

与水印互补：
- 元数据可被剥离；水印不能（轻易）。
- 元数据丰富（完整 provenance 链）；水印只承载若干比特。
- C2PA 依赖平台采用；水印自动嵌入。

Google 在 Search、Ads 和“About this image”中同时集成了两者。

### 局限

- **依赖模型。** SynthID 为启用了 SynthID 的模型生成内容加水印。来自未启用 SynthID 的模型的生成内容没有水印，因此“没有 SynthID 信号”不能证明真实性。
- **改写。** 文本水印无法经受保义改写。
- **变换攻击。** arXiv:2508.20228（2025）展示了能同时破坏文本水印和许多图像水印的保义攻击。
- **微调移除。** 根据“Stable Signature is Unstable”，生成后的微调会移除嵌入的水印。

### EU AI Act 第 50 条

面向 AI 生成内容标注的透明度行为准则（首版草案 2025 年 12 月，第二版草案 2026 年 3 月，预计 2026 年 6 月定稿，见[欧盟委员会状态页](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content)）。截至 2026 年 4 月，该准则仍为草案，时间表可能变化。这是要求技术层的监管层。Deepfake 必须被标注。

### 本课在 Phase 18 中的位置

第 22 至 23 课关注模型输出什么（私有数据、provenance 信号）。第 27 课覆盖训练数据治理。第 24 课是要求这些技术措施的监管框架。

```figure
an-watermark-greenlist
```

## Use It

`code/main.py` 构建一个玩具级文本水印。token 是 0..N-1 的整数；带水印的采样偏向由哈希定义的绿色集。检测器计算绿色 token 的 z 分数。你可以观察 1000 token 生成下的检测、看改写如何破坏信号，并测量在人类文本上的假阳性率。

## Ship It

本课产出 `outputs/skill-provenance-audit.md`。给定一个带有 provenance 主张的内容部署，它审计：水印机制（若有）、C2PA 签名链（若有）、各自的对抗鲁棒性，以及各模态的覆盖情况。

## Exercises

1. 运行 `code/main.py`。报告带水印的 1000 token 生成与人类撰写文本的 z 分数。找出 95% 置信阈值下的假阳性率。

2. 实现一个改写攻击，用同义词替换 30% 的 token。重新测量 z 分数。

3. 阅读 Kirchenbauer et al. 2023 第 6 节关于鲁棒性的内容。为什么文本水印在改写下失效，而图像水印能经受裁剪？

4. 设计一个使用 SynthID-text + C2PA 元数据的部署。描述消费者看到的 provenance 链。指出每个组件的一种失败模式。

5. 2024 年的“Stable Signature is Unstable”结果表明微调会移除图像水印。设计一个限制这种攻击的部署控制——例如要求微调检查点以签名方式发布。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| SynthID | “Google 的水印” | 跨模态 provenance 信号；文本、图像、音频、视频 |
| Token watermark | “Kirchenbauer 式” | 偏置采样的文本水印，可通过绿色 token z 分数检测 |
| Stable Signature | “图像水印” | 微调解码器水印；ICCV 2023 |
| C2PA | “元数据标准” | 加密签名的防篡改 provenance 元数据 |
| Paraphrase robustness | “改写会不会破坏它” | 文本水印属性；目前有限 |
| Fine-tune removal | “对抗性去水印” | 通过解码器微调移除图像水印的攻击 |
| Cross-modal detector | “统一 SynthID” | 2025 年 11 月的跨模态统一 API |

## Further Reading

- [Kirchenbauer et al. — A Watermark for Large Language Models（ICML 2023，arXiv:2301.10226）](https://arxiv.org/abs/2301.10226) —— token 水印机制
- [Fernandez et al. — Stable Signature（ICCV 2023，arXiv:2303.15435）](https://arxiv.org/abs/2303.15435) —— 图像水印论文
- [“Stable Signature is Unstable”（arXiv:2405.07145）](https://arxiv.org/abs/2405.07145) —— 移除攻击
- [Google DeepMind — SynthID](https://deepmind.google/models/synthid/) —— 跨模态水印
- [C2PA 2.2 Explainer（2025）](https://c2pa.org/specifications/specifications/2.2/explainer/Explainer.html) —— 元数据标准
