# Constitutional AI 与规则覆写

> Anthropic 于 2026 年 1 月 22 日发布的 Claude Constitution 共 79 页，采用 CC0 协议。它从基于规则的对齐转向基于推理的对齐，并确立了四层优先级体系：(1) 安全与支撑人类监督，(2) 伦理，(3) Anthropic 指南，(4) 有用性。行为被拆成两类：硬编码禁令（生物武器能力提升、CSAM），运营者和用户都不能覆写；以及软编码默认值，运营者可以在既定边界内调整。2022 年的原始版本（Bai 等）通过与 constitution 对照的自我批判和 RLAIF 来训练无害性。需要诚实说明的警示是：基于推理的对齐依赖模型把原则泛化到未曾预想的场景。Anthropic 自己在 2023 年的参与式实验显示，公众来源的原则与企业原则之间存在约 50% 的分歧；2026 版并未纳入那些发现。

**Type:** Learn
**Languages:** Python (stdlib, four-tier priority resolver)
**Prerequisites:** 第 15 阶段，第 06 课（Automated alignment research）、第 15 阶段，第 10 课（Permission modes）
**Time:** ~60 分钟

## 问题场景

一个已上线的 agent 会看到设计者从未见过的输入。没有哪份规则清单长到足以覆盖它们，也没有哪份规则清单短到能在算力压力下快速套用。实际问题在于：你如何让一个 agent 对齐到那样一套原则——它既能扛住长尾案例，又能在快速推理中生效？

基于规则的对齐（RBA）：把每一件不允许的事都列出来。检查快、易审计、无法保持最新，而且常常对它没预想到的近似变体过度拒绝。基于推理的对齐（2026 年的 Claude Constitution）：编码原则，让模型去推理。能泛化到未见案例，更难审计，失效模式是原则误用，而非漏掉某条规则。

2026 版 Constitution 明确采取了中间立场。硬编码禁令——那些对错不取决于上下文的做法（生物武器能力提升、CSAM）——属于 RBA：无论运营者或用户怎么指示，永远不做。其余一切都在四层体系内按推理处理：安全与支撑人类监督第一；伦理第二；Anthropic 声明的指南第三；有用性最后。运营者可以在软编码区调整默认值，但碰不到硬编码禁令。

## 核心概念

### 四层优先级体系

1. **安全与支撑人类监督。** 最高。模型优先不削弱人类与 Anthropic 监督和纠正 AI 的能力。这不是“保持谨慎”，而明确是“不要以让人类监督变得更困难的方式行事”。
2. **伦理。** 诚实，避免伤害他人，不欺骗，不操纵。当它与 Anthropic 的指南冲突时，伦理优先。
3. **Anthropic 指南。** Anthropic 认定重要的运营规范：产品范围、交互模式、何时用哪些工具。
4. **有用性。** 最低。在更高优先级允许的范围内尽可能有用。

当各层级冲突时，高者胜出。这与 Unix 优先级或网络 QoS 的形状相同——这套框架意在产生可预测的裁决，而不是在每个单独维度上都做到最优行为。

### 硬编码禁令 vs 软编码默认值

**硬编码：**
- 生物武器 / CBRN 能力提升
- CSAM
- 对关键基础设施的攻击
- 在被直接询问时欺骗用户有关模型身份的信息

运营者不能覆写这些。用户也不能覆写这些。凡能做到的地方，它们在模型权重层面执行（RLHF / Constitutional AI 训练）；做不到的地方，在推理层执行。

**软编码默认值（运营者可调）：**
- 回复长度默认值
- 话题范围（模型可以拒绝运营者部署范围之外的话题）
- 风格（正式 vs 随意）
- 工具使用模式

运营者的调整发生在声明过的边界之内。运营者不能通过改名来移除硬编码禁令。

### 2022 年的 CAI 训练

最初的 Constitutional AI（Bai 等，2022）这样训练无害性：

1. 针对一组 prompt 生成回复。
2. 让模型依据 constitution（明确的原则）逐条批判每个回复。
3. 基于批判修订回复。
4. 在修订后的配对上做 RLAIF（reinforcement learning from AI feedback）。

结果是：一个会用有原则的解释拒绝有害请求、而非一概拒绝的模型。2026 版 Constitution 用的是这套训练的后代，外加针对明确层级体系做的额外后训练。

### 基于推理的对齐抓得住什么、漏掉什么

**抓得住：**
- 由允许的原语组成、但原则明确适用的未预想组合。
- 与被禁事项高度接近的新请求。
- 依赖“你没说过 X 是被禁止的”这类说辞的社会工程攻击。

**漏掉：**
- 利用原则歧义的攻击（“用户要的是这个，所以有用性说可以”）。
- 两条原则以未预想的方式冲突、且层级顺序不明确的场景。
- 在训练循环中原则解释的缓慢漂移（重新诠释）。

### 2023 年的参与式实验

Anthropic 在 2023 年做过一个实验，比较一份企业内部撰写的 constitution 与一份由公众输入（约 1,000 名美国受访者）生成的 constitution。两个版本在约 50% 的原则上一致。在分歧之处，公众来源版本在某些议题上更严格（政治内容的处理），在另一些议题上更宽松（AI 身份的自我披露）。2026 版 Constitution 并未纳入公众来源的那些发现。这是该方法中一处有据可查的张力。

### 为什么必须有硬编码禁令

单靠基于推理的对齐关不上长尾。攻击者只要能让模型接受一个前提（例如“我们是持牌的生物武器研究实验室”），往往就能绕过那些依赖案例推理的原则。硬编码禁令不会因前提设定而弯折。它们就是第 14 课所说的“硬性宪法边界”在对齐层的体现。

### Constitution 在栈中的位置

Constitution 不是第 14 课的 kill switch。它位于模型层：模型的权重被训练成偏好什么。kill switch 和 canary token 位于运行时层：运行时允许什么。两者都需要。一个因为模型权重过于宽松而触发所有错误动作的运行时，是运行时的问题。一个因为运行时过度限制而拒绝所有正确动作的模型，也是运行时的问题。不同层覆盖不同的类别。

```figure
mx-priority-tiers
```

## Use It

`code/main.py` 实现了一个最小的四层优先级解析器。解析器接收一个拟议动作和一组原则评估（安全、伦理、指南、有用性），返回该动作、一次拒绝，或一个被修改过的动作。driver 跑一小组案例：明确允许、明确禁止、硬编码禁令、跨层的模糊案例。

## Ship It

`outputs/skill-constitution-review.md` 审计一次部署的 constitutional 层：什么是硬编码的、什么是软编码的、运营者可以在哪里调整，以及四层体系是否真的是裁决顺序。

## Exercises

1. 运行 `code/main.py`。确认即使有用性很高，硬编码禁令也会触发。修改解析器，把有用性置于伦理之上；观察失效模式。

2. 通读 Claude Constitution（公开，79 页，CC0）。找出一条你认为规格不足的原则。用两段话说明具体的歧义，并给出一个更严格的表述。

3. 为一个客服 agent 设计一套软编码默认值。运营者调整什么？运营者不能碰什么？为每一条边界给出理由。

4. 阅读 Bai 等 2022 年的 CAI 论文。描述一个案例，说明 Constitutional AI 的批判-修订回路会产生比一概规则更差的结果。指出它属于哪一类。

5. Anthropic 2023 年的参与式实验发现公众原则与企业原则之间有约 50% 的分歧。挑一个对生产部署有影响的类别（例如政治中立）。提出一种设计，让运营者能表达自己的价值观，同时硬编码禁令原封不动。

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|---|---|---|
| Constitutional AI | “Anthropic 的对齐方法” | 依据成文 constitution 做自我批判 + RLAIF |
| Reason-based alignment | “原则，而非规则” | 模型对原则进行推理，以处理未见案例 |
| Hardcoded prohibition | “永远不要做 X” | 基于规则的禁令，任何运营者或用户都无法覆写 |
| Soft-coded default | “运营者可调” | 在声明边界内的行为，由运营者控制 |
| Four-tier hierarchy | “优先级顺序” | 安全 > 伦理 > 指南 > 有用性 |
| RLAIF | “AI 反馈 RL” | 奖励来自模型生成的批判的 RL |
| Participatory constitution | “公众来源的原则” | 2023 年 Anthropic 实验；与企业版约 50% 分歧 |
| Principle drift | “解释漂移” | 模型对固定原则文本的解读随时间缓慢变化 |

## Further Reading

- [Anthropic — Claude's Constitution (January 2026)](https://www.anthropic.com/news/claudes-constitution) — 79 页的 CC0 文档。
- [Bai et al. — Constitutional AI: Harmlessness from AI Feedback](https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback) — 2022 年的原始论文。
- [Anthropic — Collective Constitutional AI (2023)](https://www.anthropic.com/research/collective-constitutional-ai-aligning-a-language-model-with-public-input) — 参与式实验。
- [Anthropic — Responsible Scaling Policy v3.0](https://anthropic.com/responsible-scaling-policy/rsp-v3-0) — Constitution 在 RSP 栈中的位置。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — Constitution 在长时程部署中的作用。
