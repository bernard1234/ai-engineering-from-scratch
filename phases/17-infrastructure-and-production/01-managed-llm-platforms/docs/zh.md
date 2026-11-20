# 托管 LLM 平台 — Bedrock、Vertex AI、Azure OpenAI

> 三家超大规模云厂商，三种截然不同的策略。AWS Bedrock 是模型市场——Claude、Llama、Titan、Stability、Cohere 统一在一个 API 之后。Azure OpenAI 是与 OpenAI 的独家合作，外加用于专属容量的 Provisioned Throughput Units（PTU）。Vertex AI 以 Gemini 为先，拥有最好的长 context 与多模态能力。2026 年 Artificial Analysis 测得 Azure OpenAI 中位数约 50 ms、Bedrock 在 Llama 3.1 405B 同等部署上约 75 ms——PTU 解释了这个差距，因为专属容量胜过共享 on-demand。决策规则不是“哪个最快”，而是“哪个模型目录和 FinOps 面匹配我的产品”。本课教你带着写下来的权衡去选，而不是靠感觉。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级成本与延迟比较器)
**Prerequisites:** 第 11 阶段（LLM Engineering），第 13 阶段（Tools and Protocols）
**Time:** ~60 分钟

## Learning Objectives

- 说出三种平台策略（市场型、独家型、Gemini 优先型），并各自匹配一个产品用例。
- 解释 Provisioned Throughput Units（PTU）在 Azure OpenAI 中为你买到了什么，以及为什么 on-demand Bedrock 在 405B 规模下通常读数慢约 25 ms。
- 画出每个平台的 FinOps 归因面（Bedrock Application Inference Profiles、Vertex 按团队分项目、Azure 作用域加 PTU 预留）。
- 写下“双供应商最低要求”策略，并解释为什么单一厂商锁定是 2026 年代价高昂的错误。

## 问题场景

你为产品选了 Claude 3.7 Sonnet。现在你需要把它服务起来。你可以直接调用 Anthropic API，也可以经由 AWS Bedrock 调用，或者走 gateway。直连 API 最简单；Bedrock 增加 BAA、VPC endpoint、IAM 和 CloudWatch 归因。gateway 则增加 failover、统一账单，以及跨供应商的 rate limit。

更深的问题是模型目录。如果同一个产品里你需要 Claude、Llama 和 Gemini，你无法从同一个地方把它们全部买齐——除非那个地方同时是 Bedrock 加 Vertex 加 Azure OpenAI。超大规模云厂商不可互换，它们各自对“谁拥有模型层”下了不同的注。

本课梳理这三种押注、延迟差距、FinOps 差距以及锁定风险。

## 核心概念

### 三种策略

**AWS Bedrock** —— 市场型。Claude（Anthropic）、Llama（Meta）、Titan（AWS 一方模型）、Stability（图像）、Cohere（embedding）、Mistral，外加图像与 embedding 子目录。一个 API、一个 IAM 面、一个 CloudWatch 导出。Bedrock 的押注是：客户想要的是可选择性，而不是单一模型。

**Azure OpenAI** —— 独家合作。你可以在 Azure 数据中心里使用 GPT-4 / 4o / 5 / o-series、DALL·E、Whisper，以及对 OpenAI 模型做 fine-tuning。“Azure OpenAI Service”目录里没有任何非 OpenAI 模型——那些走 Azure AI Foundry（独立产品）。Azure 的押注是：OpenAI 仍是前沿，而客户想在这个特定关系上拥有企业级管控。

**Vertex AI** —— Gemini 优先，其他一切居次。Gemini 1.5 / 2.0 / 2.5 Flash 与 Pro，外加 Model Garden（第三方）。Vertex 的押注是多模态长上下文——1M token 的 Gemini context 就是差异点。

### 规模化下的延迟差距

Artificial Analysis 运行持续 benchmark。在等效的 Llama 3.1 405B 部署（共享 on-demand）上，Azure OpenAI 首 token 延迟中位数约为 50 ms；Bedrock 约为 75 ms。这个差距并不是 AWS 的失败——而是容量模型的差异。Azure 出售 PTU（Provisioned Throughput Units），为你的租户预留 GPU 容量。Bedrock 的对等物（Provisioned Throughput）确实存在，但每个单元起步约 $21/小时，大多数客户仍用共享 on-demand。

on-demand 共享容量要与其他所有客户的流量竞争，专属容量则不用。如果你的产品 SLA 是 P99 下 TTFT < 100 ms，那么要么在 Azure 买 PTU，要么买 Bedrock Provisioned Throughput，要么接受默认的波动。

### Provisioned Throughput 的经济学

Azure PTU：一块预留的推理算力。对可预测的负载，相对 on-demand 最多节省约 70%。无论流量多少都按小时固定计费——即使空闲你也要为预留付费。盈亏平衡点通常在 40-60% 的持续利用率附近。

Bedrock Provisioned Throughput：按模型和区域不同，每小时 $21-$50。算法类似——盈亏平衡点约在半峰值利用率。需要按月承诺。

Vertex 的预留容量按 Gemini SKU 出售；价格随模型和区域变化，且较少公开宣传。

### FinOps 面——真正的差异点

**Bedrock Application Inference Profiles** 是市场型平台里最干净的归因方式。给 profile 打上 `team`、`product`、`feature` 标签；让所有模型调用都经由它路由；CloudWatch 就能直接按 profile 拆分成本，无需后处理。2025 年推出，仍是超大规模云厂商原生方案中粒度最细的。

**Vertex** 的归因是“每团队一个 project”加“处处打 label”。你把每个团队建模为一个 GCP project，给每个资源都打 label，再用 BigQuery Billing Export + DataStudio 做汇总。工作量更大，但 BigQuery 让你能对成本数据跑任意 SQL。

**Azure** 依赖 subscription/resource-group 作用域加 tag，并把 PTU 预留作为一等成本对象。tag 是从 resource group 继承的，而非按请求继承，因此按请求归因需要 Application Insights 自定义指标，或一个会打标 header 的 gateway。

规律是：Bedrock 原生最干净，Vertex 借助 BigQuery 最灵活，Azure 除非你做埋点否则最不透明。

### 锁定是 2026 年的风险

当某一个模型独大时，绑定单一超大规模云厂商还说得过去。到了 2026 年，前沿每月都在移动——这个季度是 Claude 3.7，下个季度是 Gemini 2.5，再下个季度是 GPT-5。锁定一个平台，就把你挡在前沿的三分之二之外。

奏效的团队采用的模式是：任何产品关键的 LLM 调用都设双供应商下限。Bedrock 加 Azure OpenAI 是常见组合——Claude 来自一个、GPT 来自另一个，二者之间 failover，共用同一个 gateway。成本上升可忽略，因为 gateway 会择优选路；而故障期间（比如 2025 年 1 月的 Azure OpenAI 事件、AWS us-east-1 中断）可用性的提升则是决定性的。

### 数据驻留、BAA 与受监管行业

Bedrock：大多数区域提供 BAA；VPC endpoint；guardrail。金融科技常见默认。
Azure OpenAI：HIPAA、SOC 2、ISO 27001；EU 数据驻留；受监管企业的默认选择。
Vertex：HIPAA、GDPR、按区域的数据驻留；Google Cloud 的合规栈。

三者都满足基本勾选项。差异在于数据保留策略、日志如何处理，以及 abuse monitoring 是否会读取你的流量（多数默认 opt-in；企业版可 opt-out）。

### 你应该记住的数字

- Azure OpenAI 在 Llama 3.1 405B 等效部署上的 TTFT 中位数：~50 ms（启用 PTU）。
- Bedrock on-demand 的 TTFT 中位数：~75 ms。
- Bedrock Provisioned Throughput：每单元 $21-$50/小时。
- Azure PTU 盈亏平衡：约 40-60% 持续利用率。
- 高利用率下 PTU 相对 on-demand 的节省：最高 70%。

```figure
i4-platform-lanes
```

## Use It

`code/main.py` 在合成负载上比较三个平台——建模 on-demand 与 PTU 的经济学、TTFT 方差，以及成本归因保真度。运行它，看看 PTU 在哪里划算，以及市场型的模型广度在哪里压过 TTFT 差距。

## Ship It

本课产出 `outputs/skill-managed-platform-picker.md`。给定负载画像（所需模型、TTFT SLA、每日量、合规要求），它会推荐一个主平台、一个后备平台，以及一份 FinOps 埋点计划。

## Exercises

1. 运行 `code/main.py`。对一个 70B 级模型，Azure PTU 在什么持续利用率下胜过 on-demand？算出盈亏平衡点，并与宣传的 40-60% 区间比较。
2. 你的产品需要 Claude 3.7 Sonnet 和 GPT-4o。设计一个双供应商部署——哪个放到哪个超大规模云厂商、前面挂什么 gateway、failover 策略是什么？
3. 一家受监管的医疗客户要求 BAA、US-East 数据驻留，以及 P99 下低于 100 ms 的 TTFT。选一个平台，并用三个具体特性来论证。
4. 你发现本月 Bedrock 账单涨了 4 倍，但流量没变。没有 Application Inference Profiles 时，你如何找出元凶？有 profile 时，需要多久？
5. 阅读 Azure OpenAI 和 Bedrock 的定价页。对每月 100M token 的 Claude 负载，哪个更便宜——直连 Anthropic API、Bedrock on-demand，还是 Bedrock Provisioned Throughput？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Bedrock | “AWS 的 LLM 服务” | 覆盖 Claude、Llama、Titan、Mistral、Cohere 的模型市场 |
| Azure OpenAI | “Azure 的 ChatGPT” | Azure 数据中心里带企业管控的独家 OpenAI 模型 |
| Vertex AI | “Google 的 LLM” | 以 Gemini 为先、并用 Model Garden 承载第三方模型的平台 |
| PTU | “专属容量” | Provisioned Throughput Unit——按小时计价的预留推理 GPU |
| Application Inference Profile | “Bedrock 打 tag” | 按产品划分、带 tag 的成本/用量 profile，CloudWatch 原生 |
| Model Garden | “Vertex 目录” | Vertex AI 的第三方模型区，与 Gemini 分开 |
| Two-provider minimum | “LLM 冗余” | 让每条关键 LLM 路径跨 ≥2 家超大规模云厂商运行的策略 |
| BAA | “HIPAA 文书” | Business Associate Agreement；处理 PHI 所必需；三家都提供 |
| Abuse monitoring | “日志监视器” | 供应商侧对 prompt/输出做安全扫描；企业版可 opt-out |

## Further Reading

- [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/) —— 权威价目表和 Provisioned Throughput 定价。
- [Azure OpenAI Service Pricing](https://azure.microsoft.com/en-us/pricing/details/azure-openai/) —— PTU 经济学与价目表。
- [Vertex AI Generative AI Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing) —— Gemini 各档位与 Model Garden 附加费。
- [Artificial Analysis LLM Leaderboard](https://artificialanalysis.ai/) —— 跨供应商的持续延迟与吞吐 benchmark。
- [The AI Journal — AWS Bedrock vs Azure OpenAI CTO Guide 2026](https://theaijournal.co/2026/03/aws-bedrock-vs-azure-openai/) —— 企业决策框架。
- [Finout — Bedrock vs Vertex vs Azure FinOps](https://www.finout.io/blog/bedrock-vs.-vertex-vs.-azure-cognitive-a-finops-comparison-for-ai-spend) —— 并排对比的归因机制。
