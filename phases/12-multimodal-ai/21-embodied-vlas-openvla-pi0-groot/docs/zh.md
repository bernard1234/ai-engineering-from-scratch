# 具身 VLA：RT-2、OpenVLA、π0、GR00T

> 第一次有模型从网站上读懂一份菜谱并在厨房机器人上执行，是 RT-2（Google DeepMind，2023 年 7 月）。RT-2 把动作离散化为文本 token，在网页数据加机器人动作数据上联合微调一个 VLM，并证明了网页规模的视觉-语言知识可以迁移到机器人控制。OpenVLA（2024 年 6 月）交付了开放的 7B 参考实现。Physical Intelligence 的 π0 系列（2024-2025）加入了 flow matching 动作专家。NVIDIA 的 GR00T N1（2025 年 3 月）为规模化人形机器人提供了双系统（System 1 / System 2）控制。VLA 原语——vision-language-action，一个既能看、又能读、还能动的单一模型——是连接本阶段理解模型与第 15 阶段自主系统的桥梁。

**Type:** Learn
**Languages:** Python（stdlib，action tokenizer + VLA 推理骨架）
**Prerequisites:** Phase 12 · 05（LLaVA）、Phase 15（Autonomous Systems，引用）
**Time:** ~180 分钟

## Learning Objectives

- 描述动作 tokenization：离散 bin 编码（RT-2）、FAST 高效动作 token、连续 flow matching 动作（π0）。
- 解释为什么在网页 + 机器人数据上联合微调能保留对新任务的通用知识迁移能力。
- 在同一机器人任务上比较 OpenVLA（开放 7B Llama+VLM）、π0（flow matching）与 GR00T N1（双系统）。
- 说出 Open X-Embodiment 数据集的名字及其作为 RT-X 训练语料的角色。

## 问题场景

能按自然语言指令做家务的机器人，自 1970 年代以来一直是研究目标。2020 年代的答案是 vision-language-action（VLA）模型。架构与做 VQA 的 VLM 相同，但输出的是动作（关节力矩、末端执行器位姿、离散命令），而不是文本。

VLA 特有的挑战：

1. 动作空间是连续的（关节角、力），且维度很高（7 自由度机械臂 + 3 自由度夹爪 = 30 Hz 下 10 个维度）。
2. 机器人专属训练数据稀缺。Open X-Embodiment 约有 100 万条轨迹；而网页文本-图像数据有 50 亿+。
3. 控制频率很关键。30 Hz 的控制回路意味着每个动作只有 33ms 预算。
4. 安全。一个错误的动作会损坏硬件、伤害人类或破坏财产。

## 核心概念

### 动作 tokenization（RT-2）

RT-2 的技巧：把每个关节目标表示为一个量化后的文本 token。将归一化到 [-1, 1] 的区间离散化为 256 个 bin，把每个 bin 映射到一个词表 ID。10 自由度的动作在每个控制步就变成 10 个 token。

在一个混合数据集上联合微调 PaLM-X VLM：

- 网页图文对（captioning、VQA）。
- 机器人演示，动作以 token 形式表示。

模型看到 “pick up the red cube”（语言）→ 图像（视觉）→ 10 个 token 的动作序列（离散化的关节目标）。网页预训练保留了通用知识迁移能力：即便 “fast-moving” 并未出现在训练数据中，RT-2 也能执行 “move towards the fast-moving object”。

RT-2 论文中推理频率为 3-5 Hz，瓶颈在于 VLM 的自回归解码。

### OpenVLA —— 开放的 7B 参考实现

OpenVLA（Kim 等，2024 年 6 月）是开放权重的 RT-2 等价物。7B Llama 骨干、DINOv2 + SigLIP 双视觉编码器、256 个 bin 的动作 tokenization。

在 Open X-Embodiment（覆盖 22 种机器人的 97 万条轨迹）上训练。自带 LoRA 微调支持，便于适配新机器人。

推理：在 A100 上量化后可达 4-5 Hz。对于慢速操作足够快，但撑不起高频控制。

### FAST tokenizer —— 更快的 action 解码

Pertsch 等（2024）指出离散 bin tokenization 效率低下——大多数动作都聚集在 bin 空间的一小块区域。FAST（Frequency-domain Action Sequence Tokenizer）通过 DCT 压缩动作序列，再对系数做量化。

一条 30 步的动作轨迹原本需要 300 个离散 bin token，现在变成约 10 个 FAST token。推理速度提升 3-5 倍，且不损失质量。

### π0 与 flow matching 动作

Physical Intelligence 的 π0（Black 等，2024 年 10 月）用一个 flow matching 动作专家取代离散动作 token：

- 一个小型动作 transformer 读取 VLM 的 hidden states，通过 rectified flow 输出连续的 50 步动作序列。
- 动作头用 flow matching 损失训练；VLM 的预训练保持不变。
- 推理：约 5 步去噪即可输出完整动作序列，实际等效于 50 Hz 控制。

π0 的主张：在大量操作任务上优于 OpenVLA 和 Octo。连续动作的表述形式保留了离散化所破坏的平滑性。

π0.5 和 π0-FAST 是增量升级。π0-FAST 将 FAST tokenization 与 flow matching 结合。

### GR00T N1 —— 面向人形机器人的双系统

NVIDIA 的 GR00T N1（2025 年 3 月）为人形机器人（>30 自由度、全身）而建：

- System 2：一个大 VLM 读取场景 + 指令，以约 1 Hz 产出高层子目标。
- System 1：一个小型动作头 transformer，以子目标为条件产出 50-100 Hz 的低层关节命令。

这种拆分对应 Kahneman 的快慢思考：System 2 负责规划，System 1 负责执行。好处是：VLM 规模的慢速规划不会阻塞快速控制；System 1 保持小巧以控制时延。

GR00T N1.7（2025 年底）改进了数据规模扩展。GR00T 使用来自 Omniverse 的 sim-to-real 数据做微调。

### Open X-Embodiment

训练数据。RT-X（2023 年 10 月）汇集了 22 个数据集，覆盖 22 种机器人的 100 万条轨迹。Open X-Embodiment 是大家共用的语料：

- ALOHA / Bridge V2 / Droid / RT-2 Kitchen / Language Table。
- 每个样本：（机器人状态、相机视角、指令、动作序列）。
- 训练规范：统一动作空间、归一化关节范围、调整相机分辨率。

OpenVLA 和 π0 都在 Open X-Embodiment 上训练。到任一具体机器人的域差距，通过在 100-1000 条任务专用演示上做 LoRA 微调来弥合。

### 联合微调 vs 纯机器人数据

联合微调把网页 VQA 数据与机器人轨迹混合。比例很关键：VQA 过多，模型会忘记动作；机器人数据过多，模型会丢失通用知识。

RT-2 的比例：约 1:1。OpenVLA：网页对机器人约 0.5:1。π0：类似。精确比例是需要按数据集规模调的超参数。

纯机器人数据训练出的模型只擅长特定任务，遇到分布外指令就会失败。联合微调的差别就在于能否从 “pick up the red cube（演示里有的）” 泛化到 “pick up the third largest object from the left（全新措辞）”。

### 安全与动作限制

每个生产级 VLA 都配有：

- 硬性关节限位（力矩不能超过规格）。
- 速度限制（软裁剪）。
- 工作空间边界（末端执行器不能离开桌面）。
- 新任务需要 human-in-the-loop 审批。

这些检查位于 VLA 之外，属于控制层。VLA 的输出是建议，不是命令。

```figure
mm-action-tokens
```

## Use It

`code/main.py`：

- 实现 256 bin 的动作 tokenization 与 de-tokenization。
- 给出一个基于 DCT + 量化的 FAST tokenizer 草图。
- 比较（discrete-bin、FAST、continuous-flow）三种方式下每个动作步的 token 数。
- 打印 RT-2 → OpenVLA → π0 → GR00T 的谱系摘要。

## Ship It

本课产出 `outputs/skill-vla-action-format-picker.md`。给定机器人任务（操作、导航、人形全身），在 discrete-bin + RT-2、FAST + OpenVLA、flow matching + π0 或双系统 + GR00T 之间做选择。

## Exercises

1. 一条 10 自由度机械臂，控制频率 30 Hz。256 bin 的离散 bin tokenization 每秒发出多少 token？7B 的 VLM 跟得上吗？

2. FAST tokenization 把 30 步轨迹压缩到约 10 个 token。如果轨迹包含高频运动（例如打鼓），用户会损失什么？

3. π0 的 flow matching 动作头约 5 步去噪。将其吞吐与 OpenVLA 在 4-5 Hz 下的自回归解码做比较。

4. GR00T 的 System 1 / System 2 拆分对应 Kahneman。提出一种不同的拆分（System 3？），可能有助于双足行走。

5. 阅读 Open X-Embodiment 第 4 节关于数据集整理的内容。说出三条防止域泄漏的整理规则。

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|------|-----------------|------------------------|
| VLA | “Vision-language-action” | 接收图像 + 指令并输出动作命令的模型 |
| Action tokenization | “离散 bin” | 把连续关节目标按每一维量化为 256 个 bin，每个 bin 是一个词表 ID |
| FAST tokenizer | “频域动作 token” | DCT + 量化，把 30 步轨迹压缩到约 10 个 token |
| Co-fine-tune | “混合网页 + 机器人” | 在网页 VQA 数据与机器人演示上一起训练，以保留通用知识 |
| Flow-matching action head | “π0 连续输出” | 通过 rectified flow 输出 50 步动作序列的小型 transformer |
| System 1 / System 2 | “双系统控制” | 大 VLM 慢速规划、小动作头快速执行；GR00T 的模式 |
| Open X-Embodiment | “RT-X 数据集” | 100 万轨迹的跨机器人数据集；训练语料 |

## Further Reading

- [Brohan 等 —— RT-2（arXiv:2307.15818）](https://arxiv.org/abs/2307.15818)
- [Kim 等 —— OpenVLA（arXiv:2406.09246）](https://arxiv.org/abs/2406.09246)
- [Black 等 —— π0（arXiv:2410.24164）](https://arxiv.org/abs/2410.24164)
- [NVIDIA —— GR00T N1（arXiv:2503.14734）](https://arxiv.org/abs/2503.14734)
- [Open X-Embodiment Collab —— RT-X（arXiv:2310.08864）](https://arxiv.org/abs/2310.08864)
