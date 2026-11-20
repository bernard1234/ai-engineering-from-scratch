# LLaVA 与视觉指令微调

> LLaVA（2023 年 4 月）是这个星球上被复制最多的多模态架构。它用 2 层 MLP 替换了 BLIP-2 的 Q-Former，用朴素的 token 拼接替换了 Flamingo 的门控交叉注意力，并用 GPT-4 从纯文本 caption 生成的 158k 条视觉指令轮次进行训练。任何在 2023 到 2026 年间构建过 VLM 的从业者，做的都是某种 LLaVA 变体。LLaVA-1.5 加入了 AnyRes。LLaVA-NeXT 提升了分辨率。LLaVA-OneVision 把图像、多图和视频统一进同一套配方。本课解读这套配方、实现 projector，并解释为什么"更简单"的方案赢了。

**Type:** Build
**Languages:** Python（stdlib，projector + 指令模板构建器）
**Prerequisites:** Phase 12 · 02（CLIP），Phase 11（LLM 工程——指令微调）
**Time:** ~180 分钟

## Learning Objectives

- 构建一个 2 层 MLP projector，把 ViT 的 patch embedding（维度 1024）映射到 LLM 的 embedding 维度（维度 4096）。
- 走一遍 LLaVA 的两阶段配方：(1) 在 558k caption 对上做 projector 对齐，(2) 在 158k 条 GPT-4 生成的指令轮次上做视觉指令微调。
- 构造 LLaVA 格式的 prompt，包含 image token 占位符、system prompt 以及 user/assistant 轮次。
- 解释尽管 Q-Former 在 token 预算上占优，社区为何仍从 Q-Former 转向 MLP。

## 问题场景

BLIP-2 的 Q-Former（第 12.03 课）把一张图像压缩成 32 个 token。干净、高效、在 benchmark 上表现良好。但它有两个问题。

第一，Q-Former 可训练，但它的 loss 并不是最终任务。Stage 1 训练 ITC+ITM+ITG，Stage 2 训练 LM loss。query 学到的是一种中间表示，之后还得由 LLM 去解码。信息在瓶颈处丢失了。

第二，Q-Former 有 188M 参数，而在 LLaVA 所处的 2023 年规模下，你必须把它和目标 LLM 一起协同设计。换 LLM，就重训 Q-Former；换视觉编码器，也要重训。每一种组合都是一个独立的研发项目。

LLaVA 给出的答案简单到令人尴尬：取出 ViT 的 576 个 patch token，让每个都通过一个 2 层 MLP（`1024 → 4096 → 4096`），然后把全部 576 个 token 塞进 LLM 的输入序列。没有瓶颈。没有在奇怪目标上做 stage 1 预训练。只用直接的 LM loss 训练这个 MLP。

数据从哪来？LLaVA 的第二个洞见是：用 GPT-4（纯文本）来生成指令数据。把某张图像的 COCO caption 和 bounding-box 数据喂给 GPT-4，让它产出对话、描述和复杂推理问题。158k 条指令-回复轮次，免费获得。无需人工标注。

结果是：一个在 8 块 A100 上跑一天就训练出来的 VLM，在 MMMU 上击败 Flamingo，并发布了社区可以继续扩展的开源 checkpoint。到 2023 年底，它已经衍生出 50 多个 fork。

## 核心概念

### 架构

13B 的 LLaVA-1.5：
- 视觉编码器：CLIP ViT-L/14 @ 336（stage 1 冻结，stage 2 可选解冻）。
- Projector：带 GELU 激活的 2 层 MLP，`1024 → 4096 → 4096`。
- LLM：Vicuna-13B（后来是 Llama-3.1-8B）。

在一张图像 + 文本 prompt 上的前向过程：

```
img -> ViT -> 576 patches of dim 1024
patches -> MLP -> 576 tokens of dim 4096
prompt: system + "<image>" placeholder + user question
replace <image> token with the 576 projected tokens
feed the full sequence to the LLM
decode response
```

图像占用 LLM 上下文中的 576 个 token。在 2048 上下文下，留给文本的是 1472 个 token。到了 32k 上下文，它就只是个舍入误差。

### 第 1 阶段：projector 对齐

冻结 ViT，冻结 LLM，只训练那 2 层 MLP。数据集：558k 图文对（LAION-CC-SBU）。loss：以投影后的 image token 为条件，在 caption 上做语言建模。

在 batch 128 下跑一个 epoch，几个小时就能完成。projector 学会把 ViT 空间映射到 LLM 空间。没有任何任务特定的监督。

### 第 2 阶段：视觉指令微调

解冻 projector（保持可训练）。解冻 LLM（通常全量解冻，有时用 LoRA）。在 158k 条视觉指令轮次上训练。

指令数据才是关键。Liu 等人是这样生成的：
1. 取一张 COCO 图像。
2. 提取其文本描述（5 条人工 caption + bounding-box 列表）。
3. 连同三个 prompt 模板发给 GPT-4：
   - 对话（Conversation）："围绕这张图像，生成一段 user 与 assistant 之间的来回对话。"
   - 详细描述（Detailed description）："给出对这张图像丰富、细致的描述。"
   - 复杂推理（Complex reasoning）："提出一个需要针对图像进行推理的问题，然后回答它。"
4. 把 GPT-4 的输出解析成 (instruction, response) 对。

这些过程都不直接接触图像——只接触文本描述。GPT-4 会虚构出看似合理的图像内容。有些噪声，但确实有效：158k 条轮次足以解锁对话能力。

### 为什么社区纷纷效仿

- 没有 stage 1 专属的 loss 需要调。全程都是 LM loss。
- projector 的训练以小时计，而不是以天计。
- 换 LLM（LLaVA-Llama2、LLaVA-Mistral、LLaVA-Llama3）只需重训 projector。
- 视觉指令数据流水线依赖 GPT-4，为新领域重新生成的成本很低。

### LLaVA-1.5 与 LLaVA-NeXT

LLaVA-1.5（2023 年 10 月）新增了：
- 把学术任务数据（VQA、OKVQA、RefCOCO）混入指令微调。
- 更好的 system prompt。
- 上下文从 2048 扩展到 32k。

LLaVA-NeXT（2024 年 1 月）新增了：
- AnyRes：把高分辨率图像切成 2x2 或 1x3 的 336x336 裁剪网格，再加一张全局低分辨率缩略图。每个裁剪变成 576 个 token；每张图像总计约 2880 个视觉 token。OCR 和图表任务的表现大幅跃升。
- 更好的指令数据配比，混入 ShareGPT4V（高质量的 GPT-4V caption）。
- 更强的基座 LLM（Mistral-7B、Yi-34B）。

### LLaVA-OneVision

第 12.08 课会深入讲解 OneVision。简版：projector 相同，但用一套课程学习训练，在同一个模型里覆盖单图、多图和视频，并共享视觉 token 预算。

### 与 Q-Former 的对比

| | Q-Former (BLIP-2) | MLP (LLaVA) |
|---|---|---|
| 每图视觉 token 数 | 32 | 576（基础）或 2880（AnyRes） |
| 可训练参数量 | 188M + LM | 40M + LM |
| Stage 1 的 loss | ITC+ITM+ITG | 仅 LM |
| LLM 可替换性 | 需要重训 | 只需极少重训即可替换 |
| 多图 | 别扭 | 自然（拼接） |
| 视频 | 别扭 | 自然（逐帧拼接） |
| token 预算 | 小 | 大 |

MLP 在简洁性和 token 灵活性上胜出，Q-Former 在 token 预算上胜出。到 2023 年底，token 预算已不再是制约因素（LLM 上下文增长到 32k–128k+），简洁性占了上风。

### prompt 格式

```
A chat between a curious human and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the human's questions. USER: <image> Describe this image in detail. ASSISTANT: The image shows ...
```

`<image>` 是一个占位 token。在 tokenization 之前，它会被替换成 576 个视觉 token（使用 AnyRes 时是 2880 个）。tokenizer 看到的序列比它训练时略长，但 LLM 能处理这种新颖输入，因为 stage 1 已经教会了它。

### 参数开销

LLaVA-1.5-7B 的拆解：
- CLIP ViT-L/14 @ 336：303M（stage 1 冻结，stage 2 通常解冻）。
- Projector（2 层 linear）：约 22M 可训练参数。
- Llama-7B：7B。
- 合计：7.3B 参数。stage 2 期间可训练的是完整的 7B + 22M projector。

stage 2 的训练成本：8xA100 上约 20 小时。这是关键数字——一天、一个节点、可复现。这正是 LLaVA 扩散开来的原因。

```figure
mm-llava-projector
```

## Use It

`code/main.py` 实现了：

1. 纯 Python 的 2 层 MLP projector（玩具规模，dim 16 → 32 → 32）。
2. prompt 构建流水线：system prompt + 用 N 个投影 token 替换 `<image>` + user 轮次 + assistant 生成占位。
3. 一个可视化工具，展示 576 个 token 的视觉块在 LLM 上下文中占多大比例（占 2k / 32k / 128k 上下文的百分比）。

## Ship It

本课产出 `outputs/skill-llava-vibes-eval.md`。给定一个 LLaVA 家族的 checkpoint，它运行一套 10 条 prompt 的 vibes-eval 套件（3 条 captioning、3 条 VQA、2 条推理、2 条拒答），并给出人类可读的评分卡。这不是 benchmark，而是用于确认 projector 与 LLM 连接良好的冒烟测试。

## Exercises

1. 计算 `1024 → 4096 → 4096` 的 2 层 MLP projector 的可训练参数量。加上 GELU 和 bias 后，它占 LLaVA-13B 的比例是多少？

2. 为"拒答"场景构造一个 LLaVA prompt——图像中包含一个私人个体。写出预期的 assistant 回复。为什么 LLaVA 应该零样本拒答？需要什么样的训练数据来强化这种拒答？

3. 阅读 LLaVA-NeXT 博客的 AnyRes 章节。计算一张 1344x672 图像在 AnyRes 下的视觉 token 数，并与 336x336 下的基础 576 个 token 作比较。

4. LLaVA 的 stage 1 projector 是在 caption 上用 LM loss 训练的。如果跳过 stage 1 直接进入 stage 2（视觉指令微调）会怎样？请引用 Prismatic VLMs 的消融实验（arXiv:2402.07865）来回答。

5. LLaVA-Instruct-150k 用 GPT-4 结合 COCO caption 来生成指令。对于一个新领域（医学 X 光片、卫星影像），描述生成领域指令的四步数据流水线。每一步可能出什么问题？

## Key Terms

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Projector | "MLP 桥" | 带 GELU 的 2 层 MLP，把 ViT 维度映射到 LLM 维度 |
| Image token | "<image> 占位符" | 推理前会被 N 个投影后的视觉 token 替换的 prompt 标记 |
| Visual instruction tuning | "LLaVA stage 2" | 在 GPT-4 生成的 (image, instruction, response) 三元组上训练 |
| Stage 1 alignment | "projector 预训练" | 冻结 ViT 和 LLM，用 caption 上的 LM loss 训练 projector |
| AnyRes | "多裁剪切块" | 把高分辨率图像切成网格块，并把每块的视觉 token 拼接起来 |
| LLaVA-Instruct | "GPT-4 生成" | 由 COCO caption + GPT-4 合成的 158k 条指令-回复对 |
| Vision encoder freeze | "骨干网锁定" | CLIP 权重在 stage 1 不更新，stage 2 有时也不更新 |
| ShareGPT4V | "更好的 caption" | 由 GPT-4V 生成的 1M 条密集 caption，用于更高质量的对齐 |
| VQA | "视觉问答" | 回答关于一张图像的自由形式问题的任务 |
| Prismatic VLMs | "设计空间论文" | Karamcheti 2024 的消融实验，系统检验 projector 与数据的选择 |

## Further Reading

- [Liu 等 — Visual Instruction Tuning（arXiv:2304.08485）](https://arxiv.org/abs/2304.08485) —— LLaVA 论文。
- [Liu 等 — Improved Baselines with Visual Instruction Tuning（arXiv:2310.03744）](https://arxiv.org/abs/2310.03744) —— LLaVA-1.5。
- [Chen 等 — ShareGPT4V（arXiv:2311.12793）](https://arxiv.org/abs/2311.12793) —— 密集 caption 数据集。
- [Karamcheti 等 — Prismatic VLMs（arXiv:2402.07865）](https://arxiv.org/abs/2402.07865) —— 设计空间的消融实验。
- [Li 等 — LLaVA-OneVision（arXiv:2408.03326）](https://arxiv.org/abs/2408.03326) —— 统一的单图、多图、视频。
