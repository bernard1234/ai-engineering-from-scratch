# 推理平台经济学 — Fireworks、Together、Baseten、Modal、Replicate、Anyscale

> 2026 年的推理市场不再是 GPU 时间租赁。它分叉为定制芯片（Groq、Cerebras、SambaNova）、GPU 平台（Baseten、Together、Fireworks、Modal）和 API 优先的市场（Replicate、DeepInfra）。Fireworks 于 2026 年 5 月 1 日每 GPU 提价 $1/小时，加上 $4B 估值、每天处理 10T+ token，说明量驱动的模式行得通。Baseten 于 2026 年 1 月以 $5B 估值完成 $300M E 轮。竞争定位规则很简单：Fireworks 优化延迟，Together 优化目录广度，Baseten 优化企业级打磨，Modal 优化 Python 原生 DX，Replicate 优化多模态触达，Anyscale 优化分布式 Python。本课给你一张可以直接递给创始人的矩阵。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级单次调用经济学比较器)
**Prerequisites:** 第 17 阶段，第 01 课（Managed LLM Platforms），第 04 课（Serving Engine Internals）
**Time:** ~60 分钟

## Learning Objectives

- 说出三个细分市场（定制芯片、GPU 平台、API 优先），并把每个厂商映射到一个细分市场。
- 解释为什么“按 token”的 API 定价模型会向 serving 引擎的成本曲线靠拢，而不是向硬件的靠拢。
- 在至少三家厂商之间计算每请求的有效成本，并解释何时按分钟（Baseten、Modal）胜过按 token。
- 识别给定负载（serverless 突发型、稳定高吞吐、fine-tuned 变体、多模态）下哪个平台是合适的默认选择。

## 问题场景

你评估过托管超大规模平台。你决定需要更聚焦、更快的供应商——延迟选 Fireworks、广度选 Together、fine-tuned 定制模型选 Baseten。现在你有六个真实选项，而定价页各说各话。Fireworks 按 $/M token；Baseten 按 $/分钟；Modal 按 $/秒；Replicate 按 $/次预测。不建模负载，你就无法把它们放在同一把尺子上比较。

更糟的是，每个定价页背后的商业模式都不同。Fireworks 在共享 GPU 上跑自研引擎（FireAttention）；按 token 的费率反映了它们的利用率曲线。Baseten 给你 Truss 加专属 GPU；按分钟反映了排他性。Modal 是真正的 Python serverless——按秒计费，cold start 亚秒级。同样的产出（一个 LLM 响应），三种不同的成本函数。

本课对六家建模，并告诉你每家何时胜出。

## 核心概念

### 三个细分市场

**定制芯片** —— Groq（LPU）、Cerebras（WSE）、SambaNova（RDU）。在同一个模型上，decode 通常比基于 GPU 的集群快 5-10 倍。按 token 价格更高（2025 年底 Groq 在 Llama-70B 上约 $0.99/M），但对延迟敏感的场景无可匹敌。Groq 是语音 agent 和实时翻译的生产首选。

**GPU 平台** —— Baseten、Together、Fireworks、Modal、Anyscale。跑在 NVIDIA（2026 年是 H100、H200、B200）上，有时也跑 AMD。它是“裸 GPU 租赁”（RunPod、Lambda）与“超大规模托管服务”（Bedrock）之间的经济层。

**API 优先的市场** —— Replicate、DeepInfra、OpenRouter、Fal。目录广，按次预测或按秒付费，强调 time-to-first-call。

### Fireworks —— 延迟优化的 GPU 平台

- FireAttention 引擎（自研）；宣称在等效配置下延迟比 vLLM 低 4 倍。
- batch 档约为 serverless 费率的 50%，面向非交互负载。
- fine-tuned 模型以与基座模型相同的费率服务——这对那些为你的 LoRA 收取溢价的供应商是真正的差异点。
- 2026 年中：on-demand GPU 租赁自 2026 年 5 月 1 日起提价 $1/小时。大规模可谈量价。
- 财务信号：$4B 估值，每天处理 10T+ token。

### Together —— 广度优化

- 200+ 模型，开源发布在上游公开后几天内就上线。
- 在等效 LLM 模型上比 Replicate 便宜 50-70%——“AI Native Cloud”的定位就是量与目录。
- 推理 + fine-tuning + 训练合于一个 API。

### Baseten —— 企业级打磨优化

- Truss 框架：把依赖、密钥、serving 配置打包进一份 manifest 的模型打包方式。
- GPU 从 T4 到 B200。按分钟计费，cold start 缓解做得尚可。
- SOC 2 Type II，HIPAA-ready。金融科技与医疗的常见选择。
- $5B 估值，2026 年 1 月 E 轮（$300M，来自 CapitalG、IVP、NVIDIA）。

### Modal —— Python 原生优化

- 用纯 Python 写基础设施即代码。给一个函数加上 `@modal.function(gpu="A100")` 装饰器，一条命令部署。
- 按秒计费。预热后 cold start 2-4s；小模型 <1s。
- $87M B 轮，$1.1B 估值（2025）。在独立调研中开发者体验得分最强。

### Replicate —— 多模态广度

- 按次预测付费。图像、视频、音频模型的默认平台。
- 集成生态（Zapier、Vercel、CMS 插件）。
- 在 LLM 按 token 费率上竞争力较弱，但在多模态多样性上胜出。

### Anyscale —— Ray 原生

- 构建于 Ray 之上；RayTurbo 是 Anyscale 专有的推理引擎（与 vLLM 竞争）。
- 最适合分布式 Python 负载，其中推理步骤只是更大图里的一个节点。
- 托管 Ray 集群；与 Ray AIR 和 Ray Serve 紧密集成。

### 按 token 与按分钟 —— 各自何时胜出

当负载对延迟不敏感且呈突发型时，按 token 合理——只为用到的付费。当利用率高且可预测时，按分钟合理——一旦你把 GPU 跑满，就胜过按 token。

粗略规律：对持续利用率超过专用 GPU 约 30% 的负载，按分钟（Baseten、Modal）开始胜过按 token（Fireworks、Together）。低于该线，按 token 胜出，因为你避免了为空闲付费。

### 自研引擎才是真正的护城河

vLLM 和 SGLang 之上的每个平台都宣称有自研引擎。FireAttention、RayTurbo、Baseten 的推理栈。自研引擎的说法有营销注水成分——诚实的表述是：vLLM + SGLang 约占生产开源推理的 80%，而平台层的差异点是 DX、归因和 SLA。

### 你应该记住的数字

- Fireworks GPU 租赁：自 2026 年 5 月 1 日起提价 $1/小时。
- Fireworks 宣称：等效配置下延迟比 vLLM 低 4 倍。
- Together：在 LLM 上比 Replicate 便宜 50-70%。
- Baseten 估值：$5B（E 轮，2026 年 1 月，$300M）。
- Modal 估值：$1.1B（B 轮，2025）。
- 持续利用率超过约 30% 时，按分钟胜过按 token。

```figure
cost-per-token
```

## Use It

`code/main.py` 在合成负载上跨定价模型比较六家厂商。报告 $/天和有效的 $/M token。运行它，找出按 token 与按分钟之间的盈亏平衡点。

## Ship It

本课产出 `outputs/skill-inference-platform-picker.md`。给定负载画像、SLA 和预算，选出主推理平台并点名次选。

## Exercises

1. 运行 `code/main.py`。对一个 H100 上的 70B 模型，Baseten（按分钟）在什么持续利用率下胜过 Fireworks（按 token）？自己推导交叉点，并与经验法则比较。
2. 你的产品同时提供图像生成、对话和语音转文字。为每种模态选一个平台，并点名统一它们的 gateway 模式。
3. Fireworks 在你的主模型上提价 $1/小时。若 40% 的流量转到 batch 档（打五折），建模混合成本的影响。
4. 一家受监管客户要求 SOC 2 Type II + HIPAA + 专属 GPU。哪三个平台可行，哪一个在 FinOps 上胜出？
5. 比较 Llama 3.1 70B 在 Fireworks serverless、Together on-demand、Baseten 专属、Replicate API 上每 1,000 次预测的成本。每天 10 次预测时哪个最便宜？10,000 次时呢？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Custom silicon | “非 GPU 芯片” | Groq LPU、Cerebras WSE、SambaNova RDU——为 decode 优化 |
| FireAttention | “Fireworks 引擎” | 自研 attention kernel；宣称延迟比 vLLM 低 4 倍 |
| Truss | “Baseten 的格式” | 模型打包 manifest；依赖 + 密钥 + serving 配置 |
| Per-token | “API 定价” | 按消耗的 token 收费；不为空闲付费 |
| Per-minute | “专属定价” | 按 GPU 墙钟时间收费；高利用率时胜出 |
| Per-prediction | “Replicate 定价” | 按每次模型调用收费；图像/视频常见 |
| RayTurbo | “Anyscale 引擎” | Ray 上的专有推理；在 Ray 集群上与 vLLM 竞争 |
| Batch tier | “打五折” | 以更低费率服务的非交互队列；Fireworks、OpenAI 常见 |
| Fine-tuned at base rate | “Fireworks LoRA” | 对以 LoRA 服务的请求按基座模型费率收费（差异点） |

## Further Reading

- [Fireworks Pricing](https://fireworks.ai/pricing) —— 按 token 费率、batch 档、GPU 租赁。
- [Baseten Pricing](https://www.baseten.co/pricing/) —— 按分钟费率、承诺容量、企业档。
- [Modal Pricing](https://modal.com/pricing) —— 按秒 GPU 费率和免费额度。
- [Together AI Pricing](https://www.together.ai/pricing) —— 模型目录与按 token 费率。
- [Anyscale Pricing](https://www.anyscale.com/pricing) —— RayTurbo 与托管 Ray 定价。
- [Northflank — Fireworks AI Alternatives](https://northflank.com/blog/7-best-fireworks-ai-alternatives-for-inference) —— 对比评估。
- [Infrabase — AI Inference API Providers 2026](https://infrabase.ai/blog/ai-inference-api-providers-compared) —— 厂商全景。
