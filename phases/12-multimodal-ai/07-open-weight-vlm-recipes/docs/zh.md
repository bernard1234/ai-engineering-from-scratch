# 开放权重 VLM 配方：真正重要的是什么

> 2024-2026 年的开放权重 VLM 文献是一片由消融表格构成的森林。Apple 的 MM1 测试了图像编码器、连接器和数据配比的 13 种组合。Allen AI 的 Molmo 证明了详细的人类描述优于 GPT-4V 蒸馏。Cambrian-1 做了 20 多组编码器对比。Idefics2 把五轴设计空间形式化了。Prismatic VLMs 在一个受控基准上比较了 27 种训练配方。在所有这些噪声之中，有一小批结论在各篇论文间保持一致：图像编码器比连接器架构更重要，数据配比比这两者都更重要，而详细的人类描述优于蒸馏得到的合成数据。本节课替你读懂这些表格。

**Type:** 学习 + 实验
**Languages:** Python（标准库，消融表格解析器 + 配方选择器）
**Prerequisites:** Phase 12 · 05（LLaVA 基线）
**Time:** ~180 分钟

## Learning Objectives

- 说出 VLM 五轴设计空间：图像编码器、连接器、LLM、数据配比、分辨率调度。
- 读懂一张 MM1 / Idefics2 / Cambrian-1 消融表，并预测哪个旋钮会推动给定 benchmark。
- 在给定算力预算和任务组合的情况下，为新 VLM 挑选一套配方（编码器、连接器、数据、分辨率）。
- 解释为什么在同等 token 数下，详细的人类描述优于 GPT-4V 蒸馏。

## 问题场景

开放权重的 VLM 已有数百个。从「好」到「state-of-the-art」之间的大部分差距不在架构，而在数据、分辨率调度和编码器选择。当你的模型表现不佳时，知道先拧哪个旋钮，能让你避免一个 500 万 GPU 小时的错误。

2023 年的那一波（LLaVA-1.5、InstructBLIP、MiniGPT-4）靠描述对预训练 + LLaVA-Instruct-150k 运行。基线不错，但上限大约在 MMMU 35%。

2024 年的那一波（MM1、Idefics2、Molmo、Cambrian-1、Prismatic VLMs）做了穷举式消融。结果既出人意料，又非常实用。

## 核心概念

### 五轴设计空间

Idefics2（Laurençon 等，2024）为这些轴命了名：

1. 图像编码器。CLIP ViT-L/14、SigLIP SO400m/14、DINOv2 ViT-g/14、InternViT-6B。编码器在 patch 大小、分辨率和预训练目标上各不相同。
2. 连接器。MLP（2-4 层）、Q-Former（32 个 query + cross-attn）、Perceiver Resampler（64 个 query）、C-Abstractor（卷积 + 双线性池化）。
3. 语言模型。Llama-3 8B / 70B、Mistral 7B、Phi-3、Gemma-2、Qwen2.5。LLM 的规模是参数成本的主导项。
4. 训练数据。描述对（CC3M、LAION）、交错图文（OBELICS、MMC4）、指令数据（LLaVA-Instruct、ShareGPT4V、PixMo、Cauldron）。
5. 分辨率调度。固定 224/336/448、AnyRes、原生动态。训练中逐步提升或保持恒定。

每一个量产 VLM 都要在每个轴上做出选择。MMMU 分数的大部分方差由第 1、4、5 轴解释——而不是你选了哪种连接器。

### 第 1 轴：编码器 > 连接器

MM1 第 3.2 节表明：从 CLIP ViT-L/14 换成 SigLIP SO400m/14，MMMU 提升了 3 分以上。把连接器从 MLP 换成 Perceiver Resampler，提升不到 1 分。Idefics2 复现了这一结果：SigLIP > CLIP，在同等 token 数下 Q-Former ≈ MLP ≈ Perceiver。

Cambrian-1 的「Cambrian Vision Encoders Match-Up」（Tong 等，2024）在一个以视觉为中心的 benchmark（CV-Bench）上跑了 20 多个编码器。榜首是 DINOv2 与 SigLIP 的混合；CLIP 处于中游；ImageBind 和 ViT-MAE 更靠下。从 CLIP ViT-L 到 DINOv2 ViT-g/14 的差距在 CV-Bench 上约为 5-7 分。

2026 年开放 VLM 的默认编码器是 SigLIP 2 SO400m/14，用于语义 + 稠密特征，有时与 DINOv2 ViT-g/14 的特征拼接（Cambrian 的「Spatial Vision Aggregator」就是这么做的）。

### 第 2 轴：连接器设计几乎无关紧要

MM1、Idefics2、Prismatic 和 MM-Interleaved 都得出同一结论：在固定的视觉 token 数下，连接器架构几乎不起作用。在同等 token 预算下，对 mean-pooled patch 加一个 2 层 MLP，与 32-query Q-Former 的表现相差不到 1 分。

真正重要的是 token 数。更多视觉 token = 更多 LLM 计算 = 性能提升，直到某一点后收益递减。每张图 64 个 token 对 OCR 而言太少。576-1024 个 token 是大多数开放 VLM 的最佳区间。2048+ 只对文档和图表有帮助。

Q-Former 与 MLP 之争是一个成本问题，不是质量问题：无论图像分辨率如何，Q-Former 都把 token 上限压在 32-64；MLP 则输出全部 patch token。对高分辨率输入，Q-Former 节省 LLM 上下文；对低分辨率输入，差别只是噪声。

### 第 3 轴：LLM 规模决定天花板

在每一篇 VLM 论文中，把 LLM 从 7B 翻倍到 13B，都能稳定在 MMMU 上加 2-4 分。到 70B 时，大多数 benchmark 已经饱和。VLM 的多模态推理天花板就是 LLM 的文本推理天花板——视觉编码器只能给它喂料，不能替它推理。

这就是为什么 Qwen2.5-VL-72B 和 Claude Opus 4.7 能在 MMMU-Pro 和 ScreenSpot-Pro 上碾压：语言大脑足够大。一个 7B 的 VLM 无法靠巧妙的连接器设计替代 70B 的 VLM。

### 第 4 轴：数据——详细的人类描述优于蒸馏

Molmo + PixMo（Deitke 等，2024）是 2024 年人人都该读的成果。Allen AI 让人类标注者用 1-3 分钟的高密度语音转文字来描述图像，得到 712K 张密集描述的图像。训练数据中没有任何地方用到 GPT-4V 蒸馏。

Molmo-72B 在 11 项 benchmark 中的 11 项上击败 Llama-3.2-90B-Vision。差距不在架构——而在描述质量。详细的人类描述每张图所包含的信息量是简短网络描述文本的 5-10 倍，并且在 GPT-4V 蒸馏会产生幻觉的地方保持事实扎实。

ShareGPT4V（Chen 等，2023）和 Cauldron（Idefics2）沿用同样的套路，混合了人类描述与 GPT-4V 描述。趋势很明确：对 2026 年的前沿而言，描述密度 > 描述数量 > 蒸馏的便利性。

### 第 5 轴：分辨率及其调度

Idefics2 的消融：384 -> 448 加 1-2 分。配合图像切分的 448 -> 980（AnyRes）在 OCR benchmark 上再加 3-5 分。平直的分辨率训练会停在中等准确率；分辨率爬坡（从 224 开始，结束于 448 或原生）训练更快，最终也更高。

Cambrian-1 做了分辨率与 token 的取舍实验：在固定算力下，你可以选择较低分辨率下的更多 token，或较高分辨率下的更少 token。高分辨率在 OCR 上胜出；低分辨率多 token 在通用场景理解上胜出。

2026 年的量产配方：Stage 1 用 384 固定分辨率训练，Stage 2 用最高 1280 的动态分辨率，面向 OCR 密集的任务。

### Prismatic 的受控对比

Prismatic VLMs（Karamcheti 等，2024）是把所有轴都控制住的论文。同一个 13B LLM、同一份指令数据、同一套评测——每次只变动一个轴。结果：

- 每图视觉 token 数解释了约 60% 的方差。
- 编码器选择解释了约 20%。
- 连接器架构解释了约 5%。
- 其余一切（数据配比、scheduler、LR）占剩下的约 15%。

这是个粗略的分解，但它是文献中对「我应该先消融什么」最干净的回答。

### 一个 2026 年的选择器

基于这些证据，2026 年新项目的默认开放 VLM 配方是：

- 编码器：原生分辨率 + NaFlex 的 SigLIP 2 SO400m/14；如果需要分割/grounding，再拼接 DINOv2 ViT-g/14 的稠密特征。
- 连接器：patch token 上的 2 层 MLP。除非受 token 限制，否则跳过 Q-Former。
- LLM：Qwen2.5 / Llama-3.1 / Gemma 2，7B 求成本，70B 求质量，按目标延迟来选。
- 数据：PixMo + ShareGPT4V + Cauldron，再用任务特定的指令数据补足。
- 分辨率：动态（长边最小 256，最大 1280 像素）。
- 调度：Stage 1 对齐（仅投影器），Stage 2 全量微调，Stage 3 任务特定微调。

上述每一项默认值都能追溯到本节课末尾所引论文中的某次实测消融。

```figure
l5-vlm-recipe-knobs
```

## Use It

`code/main.py` 是一个消融表格解析器兼配方选择器。它把 MM1 和 Idefics2 的消融表（经过压缩）编码进去，让你可以查询：

- 「给定预算 X 和任务 Y，哪套配方胜出？」
- 「如果我在 7B Llama 上把 SigLIP 换成 CLIP，MMMU 的预期变化是多少？」
- 「为了得到 80% 置信度的答案，我应该先消融哪个轴？」

输出是一份排序后的配方列表，附带各 benchmark 的预期变化，以及一条「先消融什么」的建议。

## Ship It

本节课产出 `outputs/skill-vlm-recipe-picker.md`。给定目标任务组合、算力预算和延迟目标，它会输出一份完整配方（编码器、连接器、LLM、数据配比、分辨率调度），并为每个选择附上支撑它的消融实验引用。它能避免工程师在每启动一个新 VLM 项目时都重新造一遍 Idefics2 的消融表。

## Exercises

1. 阅读 MM1 第 3.2 节。在固定的 2B LLM、5000 万张图像预算下，哪个编码器胜出？换到 13B LLM 时答案会反转吗？为什么？

2. Cambrian-1 发现，拼接 DINOv2 + SigLIP 在以视觉为中心的 benchmark 上优于任一单独模型，但在 MMMU 上没有额外信号。预测哪些 benchmark 会获益，哪些保持不变。

3. 你的目标是运行在 2B LLM 上的移动端 UI agent。请选择编码器、连接器、分辨率和数据配比。用一张具体的消融表为每个选择辩护。

4. Molmo 提供了 4B 和 72B 模型。4B 与闭源 7B VLM 有竞争力；72B 在 11/11 项 benchmark 上击败 Llama-3.2-90B-Vision。这对 LLM 规模平台期假说说明了什么？

5. 设计一张消融表，在 7B VLM 上把数据配比质量与编码器质量分离开来。最少需要多少次训练？给出四个轴的设置。

## Key Terms

| Term | What people say | What it actually means |
|------|-----------------|------------------------|
| Ablation | 「拧动一个旋钮」 | 训练多轮，彼此之间恰好在一个设计空间轴上不同，其余保持恒定 |
| Connector | 「桥梁」/「投影器」 | 把视觉编码器输出映射到 LLM token 空间的可训练模块（MLP、Q-Former、Perceiver） |
| Detailed human caption | 「密集描述」 | 由人撰写的多句描述（通常 80-300 个 token），比网络 alt 文本信息更丰富 |
| Distillation | 「GPT-4V 描述」 | 由更强的专有 VLM 生成的训练数据；方便，但容易继承其幻觉 |
| AnyRes / dynamic res | 「高分辨率路径」 | 通过切块或 M-RoPE 输入大于编码器原生分辨率图像的策略 |
| Resolution ramp | 「课程表」 | 从低分辨率开始逐步提升的训练调度，可加速对齐学习 |
| Vision-centric bench | 「CV-Bench / BLINK」 | 侧重细粒度视觉感知、而非语言密集推理的评测 |
| PixMo | 「Molmo 的数据」 | Allen AI 的 712K 密集描述图像数据集；由人类语音转写为密集描述 |

## Further Reading

- [McKinzie et al. — MM1 (arXiv:2403.09611)](https://arxiv.org/abs/2403.09611)
- [Laurençon et al. — Idefics2 / What matters building VLMs (arXiv:2405.02246)](https://arxiv.org/abs/2405.02246)
- [Deitke et al. — Molmo and PixMo (arXiv:2409.17146)](https://arxiv.org/abs/2409.17146)
- [Tong et al. — Cambrian-1 (arXiv:2406.16860)](https://arxiv.org/abs/2406.16860)
- [Karamcheti et al. — Prismatic VLMs (arXiv:2402.07865)](https://arxiv.org/abs/2402.07865)
