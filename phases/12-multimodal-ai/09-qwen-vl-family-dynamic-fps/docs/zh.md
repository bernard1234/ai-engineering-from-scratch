# Qwen-VL 家族与动态 FPS 视频

> Qwen-VL 家族——Qwen-VL（2023）、Qwen2-VL（2024）、Qwen2.5-VL（2025）、Qwen3-VL（2025）——是 2026 年最具影响力的开源视觉语言模型谱系。每一代都做出一个决定性的架构押注，而整个开源生态在十二个月内都会照抄：通过 M-RoPE 实现的原生动态分辨率、带绝对时间对齐的动态 FPS 采样、ViT 中的窗口注意力，以及结构化的 agent 输出格式。到 Qwen3-VL 时，配方已经稳定：一个支持原生宽高比输入的 2D-RoPE-ViT 编码器、一个映射到大 Qwen3 语言基座的 MLP projector，以及把 OCR、grounding 和 agent 行为作为一等目标的训练阶段。本课按时间顺序解读这个家族，让你理解每个旋钮为什么处在它现在的位置。

**Type:** Learn
**Languages:** Python（stdlib，M-RoPE 编码器 + 动态 FPS 采样器）
**Prerequisites:** Phase 12 · 06（patch-n'-pack）
**Time:** ~120 分钟

## Learning Objectives

- 计算 M-RoPE 的三轴旋转（时间、高度、宽度），并解释为什么三轴都不可或缺。
- 为一段视频选择动态 FPS 采样策略，并权衡每秒 token 数与事件检测准确率。
- 按顺序说出 Qwen-VL 的四代升级，以及每一代解锁了什么能力。
- 搭出一个 Qwen2.5-VL 风格的 JSON agent 输出格式，并从 VLM 响应中解析结构化工具调用。

## 问题场景

Qwen-VL 于 2023 年 8 月发布，是对 LLaVA-1.5 和 BLIP-2 的直接回应。Qwen 团队瞄准的差距有三方面：分辨率、视频和结构化输出。

分辨率：LLaVA-1.5 运行在 336x336。这对照片够用，对一张中文发票或密集的电子表格截图则毫无用处。Qwen-VL 的第一个创新是 448x448 加上带 grounding 的边界框输出，让模型能够"指"出东西。

视频：Video-LLaMA 堆叠逐帧编码器再把结果喂给 LLM。这对短片段有效，但对于时间轴本身就是信号的多分钟视频就不行了。Qwen 团队想要一个能理解时间的单一编码器。

结构化输出：LLaVA 输出自由文本。而 agent 需要 JSON。Qwen-VL 在包含以文本形式表示的边界框坐标的显式 JSON 输出格式上做了训练。

每一代 Qwen-VL 都在延伸这三条轴之一。

## 核心概念

### Qwen-VL（2023 年 8 月）

第一代：用 OpenCLIP ViT-bigG/14 作为编码器（2.5B 参数）、LLama 兼容的 Q-Former（1 步，256 个 query）、Qwen-7B 作为基座。贡献包括：

- 448x448 分辨率（当时开源 VLM 的 SOTA）。
- Grounding：在带有显式坐标 token 输出的图文对上训练。"The cat is at <box>(112, 204), (280, 344)</box>"。
- 从一开始就做中英双语训练。

当时的 benchmark：英文上可与 GPT-4V 竞争，中文上占据主导。grounding 监督才是真正的头条。

### Qwen2-VL（2024 年 9 月）—— M-RoPE 与原生分辨率

Qwen2-VL 用原生动态分辨率的 ViT 编码器取代了固定分辨率 + Q-Former 的堆栈。关键变化：

- 原生动态分辨率。ViT 接受任何可被 28 整除的 HxW（patch 14 加 2x 空间合并）。一张 1120x672 的图片（40x24 个合并后 patch）产生 960 个视觉 token。不缩放、不切块、不缩略图。
- M-RoPE（Multimodal RoPE）。每个 token 携带 3D 位置 (t, h, w) 而不是 1D。对图像 t=0，对视频 t = frame_index。RoPE 按每个轴各自的频率旋转 query/key 向量。没有位置 embedding 表。
- MLP projector。去掉 Q-Former；在合并后的 patch token 上用一个 2 层 MLP。
- 带动态 FPS 的视频。视频默认按 1-2 FPS 采样，但模型接受任意帧数。

结果：Qwen2-VL-7B 在多个多模态 benchmark 上与 GPT-4o 持平，并在 DocVQA 上超越它（94.5 对 88.4）。架构变化才是决定性的一步。

### Qwen2.5-VL（2025 年 2 月）—— 动态 FPS + 绝对时间

Qwen2.5-VL 的重大转变在视频上。动态 FPS 并不只是"需要时多采几帧"。论文把它形式化为：

- 绝对时间 token。不再使用位置索引（frame 0, 1, 2...），而是使用真实时间戳。"At 0:04, the cat jumps." 模型看到的是与帧 token 交错出现的 `<time>0.04</time>` token。
- 动态 FPS。慢速画面按 1 FPS 采样，动作场景按 4+ FPS 采样。由用户或训练方选择；M-RoPE 自适应。
- ViT 中的窗口注意力。空间注意力采用窗口化（块内局部）以提升吞吐；每隔几层插入一次全局注意力。
- 显式 JSON 输出格式。在工具调用数据上训练："{\"tool\": \"click\", \"coords\": [380, 220]}"。开箱即用，为 agent 做好准备。
- MRoPE-v2 缩放。位置随最大输入尺寸缩放，这样一段 10 分钟的视频不会耗尽频率范围。

Benchmark：Qwen2.5-VL-72B 在大多数视频 benchmark 上击败 GPT-4o，在文档任务上与 Gemini 2.0 持平，并创下开源模型 GUI grounding 的 SOTA（ScreenSpot：84% 准确率，GPT-4o 为 38%）。

### Qwen3-VL（2025 年 11 月）

Qwen3-VL 是一次以整合而非重构为主的增量升级：更大的 LLM 主干（Qwen3-72B）、扩展的训练数据、更好的 OCR、通过 Qwen3"thinking mode"带来的更强推理。ViT 和 M-RoPE 保持不变。论文的重点在于数据和训练改进，而非架构。

谱系结论：到 2025 年，Qwen-VL 架构已经稳定下来。后续世代扩展的是算力和数据，而不是新的基础构件。

### M-RoPE 的数学形式

经典 RoPE 用成对坐标把维度为 `d` 的 query `q` 按位置 `m` 旋转：

```
q_rot[2i]   = q[2i]   * cos(m * theta_i) - q[2i+1] * sin(m * theta_i)
q_rot[2i+1] = q[2i]   * sin(m * theta_i) + q[2i+1] * cos(m * theta_i)
theta_i     = 10000^(-2i/d)
```

M-RoPE 把隐藏维切成三个频带。假设 `d = 96`。分配 32 维给时间、32 维给高度、32 维给宽度。每个频带按自己轴上的位置旋转。位于 (t=5, h=10, w=20) 的 patch 会在其三个频带上分别施加 `R_t(5)`、`R_h(10)`、`R_w(20)` 的旋转。

文本 token 使用 `t = text_index, h = 0, w = 0`（或某种归一化选择），以保持兼容性。视频帧使用 `t = frame_time, h = row, w = col`。单张图像使用 `t = 0`。

好处是：一种位置编码同时处理文本、图像和视频，不需要分支代码，也不需要不同的位置表。

### 动态 FPS 采样逻辑

给定一段时长为 `T` 秒的视频和目标 token 预算 `B`：

1. 计算你负担得起的最大 FPS：`fps_max = B / (T * tokens_per_frame)`。
2. 从 `{1, 2, 4, 8}` 中选一个满足 `fps <= fps_max` 的目标 FPS。
3. 如果运动剧烈（光流启发式判断或用户明确要求），选更高的 FPS。如果运动平缓，选更低的。
4. 按选定 FPS 均匀采样；在帧之间插入 `<time>t</time>` token。

Qwen2.5-VL 隐式训练了这套逻辑；推理时由用户通过 `fps` 参数控制。一段 60 秒的动作序列按 4 FPS、每帧 81 个 token 计算 = 19440 个 token，在 32k 上下文中可以容纳。

### 结构化 agent 输出

Qwen2.5-VL 的 agent 训练明确瞄准结构化工具调用：

```
{
  "tool": "mouse_click",
  "coords": [1024, 512],
  "button": "left",
  "modifier": null
}
```

解析是确定性的：直接对模型输出做 JSON.parse。相比之下，自由形式的 "click at (1024, 512)" 需要正则表达式和歧义处理。正是这一转变让 Qwen2.5-VL 的 ScreenSpot 分数从 Qwen2-VL 的 55% 跃升到 84%。

```figure
mm-mrope-axes
```

## Use It

`code/main.py` 实现了：

- 针对混合文本、图像 patch 和视频帧的打包序列计算 M-RoPE 位置。
- 动态 FPS 采样器：给定 (duration, budget, motion_level)，选出 FPS 并输出帧时间戳。
- 一个玩具版 Qwen2.5-VL JSON 输出解析器，能处理带坐标字段的工具调用响应。

运行它，然后在 5 分钟视频上把固定 FPS 换成动态 FPS，体会其中的差别。

## Ship It

本课产出 `outputs/skill-qwen-vl-pipeline-designer.md`。给定一个视频任务（监控、agent、动作识别、无障碍），它会输出 Qwen2.5-VL 配置（帧预算、FPS 策略、窗口注意力开关、agent 输出模式）以及延迟估计。当你要为视频产品部署 Qwen-VL 家族模型时就用它。

## Exercises

1. 为一个位于 (t=3, h=5, w=7)、隐藏维 48（每频带 16 维，base theta 10000）的 patch 计算 M-RoPE 旋转。给出每个频带中前三对坐标的旋转角度。

2. 一段 10 分钟、1 FPS 的安防摄像头录像会产生多少帧？在 384 分辨率、3x pool 下，总共多少 token？Qwen2.5-VL 默认的 32k 上下文能处理吗？

3. 为一段 30 秒的网球对拉、一段 30 秒的菜谱演示、一段 30 秒的 UI-agent 录屏分别选择 FPS。用动态 FPS 逻辑为每一个给出理由。

4. Qwen2.5-VL 完全去掉了 Q-Former。为什么简单的 MLP 在 2025 年可行而在 2023 年不行？（提示：数据规模和编码器质量。）

5. 把三条 Qwen2.5-VL JSON 工具调用输出解析成 Python dict。格式错误的 JSON 会出什么问题，Qwen 的 cookbook 推荐什么恢复策略？

## Key Terms

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------|----------|
| M-RoPE | "Multimodal RoPE" | 在隐藏维中带有时间、高度、宽度三个频带的 3D 旋转位置编码 |
| Dynamic FPS | "Smart sampling" | 根据运动、时长和 token 预算为每段视频选择的帧采样率 |
| Absolute time token | "Timestamp token" | 交错在序列中的 `<time>t</time>`，让模型看到真实秒数而非帧索引 |
| Window attention | "Local attention" | 为提速把空间自注意力限制在小窗口内；周期性加入全局注意力 |
| Structured agent output | "JSON mode" | 通过训练数据监督教 VLM 输出带坐标和工具名、可被解析的 JSON |
| min_pixels / max_pixels | "Resolution bounds" | Qwen2.5-VL 的按请求控制项，限定总像素数从而限定 token 数 |
| Grounding | "Point-at-it" | 以文本 token 形式输出边界框坐标；自 Qwen-VL v1 起使用 |

## Further Reading

- [Bai 等 —— Qwen-VL（arXiv:2308.12966）](https://arxiv.org/abs/2308.12966)
- [Wang 等 —— Qwen2-VL（arXiv:2409.12191）](https://arxiv.org/abs/2409.12191)
- [Qwen 团队 —— Qwen2.5-VL 技术报告（arXiv:2502.13923）](https://arxiv.org/abs/2502.13923)
- [Qwen 团队 —— Qwen3-VL（arXiv:2511.21631）](https://arxiv.org/abs/2511.21631)
- [Zhu 等 —— InternVL3（arXiv:2504.10479）](https://arxiv.org/abs/2504.10479)
