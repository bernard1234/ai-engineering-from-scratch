# Capstone 12 — 视频理解流水线（场景、QA、搜索）

> Twelve Labs 把 Marengo + Pegasus 产品化。VideoDB 交付了面向视频的 CRUD API。AI2 的 Molmo 2 发布了开放的 VLM checkpoint。Gemini 的长 context 原生就能处理数小时视频。TimeLens-100K 在大规模上定义了时间定位。2026 年的流水线已经定型：场景分割、逐场景 caption + embedding、transcript 对齐、多向量索引，以及一个用 (start, end) 时间戳加帧预览来作答的查询。这个 capstone 要求摄取 100 小时视频、命中共公开 benchmark，并测量计数类与动作类问题上的幻觉。

**Type:** Capstone
**Languages:** Python（流水线）、TypeScript（UI）
**Prerequisites:** 第 4 阶段（CV）、第 6 阶段（speech）、第 7 阶段（transformers）、第 11 阶段（LLM engineering）、第 12 阶段（multimodal）、第 17 阶段（infrastructure）
**Phases exercised:** P4 · P6 · P7 · P11 · P12 · P17
**Time:** 30 小时

## 问题场景

长视频 QA 是 2026 年规模下最吃带宽的多模态问题。Gemini 2.5 Pro 能原生读一段 2 小时的视频，但要把 100 小时视频摄取进一个可查询的语料，仍然需要场景级索引。生产形态组合了：场景分割（TransNetV2 或 PySceneDetect）、用 VLM 做逐场景 caption（Gemini 2.5、Qwen3-VL-Max 或 Molmo 2）、transcript 对齐（Whisper-v3-turbo 带词级时间戳），以及一个把 caption、frame embedding 与 transcript 并排存储的多向量索引。查询流水线用 (start, end) 时间戳加帧预览来作答。

benchmark 是公开的（ActivityNet-QA、NeXT-GQA），再加上你自己那套 100 条查询的自定义集。计数类与动作类问题上的幻觉是公认的难点失效类别；这个 capstone 明确测量它。

## 核心概念

摄取时有三条流水线并行。**场景分割**把视频切成场景。**VLM captioning** 为每个场景生成一条 caption，并从关键帧生成一个 frame embedding。**ASR 对齐**产出词级时间戳。三路数据流按 (scene_id, time range) 做 join。每个场景在多向量索引（Qdrant）中得到三种向量：caption embedding、关键帧 embedding、transcript embedding。

查询时，自然语言问题同时对三种向量发起检索；结果用 RRF 合并；一个时间定位适配器（TimeLens 风格）在 top 场景内细化 (start, end) 窗口。VLM 合成器（Gemini 2.5 Pro 或 Qwen3-VL-Max）接收 query + top 场景 + 裁剪后的帧，并带引用时间戳与帧预览作答。

幻觉的测量很重要。计数类问题（“有几个人进了房间？”）与动作类问题（“厨师是先倒油还是先搅拌？”）出了名地不可靠。要把这类准确率与描述类问题分开报告。

## 架构

```
video file / URL
      |
      v
PySceneDetect / TransNetV2  (scene segmentation)
      |
      +--- per-scene keyframe --- VLM caption + frame embedding
      |                            (Gemini 2.5 Pro / Qwen3-VL-Max / Molmo 2)
      |
      +--- audio channel --- Whisper-v3-turbo ASR + word timestamps
      |
      v
multi-vector Qdrant: {caption_emb, keyframe_emb, transcript_emb}
      |
query:
  dense queries against all three -> RRF merge -> top-k scenes
      |
      v
TimeLens / VideoITG temporal grounding (refine start/end within scene)
      |
      v
VLM synth: query + top scenes + frame previews
      |
      v
answer + (start, end) timestamps + frame thumbs + citations
```

## 技术栈

- 场景分割：TransNetV2（2024-26 年的 SOTA）或 PySceneDetect
- ASR：Whisper-v3-turbo，通过 faster-whisper 带词级时间戳
- VLM captioner + 作答模型：Gemini 2.5 Pro 或 Qwen3-VL-Max 或 Molmo 2
- 时间定位：TimeLens-100K 训练的适配器或 VideoITG
- 索引：Qdrant，支持多向量（caption / frame / transcript）
- UI：Next.js 15，配 HTML5 视频播放器与场景缩略图
- 评测：ActivityNet-QA、NeXT-GQA、自建 100 题人工标注集
- 幻觉 benchmark：计数与动作类子集，带人工标注

```figure
cf-scene-index
```

## Build It

1. **摄取遍历器。** 接受 YouTube URL 或本地 MP4。必要时降采样到 720p。持久化 `{video_id, file_path}`。

2. **场景分割。** 运行 TransNetV2 或 PySceneDetect，产出 `[{scene_id, start_ms, end_ms, keyframe_path}]`。目标 100 小时：约 6k-8k 个场景。

3. **ASR。** 对音频运行 Whisper-v3-turbo；导出词级时间戳；切成逐场景的 transcript 片段。

4. **VLM captioning。** 对每个场景，用关键帧与一个简短的 caption 模板调用 Gemini 2.5 Pro（或 Qwen3-VL-Max）。产出 caption + frame embedding。

5. **多向量索引。** Qdrant collection，含三个具名向量。payload：`{video_id, scene_id, start_ms, end_ms, keyframe_url}`。

6. **查询。** 自然语言问题发起三次稠密查询；用 reciprocal rank fusion 合并；top-k=5 个场景。

7. **时间定位。** 在 top 场景上运行 TimeLens 风格的适配器，在该场景内细化 (start, end) 窗口。

8. **VLM 合成。** 用 query + top-3 场景片段（以图像或短视频形式）+ transcript 调用 Gemini 2.5 Pro。要求给出 `(video_id, start_ms, end_ms)` 引用。

9. **评测。** 跑 ActivityNet-QA 与 NeXT-GQA。构建一套 100 条查询的自定义集。报告总体准确率 + 按类别拆分（计数、动作、描述）。

## Use It

```
$ video-qa ask --url=https://youtube.com/watch?v=X "how many cars pass the intersection in the first minute?"
[scene]    23 scenes detected
[asr]      transcript complete, 4m12s
[index]    69 vectors written (23 scenes x 3)
[query]    top scene: scene 3 [01:32-01:54], confidence 0.84
[ground]   refined window: [00:12-00:58]
[synth]    gemini 2.5 pro, 1.4s
answer:    5 cars pass the intersection between 00:12 and 00:58.
citations: [scene 3: 00:12-00:58]
          [frame preview at 00:14, 00:27, 00:44, 00:51, 00:57]
```

## Ship It

`outputs/skill-video-qa.md` 是交付物。给定一个 YouTube URL 或上传的视频，流水线索引其场景，并以带时间戳引用的方式回答问题。

| 权重 | 标准 | 衡量方式 |
|:-:|---|---|
| 25 | 时间定位 IoU | 在留出的定位集上的交并比 |
| 20 | QA 准确率 | NeXT-GQA 与自建 100 条查询 |
| 20 | 摄取吞吐 | 每美元能处理多少小时视频 |
| 20 | UI 与引用体验 | 时间戳链接、缩略图条、跳转到帧 |
| 15 | 幻觉率 | 计数与动作类准确率分开报告 |
| **100** | | |

## Exercises

1. 把 captioning 那一步的 Gemini 2.5 Pro 换成 Qwen3-VL-Max。在 50 个场景的人工评分样本上报告 caption 质量差。

2. 把逐场景的 frame embedding 从多向量缩减为一个池化向量。测量检索性能的退化。

3. 构建一个“严格计数”模式：合成器为每个被计数的实例提取时间戳，用户点击验证。测量用户验证是否降低幻觉。

4. 对摄取成本做 benchmark：在三种 VLM 选择下比较每美元可处理的视频小时数。挑出最优点。

5. 增加说话人分离 transcript：对音频运行 pyannote 说话人分离，并按说话人嵌入 transcript。演示“Alice 关于 X 说了什么？”这类查询。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Scene segmentation | “镜头检测” | 在镜头边界处把视频切成场景 |
| Multi-vector index | “caption + frame + transcript” | 每种表示各有一个具名向量的 Qdrant collection |
| Temporal grounding | “它到底发生在什么时候” | 为查询答案细化 (start, end) 窗口 |
| Frame embedding | “视觉表示” | 关键帧的向量 embedding；用于场景视觉相似度 |
| RRF fusion | “倒数排名融合” | 跨多个有序列表的合并策略；经典的混合检索技巧 |
| Counting hallucination | “数错了” | VLM 在“有多少个 X”类问题上的已知失效模式 |
| ActivityNet-QA | “视频 QA benchmark” | 长视频 QA 准确率 benchmark |

## Further Reading

- [AI2 Molmo 2](https://allenai.org/blog/molmo2) — 开放的 VLM checkpoint
- [TimeLens (CVPR 2026)](https://github.com/TencentARC/TimeLens) — 大规模时间定位
- [Gemini Video 长 context](https://deepmind.google/technologies/gemini) — 托管方案的参考
- [VideoDB](https://videodb.io) — 面向视频的 CRUD API 参考
- [Twelve Labs Marengo + Pegasus](https://www.twelvelabs.io) — 商业方案参考
- [TransNetV2](https://github.com/soCzech/TransNetV2) — 场景分割模型
- [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) — 经典的开源替代
- [ActivityNet-QA](https://arxiv.org/abs/1906.02467) — 参考评测 benchmark
