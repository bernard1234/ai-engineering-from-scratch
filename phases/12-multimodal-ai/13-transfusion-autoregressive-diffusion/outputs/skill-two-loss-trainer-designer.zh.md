---
name: two-loss-trainer-designer
description: 设计一套 Transfusion / MMDiT 式的双 loss 训练方案（一种模态用 NTP，另一种用 diffusion），包含 loss 权重、mask 设计与调度。
version: 1.0.0
phase: 12
lesson: 13
tags: [transfusion, mmdit, two-loss, flow-matching, hybrid-attention]
---

给定一份多模态训练规格（两种模态、哪一种走 NTP 哪一种走 diffusion、目标模型规模、目标样本长度），设计一套可用的双 loss 方案。

产出：

1. 模态划分。哪些 token 是离散的（NTP），哪些是连续的（diffusion）。按内容类型给出理由（文本始终离散；图像、音频、视频两种方式都可）。
2. Attention mask。为一条示例序列画出块三角 mask。标明双向区域与因果区域。
3. Loss 权重。（text_loss, image_loss）的初始权重。建议按目标梯度范数比例来调。引用 Transfusion 约 0.1 的默认值。
4. Flow matching 与 DDPM 的取舍。选择 diffusion 变体；flow matching 数学更简单，rectified flow 推理步数更少。
5. 推理方案。NTP 路径（对文本做自回归采样）+ diffusion 路径（对图像 patch 做条件去噪）。明确去噪步数（10-30）。
6. MMDiT 还是 Transfusion 的划分。何时加入模态专属 block 权重（MMDiT）、何时完全共享（Transfusion）；按参数量给出经验法则。

硬性拒绝：
- 声称一个 mask 适配所有序列。每个样本的图像跨度不同，需要各自的块三角 mask。
- 使用 DDPM 而不用 rectified flow 或 flow matching。后两者需要的推理步数更少，也更易调。
- 用固定权重来平衡 loss，而不测量梯度范数比例。

拒绝规则：
- 如果用户只需要理解（图像进、文本出），拒绝并推荐 LLaVA 式的晚期融合（12.05 课）。双 loss 是用于生成的。
- 如果用户想要 <1B 的模型，拒绝双 loss 并推荐离散 token（Chameleon）——在小规模下 diffusion head 会欠拟合。
- 如果用户负担不起双推理（NTP + diffusion 循环），拒绝并推荐 Show-o（离散 diffusion，单循环）或 Emu3。

输出：一页设计，包含模态划分、mask 示意图、loss 权重、flow 变体、推理方案，以及 MMDiT 与共享方案的决策。结尾引用 arXiv 2408.11039（Transfusion）和 2403.03206（SD3）作为权威参考。
