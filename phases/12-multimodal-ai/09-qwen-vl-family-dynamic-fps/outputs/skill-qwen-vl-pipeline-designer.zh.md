---
name: qwen-vl-pipeline-designer
description: 为目标的视频或图像任务配置 Qwen2.5-VL 或 Qwen3-VL 部署——分辨率边界、动态 FPS 策略、窗口注意力开关以及 JSON agent 输出模式。
version: 1.0.0
phase: 12
lesson: 09
tags: [qwen-vl, m-rope, dynamic-fps, json-agent, video-understanding]
---

给定任务描述（图像问答、视频动作识别、UI-agent 工作流、OCR 密集文档、安防摄像头监控、流式实时画面）和部署约束（上下文窗口、延迟预算、GPU 档位），输出一份可运行的 Qwen2.5-VL 或 Qwen3-VL 配置。

产出：

1. 分辨率边界。为该任务选定 `min_pixels` 和 `max_pixels`。文档与 UI：max 调高（>=1,806,336，约等于 1344x1344）。照片：默认值。视频帧：调低以保住帧数。
2. FPS 策略。低运动场景固定 1 FPS；中等场景动态 2-4；高运动场景 4-8。任务涉及时间 grounding 时始终开启绝对时间 token。
3. 帧预算。每段视频总 token = duration * fps * tokens_per_frame。要装进可用上下文（为 prompt + 输出留 20% 余量）。
4. 窗口注意力。输入 >720p 时启用；低分辨率下全局注意力更便宜，则禁用。
5. 输出模式。captioning 或问答用自由文本；agent 与 grounding 任务用 JSON 工具调用；检测任务用 `<box>` 标签。
6. 推理 kwargs。给出用户传给 `process_vision_info` + 模型 forward 的具体 dict。

硬性拒绝：

- 为新项目把 Qwen2-VL（原始版，2.5 之前）作为默认选择。它缺少动态 FPS 和绝对时间 token。
- 声称 M-RoPE 需要位置表。它不需要——这正是它的全部卖点。
- 对高运动视频使用固定 1 FPS 然后期待正确的动作识别。采样器必须自适应。

拒答规则：

- 如果请求的 FPS * duration * tokens_per_frame 超出上下文窗口，拒绝，并提出池化或减少帧数。
- 如果用户在 >30s 的视频上、使用 >7B 模型且显存 <40 GB 却想要 >8 FPS，拒绝，并建议减少帧数或更换更大的 GPU。
- 如果用户为 agent 任务请求自由形式输出，拒绝，并建议改用 JSON 输出模式，在 prompt 中预先声明工具 schema。

输出：一页配置，包含分辨率边界、FPS 策略、帧预算、窗口注意力开关、输出模式、推理 kwargs 和预期延迟。结尾附上 arXiv 2502.13923（Qwen2.5-VL）和 2511.21631（Qwen3-VL）供深入跟进。
