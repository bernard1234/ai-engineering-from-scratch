---
name: clip-zero-shot
description: 使用 CLIP / SigLIP checkpoint 运行零样本图像分类，产出带相似度分数的排序预测。
version: 1.0.0
phase: 12
lesson: 02
tags: [clip, siglip, zero-shot, vision-language]
---

给定一组图像（文件路径或 URL）和一组候选类别名，使用声明的 CLIP 或 SigLIP checkpoint 产出排序后的零样本分类。该 skill 只做预测；它不训练也不微调。

产出：

1. Prompt 构造。为每个类别构造 N 个文本模板（默认：`a photo of a {class}`、`a picture of a {class}`、`an image of a {class}`）。用文本编码器嵌入每个 prompt 并取平均，形成类别原型。
2. 图像 embedding。用声明的视觉编码器嵌入每张输入图像。把两侧都归一化为单位长度。
3. 排序预测。计算每张图像 embedding 与每个类别原型之间的余弦相似度。返回带分数的 top-1 和 top-5。
4. Checkpoint 元数据。列出所用的确切 Hugging Face checkpoint（例如 `openai/clip-vit-large-patch14` 或 `google/siglip2-so400m-patch14-384`）及其期望的分辨率。
5. 诚实性提示。说明对预训练分布之外的类别做零样本并不可靠；把 top-1 分数作为置信度代理展示出来，并在低于 0.2 时给出警告。

硬性拒答：
- 任何把输出表述为调用方所提供列表之外类别之确定性标签的用法。
- 声称不同 checkpoint 之间的分数可比较；SigLIP 与 CLIP 的分数量纲不同。
- 在缺少下游同意政策的情况下，对已知包含人物的图像运行。

拒答规则：
- 如果调用方要求分类到医疗、法律或安全关键类别（诊断、身份、受保护属性），拒绝并引导至有审计追踪的监督模型。
- 如果调用方只提供一个类别名（没有备选项的单向分类），拒绝 —— 零样本至少需要两个候选才有意义。
- 如果未指定 checkpoint，拒绝并询问是（CLIP、OpenCLIP、SigLIP、SigLIP 2）中的哪一个，以及哪个规模。

输出：每张图像带余弦相似度分数的 top-5 预测排序列表、checkpoint 名称、所用 prompt 模板，以及一个置信度标记。结尾附一段"接下来读什么"，指向课程 12.06 了解 NaFlex（处理可变宽高比），或 SigLIP 2 论文做更深入的研读。
