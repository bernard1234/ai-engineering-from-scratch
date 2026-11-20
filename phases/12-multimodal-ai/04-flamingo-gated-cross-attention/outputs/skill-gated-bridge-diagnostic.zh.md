---
name: gated-bridge-diagnostic
description: 在开放 VLM 配置中识别 Flamingo 谱系的设计要素，并诊断冻结与门控方面的问题。
version: 1.0.0
phase: 12
lesson: 04
tags: [flamingo, idefics, openflamingo, gated-cross-attention, interleaved-inputs]
---

给定一个开放 VLM checkpoint 及其配置（层结构、cross-attention 调度、门控参数化方式、训练配方），识别它使用了哪些 Flamingo 谱系要素，并诊断门控设置不当的常见症状。

产出：

1. 谱系清单。标记是否存在（Perceiver resampler 有/无、门控 cross-attn 频率 M、tanh vs sigmoid 门、alpha 初值、LLM 冻结深度）。
2. 交错输入支持。解析模型期望的 prompt 格式；确认或否定其对多图、视频与 few-shot in-context prompt 的支持。
3. 视觉 token 预算。计算每张图的成本：K 个 latent x N 个 cross-attn 插入点。与同等图像数量下 BLIP-2 式单输入桥做对比。
4. 门控诊断。根据训练 loss 曲线或 benchmark 退化情况，判断门是开得太快（丧失文本能力）、太慢（无法利用视觉输入），还是标定失当（视觉 token 与文本竞争而非增益）。
5. 修复配方。给出具体的参数修复：若文本退化，把 alpha 初值设得更接近 0；调高门参数的 learning rate；或在最初 N 步冻结门。

硬性拒绝：
- 不检查 resampler 与门控调度就把任何开放 VLM 当作 "一个 Flamingo"。Idefics2 放弃了 resampler；不加限定地把它标为 Flamingo 谱系是错误的。
- 假设零初始化总能撑过训练。一些开放复现使用较小的非零初值，以初始稳定性换取更快收敛。
- 声称门控 cross-attention 在所有任务上都严格优于单一 BLIP-2 桥。在配小 LLM 的单图 VQA 上，额外的 cross-attn 层纯属成本。

拒答规则：
- 若该 checkpoint 的训练配方未公开，拒绝并解释为什么门控诊断需要知道门控调度。
- 若调用方要求与 Gemini 或 Claude（专有模型）对比，拒绝——它们的门控机制未公开。
- 若范围内的 VLM 是 early-fusion 模型（Chameleon、Emu3），拒绝——门控只适用于 adapter 式 VLM。

输出：一页纸的诊断，包含谱系清单、交错输入能力矩阵、token 预算、门控诊断与具体修复配方。结尾用一段 "下一步该读什么" 指向第 12.05 课（LLaVA）了解另一种 projector 路线，或第 12.11 课（Chameleon）了解 early-fusion 这条逃生通道。
