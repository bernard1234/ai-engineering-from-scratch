---
name: provenance-audit
description: 跨水印与 C2PA 元数据审计内容部署的 provenance 链。
version: 1.0.0
phase: 18
lesson: 23
tags: [watermarking, synthid, stable-signature, c2pa, provenance]
---

给定一个带有 provenance 主张的内容部署，审计其 provenance 链。

产出：

1. 水印清单。列出每种模态（文本、图像、音频、视频）以及各自施加的水印。没有水印 = 没有检测路径。
2. 水印鲁棒性。对每种水印，点明它能经受的对抗类别（压缩、裁剪、改写、微调）。按 Kirchenbauer 2023 第 6 节（改写）与 2024 年的“Stable Signature is Unstable”（微调）标出局限。
3. C2PA 覆盖。是否附加了 C2PA 元数据？签名链是否来自可信身份？元数据可被剥离；存在并不充分。
4. 跨模态检测器。是否有跨模态的统一检测器（SynthID 2025），还是只有模态特定的检测器？
5. 监管对齐。部署是否满足 EU AI Act 第 50 条的透明度义务（2026 年 8 月生效）？是否符合透明度准则（2026 年 6 月定稿）？

硬性拒绝：
- 任何没有点明机制与检测器的“水印”主张。
- 任何仅依据水印缺失得出的“真实性”主张（模型未加水印 ≠ 真实）。
- 任何未评估 Fernandez 2024 移除攻击的图像 provenance 主张。

拒绝规则：
- 如果用户问“这是否能检测所有 AI 内容”，拒绝二元主张；水印是模型特定的。
- 如果用户要求通用的 provenance 方案，拒绝，并指向水印 + C2PA 的分层方法。

输出：一页审计，填写上述五个部分，按模态标出鲁棒性缺口，并点明单个价值最高的补充控制。各引用 SynthID（Google DeepMind）、Stable Signature（Fernandez et al. 2023）与 C2PA 一次。
