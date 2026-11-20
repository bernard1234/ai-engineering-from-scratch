# InternVL3：原生多模态预训练

> InternVL3 之前的每个开源 VLM 都遵循同一套三步配方：拿一个在数万亿文本 token 上训练好的文本 LLM，外挂一个视觉编码器，再微调接缝处。这样可行，但会留下对齐债务（alignment debt）——文本 LLM 已经把全部预训练预算花在纯文本上，并不能原生理解视觉 token。事后加入视觉能力时，LLM 必须重新学习如何把视觉输入与自己的文本推理联系起来，同时又不能忘掉文本。InternVL3（Zhu 等，2025 年 4 月）否定了这种事后方案：一次预训练，从第一步起文本与多模态就交错进行。结果是：在 78B 参数下开放模型在 MMMU-Pro 上可与 Gemini 2.5 Pro 匹敌。本课解读原生预训练的论据，以及做出这一选择后会带来哪些变化。

**Type:** Learn
**Languages:** Python（stdlib，训练语料混合器）
**Prerequisites:** Phase 12 · 05，Phase 12 · 07（recipes）
**Time:** ~120 分钟

## Learning Objectives

- 解释事后 VLM 训练为何会积累对齐债务，并列举三种可测量的症状（灾难性遗忘、答案漂移、视觉-文本不一致）。
- 描述 InternVL3 的原生预训练语料配比，以及 text : interleaved : caption 比例为何重要。
- 把 V2PE（可变视觉位置编码）与 Qwen2-VL 的 M-RoPE 做比较。
- 说出视觉分辨率路由器（ViR）与解耦视觉-语言部署（DvD）两项部署优化。

## 问题场景

事后 VLM 训练是默认做法。LLaVA、BLIP-2、Qwen-VL、Idefics——全都拿一个已经预训练好的 LLM（Llama、Vicuna、Qwen、Mistral）再加装视觉。训练阶段通常长这样：

1. 冻结 LLM + 冻结视觉编码器 + 可训练 projector，在 caption 对上训练以对齐 embedding。
2. 解冻 LLM，在指令数据（LLaVA-Instruct、ShareGPT4V）上训练。
3. 可选的任务特定微调。

对齐债务会以三种症状显现：

- 灾难性遗忘。事后 VLM 会忘掉纯文本能力。GSM8K 分数下降 5-10 分。Hellaswag 分数下降。纯文本 agent 出现退化。
- 答案漂移。同一个视觉问题的细微措辞变化会得到不同答案。视觉编码器与 LLM 的连接绑定弱于 LLM 自身的 token 之间。
- 视觉-文本不一致。VLM 能正确描述一张图像，随后却给出与自己描述相矛盾的答案。视觉 token 不像文本那样参与 LLM 的内部一致性检查。

这些症状有充分记录。MM1.5 第 4 节对它们做了量化。LLaVA-OneVision 的消融实验暗示了它们。原生预训练就是答案。

## 核心概念

### 原生多模态预训练

InternVL3 从零开始在从第一步起就是原生多模态的语料上训练。配比是：

- 40% 纯文本数据（FineWeb、Proof-Pile-2 等）
- 35% 图文交错数据（OBELICS、MMC4 风格）
- 20% 成对图文 caption 数据
- 5% 视频-文本数据

视觉 token、文本 token 以及跨模态交互从第一个梯度步起就参与同一个 loss。没有对齐预训练，没有 projector 冻结阶段，也没有需要事后恢复的灾难性遗忘。

对基座模型来说训练只有一个阶段。指令微调随后进行，但基座模型已经把视觉 token 当成一等公民来理解。

### V2PE（可变视觉位置编码）

Qwen2-VL 使用固定轴分配的 M-RoPE。InternVL3 引入 V2PE：位置编码按模态类型（文本、图像、视频）变化，并带有可学习的缩放。实践中：

- 文本 token 使用 1D 位置（文本索引）。
- 图像 patch 使用 2D 位置（行、列）。
- 视频帧使用 3D 位置（时间、行、列）。

三者共享同一 RoPE 频率基，但每个频带的隐藏维分配是可学习参数，而不是固定切分。这为预训练期间在时间与空间频率分辨率之间做取舍提供了自由。

V2PE 的消融结论：同等算力下在视频 benchmark 上比 M-RoPE 高 1-2 分。算不上革命，但更干净。

### 视觉分辨率路由器（ViR）

部署优化。并非所有图像都需要全分辨率编码。一张只有一个物体的低细节照片以 1280px 原生分辨率编码就是在浪费 token。ViR 是一个小分类器，在编码之前预测回答该问题所需的最低分辨率。

路由分三档：低分辨率（256 token）、中（576）、高（2048+）。在生产流量中约 60% 的查询，低或中档就足够。净效果：同等质量下 2-3 倍吞吐。

### 解耦视觉-语言部署（DvD）

服务一个大型 VLM 时，视觉编码器每张图像只运行一次，但 LLM 要为每个输出 token 自回归运行。两个组件的瓶颈不同（视觉 = 卷积 + 注意力所需的 GPU 显存带宽；LLM = KV cache）。DvD 把它们拆到不同的 GPU 上，中间以流式方式交接。

对于一个 8B + 400M 编码器的模型，DvD 相比同机部署大约能把单节点吞吐翻倍。

### 单阶段与多阶段的质量对比

InternVL3 的主要 benchmark 主张：78B 参数下，在 MMMU-Pro 上与 Gemini 2.5 Pro 持平。38B 下，与 GPT-4o 持平。8B 下，领跑开源 8B 榜单。全部基于单阶段预训练 + 指令微调的配方。

对齐债务假说是可测量的：InternVL3-8B 每获得一单位视觉 benchmark 提升，所损失的文本 benchmark 分数（MMLU、GSM8K）都少于 Qwen2.5-VL-7B。这个模型更像通才，因为训练是一个整体而非两个拼件。

### InternVL3.5 与 InternVL-U

InternVL3.5（2025 年 8 月）把配方规模化。同样的原生预训练路线，更多数据、更多参数。MMMU 的提升是增量的。

InternVL-U（2026）加入统一生成——在相同主干之上通过 MMDiT 头输出图像。"U"代表"Understanding + generation"（理解 + 生成），追赶 Transfusion 风格的统一模型（第 12.13 课）。同一个原生预训练主干同时支撑理解头与生成头。

### 原生预训练的权衡

原生预训练并不免费：

- 算力。从零训练一个新 VLM 的成本与训练一个文本 LLM 相同——数百万 GPU 小时。事后适配复用已有的 LLM 权重，省掉了大部分成本。
- 数据。大规模图文交错语料很稀缺。OBELICS 是 141M 篇文档；MMC4 是 571M。纯文本数据则以 15T token 的规模供应。多模态预训练数据的稀缺是硬约束。
- 基座 LLM 复用。原生预训练放弃了日后替换新 LLM 的选项。事后方案只需重训适配器就能把 Llama-3.1 换成 Llama-4。

InternVL3 押的注是：对齐债务的代价大于复用损失的代价。benchmark 支持这一主张。产生成本的门槛让后来的实验室难以廉价复制。事后 VLM 会继续存在，因为对大多数项目来说它们仍然更便宜。

```figure
l5-native-pretrain
```

## Use It

`code/main.py` 是一个训练语料混合器与 ViR 路由模拟器。它：

- 接收目标语料配比（%text、%interleaved、%caption、%video）并计算各模态的预期步数。
- 在一批查询上模拟 ViR 路由（分布：50% 低细节、30% 中、20% 高细节）并报告平均 token 数。
- 给定编码器与 LLM 的 FLOPs，报告 DvD 吞吐估计。
- 打印事后预训练与原生预训练在参数、算力、数据和预期对齐债务症状上的并排对比。

## Ship It

本课产出 `outputs/skill-native-vs-posthoc-auditor.md`。给定一份拟议的 VLM 训练计划，它会审计应该走原生还是事后路线、标出对齐债务风险，并推荐语料配比。当你正在为一个新的开源 VLM 项目做规模评估、需要选定训练策略时就用它。

## Exercises

1. 估算 InternVL3-8B（原生预训练）与 LLaVA-OneVision-7B（事后）之间的算力差。GPU 小时数之比大约是多少？这个差距怎么解释？

2. InternVL3 报告的配比是 40% 文本 / 35% 交错 / 20% caption / 5% 视频。如果你的目标任务偏视频，提出一个新配比，并论证基座模型为什么仍然需要大量文本和 caption 数据。

3. 阅读 MM1.5 第 4 节关于遗忘的内容。说出事后训练中回归最大的具体 benchmark。这个回归的代价是多少？

4. ViR 把 60% 的流量路由到低分辨率编码。哪些类型的查询会被误路由（本需要高分辨率却被送到低分辨率）？提出三种路由器失效模式。

5. DvD 把视觉与 LLM 拆到不同的 GPU 上。在什么样的流量模式下，DvD 会损害而不是提升吞吐？

## Key Terms

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------|----------|
| Native multimodal pretraining | "From scratch together" | 文本 + 图像 + 视频 token 从第 1 步起就参与 loss，而不是后来外挂 |
| Alignment debt | "Post-hoc penalty" | 把视觉外挂到冻结 LLM 上所带来的、可测量的文本能力和答案一致性回归 |
| V2PE | "Variable visual pos encoding" | 按模态可学习的位置编码分配；InternVL3 对 M-RoPE 的继任方案 |
| ViR | "Resolution router" | 小分类器，在编码前为每个查询挑选所需最低分辨率，节省推理 token |
| DvD | "Decoupled deployment" | 视觉编码器在一个 GPU、LLM 在另一个 GPU，以流式交接；为大模型 VLM 吞吐翻倍 |
| InternVL-U | "Unified understanding + generation" | 2026 年的后续版本，为原生预训练主干加上图像生成头 |
| Interleaved corpus | "OBELICS / MMC4" | 文本与图像按自然阅读顺序排列的文档；原生预训练的原材料 |

## Further Reading

- [Chen 等 —— InternVL 1（arXiv:2312.14238）](https://arxiv.org/abs/2312.14238)
- [Zhu 等 —— InternVL3（arXiv:2504.10479）](https://arxiv.org/abs/2504.10479)
- [InternVL3.5（arXiv:2508.18265）](https://arxiv.org/abs/2508.18265)
- [InternVL-U（arXiv:2603.09877）](https://arxiv.org/abs/2603.09877)
- [Zhang 等 —— MM1.5（arXiv:2409.20566）](https://arxiv.org/abs/2409.20566)
