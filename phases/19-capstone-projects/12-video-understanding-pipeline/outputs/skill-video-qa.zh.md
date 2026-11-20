---
name: video-qa
description: 构建一条视频理解流水线，包含场景分割、多向量索引、时间定位与带时间戳的引用。
version: 1.0.0
phase: 19
lesson: 12
tags: [capstone, video, multimodal, gemini, qwen-vl, molmo, transnet, qdrant]
---

给定 100 小时视频，构建一条摄取流水线和一个查询系统，用（start, end）时间戳加上帧预览来回答自然语言问题。

构建计划：

1. 摄取视频（YouTube URL 或 MP4）；必要时降采样到 720p。
2. 用 TransNetV2 或 PySceneDetect 做场景分割；产出 `[{scene_id, start_ms, end_ms, keyframe_path}]`。
3. 用 Whisper-v3-turbo（faster-whisper）做 ASR，产出词级时间戳；按场景切片。
4. 用 Gemini 2.5 Pro 或 Qwen3-VL-Max 或 Molmo 2 做 VLM captioning；产出 caption + 帧 embedding。
5. Qdrant 多向量索引，每个场景三个命名向量（caption_emb、frame_emb、transcript_emb）和 payload {video_id, scene_id, start_ms, end_ms, keyframe_url}。
6. 查询：三路并行稠密检索；用倒数排名融合合并；top-k=5 场景。
7. 时间定位（TimeLens adapter 或 VideoITG）在 top 场景内细化（start, end）。
8. VLM 综合（Gemini 2.5 Pro），输入 query + top-3 场景片段 + transcript；要求 `(video_id, start_ms, end_ms)` 引用。
9. 在 ActivityNet-QA、NeXT-GQA，外加一个 100 条人工标注的自定义集上评估。报告总体准确率以及按问题类别（描述型、计数型、动作类型）的准确率。

评估标准：

| 权重 | 标准 | 衡量方式 |
|:-:|---|---|
| 25 | 时间定位 IoU | 在留出定位集上的 IoU |
| 20 | QA 准确率 | NeXT-GQA 与 100 条自定义集 |
| 20 | 摄取吞吐 | 每美元索引的视频小时数 |
| 20 | UI 与引用 UX | 时间戳链接、缩略图条、跳转到帧 |
| 15 | 幻觉率 | 分别报告计数型与动作类型准确率 |

硬性否决：

- 每个场景只池化单个向量的流水线。要让类别差异显现，多向量是必需的。
- 没有（start, end）引用的回答。
- 只报告一个总体准确率而没有计数/动作子集细分。
- 不直接接收场景帧的 VLM 综合（纯文本输入会丢失视觉定位）。

拒绝规则：

- 拒绝提供许可证来源不清的视频；要求每个 video_id 都带许可证标签。
- 拒绝在高于实测吞吐的摄取速率下声称「实时」响应。
- 拒绝把计数/动作幻觉数字藏进总体准确率里。

输出：一个仓库，包含场景分割 + ASR + captioning 流水线、多向量 Qdrant collection、时间定位 adapter、带时间戳深链的 Next.js 15 查看器、三个 benchmark 的 eval 结果（ActivityNet-QA、NeXT-GQA、自定义），以及一份书面说明，列出你观察到的三类计数或动作类型失败类别，以及分别降低每一类的检索或综合改动。
