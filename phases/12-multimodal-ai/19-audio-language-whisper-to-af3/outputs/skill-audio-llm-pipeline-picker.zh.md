---
name: audio-llm-pipeline-picker
description: 为一个音频任务选择级联式（Whisper + LLM）或端到端（AF3 / Qwen-Audio）流水线，并给出 encoder 与 bridge 配置。
version: 1.0.0
phase: 12
lesson: 19
tags: [whisper, audio-flamingo-3, qwen-audio, cascaded, end-to-end]
---

给定一个音频任务（转写、摘要、diarization、情绪、音乐、环境声音、deepfake、时间 grounding）和一条部署约束，选择一条流水线并输出配置。

产出：

1. 流水线选择。仅转写、或仅对干净语音做摘要时用级联；任何声学任务用端到端（AF3 / Qwen-Audio）。
2. Encoder 栈。Whisper-large-v3（语音强）、BEATs（音乐强）、AF-Whisper 拼接（均衡）。
3. Bridge 配置。非流式用 Q-former 32-64 个 query；流式用 RVQ token。
4. LLM 选择。成本优先用 Qwen2.5-7B，质量优先用 Qwen2.5-72B 或 AF3 的主干。
5. 按需 CoT。MMAU 类推理任务开启；追求转写吞吐时关闭。
6. MMAU 预期准确率。级联约 0.50，Qwen-Audio 约 0.60，AF3 约 0.72，Gemini 2.5 Pro 约 0.78。

硬性拒绝：
- 为音乐或情绪任务推荐级联。声学信号会丢失。
- 为多任务音频使用少于 32 个 query 的 Q-former。对推理来说 token 化不足。
- 声称 Whisper 单打独斗就能处理音乐。它是在语音主导的数据上训练的。

拒答规则：
- 如果用户需要流式对话音频（实时语音输入 / 语音输出），拒绝基于 Q-former 的 AF3，推荐 Moshi 或 Qwen-Omni（第 12.20 课）。
- 如果延迟预算 <500ms 且目标是简单转写，推荐级联 + 流式 Whisper。
- 如果任务是新型音频任务（deepfake、压缩伪影检测），拒绝开箱即用的方案，并建议在 AF3 上用合成数据做微调。

输出：一页方案，包含流水线选择、encoder 栈、bridge 配置、LLM 选择、CoT 开关、预期准确率。结尾附上 arXiv 2212.04356（Whisper）与 2507.08128（AF3）供深入阅读。
