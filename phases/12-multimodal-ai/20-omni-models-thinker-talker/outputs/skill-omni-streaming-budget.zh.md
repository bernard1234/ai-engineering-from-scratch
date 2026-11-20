---
name: omni-streaming-budget
description: 为目标的 TTFAB 和功能集，规划 Thinker-Talker 流式语音流水线（Qwen-Omni / Moshi / Mini-Omni）的规模。
version: 1.0.0
phase: 12
lesson: 20
tags: [qwen-omni, moshi, mini-omni, streaming, ttfab, thinker-talker]
---

给定一份语音优先的产品规格（目标 TTFAB、麦克风采样率、是否含视觉输入、是否双语、是否全双工）和一条算力约束（GPU 档位、预算），规划 Thinker-Talker 流水线的规模。

产出：

1. 模型家族选择。Moshi（延迟最佳）、Qwen2.5-Omni（开源功能最全）、Qwen3-Omni（前沿质量）、Mini-Omni（最简单）。
2. Thinker 与 Talker 的规模。TTFAB <400ms 用 7B Thinker + 200-300M Talker。质量优先用 70B+ Thinker，接受更高的 TTFAB。
3. TTFAB 拆解。逐组件的延迟估算。
4. 双工模式。默认用半双工 + VAD 轮次交替；产品需要附和时用全双工。
5. 视觉集成。对交错视频帧使用带绝对时间戳的 TMRoPE。
6. 部署形态。根据吞吐需求选择单 GPU 或拆分部署（Thinker 在 A 卡、Talker 在 B 卡）。

硬性拒绝：
- 提出 70B 的 Talker。Talker 必须小，才能跟上 speech token 速率。
- 使用非流式语音 decoder。TTFAB 会爆炸。
- 声称全双工即插即用。它需要专门的训练数据。

拒答规则：
- 如果目标 TTFAB <200ms，在单张 A100 上拒绝任何大于 Moshi 级（7B 融合）的方案。
- 如果产品需要流内生成音乐，拒绝这套架构，推荐单独的音乐流水线。
- 如果麦克风采样率是 48kHz 且有严格质量要求，指出需要更强的语音 encoder；不要盲目降采样。

输出：一页流式方案，包含模型选择、规模、TTFAB 拆解、双工模式、视觉策略、部署。结尾附上 arXiv 2503.20215（Qwen2.5-Omni）、2410.00037（Moshi）。
