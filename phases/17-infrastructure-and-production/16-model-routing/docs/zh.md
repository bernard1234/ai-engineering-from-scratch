# Model Routing 作为降本的 primitive

> 一个动态 broker 评估每个请求（任务类型、token 长度、embedding 相似度、置信度），把简单查询发给便宜模型，把复杂查询升级到 frontier 模型。这也叫 model cascading。生产案例研究显示，在美国/英国/欧盟的部署中，iso-quality 下可降低 20-60% 成本；在高流量 SaaS 上，路由效率提升 30% 就能转化为六位数的年度节省。2026 年的背景是 LLM 推理价格每年下降约 10 倍——从 2022 年末到 2026 年，一个 GPT-4 级 token 从 $20/M 降到约 $0.40/M。大部分降幅来自更好的 serving 栈（第 17 阶段 · 04-09），而非硬件。路由就是把这份降价转化为利润、又不让产品退化的方式。失败模式是便宜模型漂移：路由把 40% 推给更弱的模型，推理任务上质量下降 3-5%，一个季度都没人察觉。用在线质量指标来把守路由，而不只是离线 eval 集。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级级联路由模拟器)
**Prerequisites:** 第 17 阶段，第 01 课（Managed LLM Platforms），第 19 课（AI Gateways）
**Time:** ~60 分钟

## Learning Objectives

- 解释 model cascading：便宜优先 + 置信度检查，置信度低时升级。
- 列举四个路由信号（任务分类、prompt 长度、与已知困难集的 embedding 相似度、首轮的自我置信度）。
- 在目标路由切分与质量损失容忍度下，计算预期混合成本。
- 指出能捕捉便宜模型蠕变的漂移监控指标（在线质量闸门）。

## 问题场景

你的服务在 GPT-5 上每月花 $80k。分析显示 70% 的查询很简单：“巴黎现在几点？”“改写这句话。”Haiku 级模型能以 3% 的成本完美处理这些。30% 需要 GPT-5 的推理——编码、数学、多步规划。

如果你把 70% 路由到便宜模型、30% 路由到昂贵模型，账单在产品质量不变的情况下下降约 65%。这就是路由。诀窍在于构建这个 broker 又不让质量退化。

## 核心概念

### 四个路由信号

1. **任务分类**：simple/complex/codegen/math/chat。可以是基于规则的分类器、一个小 LLM（Haiku 级，$0.25/M），或与标注桶的 embedding 相似度。输出：route = cheap / balanced / frontier。

2. **prompt 长度**：>4K tokens 的 prompt 往往需要 frontier 来保持连贯性。<500 tokens 的 prompt 通常不需要。

3. **与已知困难集的 embedding 相似度**：如果查询与某个已知困难桶很接近（余弦 > 0.88），直接升级到 frontier。

4. **首轮的自我置信度**：发给便宜模型；如果模型的 log-probs 显示低置信度、或它拒绝、或输出模棱两可的话术，就在 frontier 上重试。这会为约 10% 的流量增加 P95 latency，却能在另外 90% 上省下 50%+。

### 三种模式

**Pre-route**（前置分类器）：增加约 5-10ms latency；总体最快。

**Cascade**（便宜优先，低置信度升级）：中位 latency 约 1.2 倍（便宜运行 + 验证），升级的请求约 2 倍。质量下限最好。

**Ensemble route**（对样本并行跑便宜与 frontier，由 reward model 挑选）：质量最高、成本最高；只用于关键的 A/B。

### 实现

AI 网关（第 17 阶段 · 19）暴露路由能力。LiteLLM 有带 fallback 与 cost-routing 的 `router` 配置。Portkey 有 guards + routing。Kong AI Gateway 有基于插件的路由。OpenRouter 的模型市场暴露推荐 API。

开源：RouteLLM（LMSYS）、Not Diamond（商业）、Prompt Mule。

### 2026 的价格曲线

| 模型档位 | 2022 年末 | 2026 | 变化 |
|-------------|-----------|------|--------|
| GPT-4 级质量 | ~$20/M | ~$0.40/M | 便宜 50 倍 |
| Frontier（GPT-5、Claude 4） | — | ~$3-10/M | 新档位 |

大部分改进来自 serving 效率——第 17 阶段 · 04-09 的核心课程转化成了 provider 侧的成本下降。路由让你在应用层捕获这些收益，而不必等所有用户都迁移到便宜档。

### 漂移才是真正的风险

你的路由把 40% 发给便宜模型。六个月里，任务分布发生偏移（用户变得更老练，问题问得更长）。router 没察觉，因为它的分类器是在第一季度数据上训练的。质量悄悄下降。没人抱怨得足够大声。你是在一场输掉的竞品 benchmark 里才发现的。

用在线质量指标来把守路由：

- 每条路由的用户点赞/点踩。
- 每条路由在留出样本（5%）上的自动 LLM-judge。
- 升级率：如果 cascade 触发上行路由 >30%，说明便宜模型被过度使用。
- 每条路由的 refusal rate。

### 你该记住的数字

- 2026 年 iso-quality 下的路由节省：案例研究为 20-60%。
- 2022-2026 年 LLM 降价：总体每年约 10 倍。
- GPT-4 级 2022 vs 2026：~$20/M → ~$0.40/M。
- Cascade 的 latency 影响：中位约 1.2 倍，升级请求约 2 倍（约 10% 的流量）。

```figure
model-cascade-router
```

## Use It

`code/main.py` 在混合负载上模拟 pre-route、cascade 与 ensemble。报告混合成本、质量损失与升级率。

## Ship It

本课产出 `outputs/skill-router-plan.md`。给定负载与质量预算，挑选路由模式与信号。

## Exercises

1. 运行 `code/main.py`。在什么准确率下限上，cascade 会胜过 pre-route？
2. 你的用户群是 30% 企业（复杂查询）、70% 免费档（简单）。设计路由切分。用什么在线指标把守？
3. 一条路由让质量下降 2%，却省下 40%。这能上线吗？取决于产品——两面都论证。
4. 使用 OpenAI / Anthropic API 的 logprobs 实现一个置信度检查。你从什么阈值起步？
5. 六个月里，升级率从 8% 攀升到 22%。诊断三个原因以及各自的修复。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Model routing | “成本 broker” | 按请求动态选择模型 |
| Model cascade | “便宜优先升级” | 先跑便宜模型，低置信度时落到 frontier |
| Pre-route | “先分类” | 前置分类器；不重跑 |
| Ensemble route | “并行挑选” | 跑多个，由 reward model 挑最好 |
| Escalation rate | “上行路由 %” | cascade 请求中升级的占比 |
| RouteLLM | “LMSYS 路由器” | OSS 路由库 |
| Not Diamond | “商业路由器” | SaaS 模型路由产品 |
| Drift | “便宜模型蠕变” | 分布偏移而 router 未察觉 |
| Online quality gate | “实时检查” | 自动 LLM-judge 采样实时流量 |

## Further Reading

- [AbhyashSuchi — Model Routing LLM 2026 Best Practices](https://web.archive.org/web/20260413143335/https://abhyashsuchi.in/model-routing-llm-2026-best-practices/)
- [Lukas Brunner — Rise of Inference Optimization 2026](https://dev.to/lukas_brunner/the-rise-of-inference-optimization-the-real-llm-infra-trend-shaping-2026-4e4o)
- [RouteLLM paper / code](https://github.com/lm-sys/RouteLLM)
- [Not Diamond — model routing](https://www.notdiamond.ai/)
- [OpenRouter](https://openrouter.ai/) ——具备路由基础能力的多模型网关。
