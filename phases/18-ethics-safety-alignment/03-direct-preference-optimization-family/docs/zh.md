# Direct Preference Optimization 家族

> Rafailov et al.（2023）表明 RLHF 的最优解可以用偏好数据写成闭式，因此你可以跳过显式 reward model，直接优化 policy。这一洞见催生了一个家族——IPO、KTO、SimPO、ORPO、BPO——每个都在修复 DPO 的一种失效模式。2026 年，直接对齐算法在前沿后训练运行中的出货量超过 PPO。但第 02 课的 over-optimization 曲线依然适用：DAA 并没有逃离 Goodhart，它们只是把 Goodhart 咬人的位置挪了。

**Type:** Learn
**Languages:** Python (stdlib, 六变体偏好损失比较器)
**Prerequisites:** 第 18 阶段，第 01 课（InstructGPT）、第 02 课（Reward hacking），第 10 阶段，第 08 课（DPO basics）
**Time:** ~75 分钟

## Learning Objectives

- 从带 KL 的 RLHF 最优解推导 DPO 的闭式。
- 说出 IPO、KTO、SimPO、ORPO、BPO 各自修复 DPO 的哪种失效模式。
- 区分“隐式 reward 差距”与“偏好强度”，并解释 IPO 的恒等映射为什么重要。
- 解释为什么 Rafailov et al.（NeurIPS 2024）证明 DAA 在没有显式 RM 的情况下仍然会 over-optimize。

## 问题场景

RLHF 目标（第 01 课）：

```
max_pi E_{x,y~pi} [ r(x, y) ] - beta * KL(pi || pi_ref)
```

有一个已知的最优解：

```
pi*(y|x) = (1/Z(x)) * pi_ref(y|x) * exp(r(x, y) / beta)
```

因此 reward 由最优 policy 与参考 policy 的比值隐式定义：

```
r(x, y) = beta * log(pi*(y|x) / pi_ref(y|x)) + beta * log Z(x)
```

把它代入 Bradley-Terry 偏好似然，配分函数 `Z(x)` 会消掉，因为它只依赖 `x`。剩下的是一个仅关于 policy 参数的损失——不需要 reward model。这就是 DPO。

麻烦之处在于：推导假设最优解可达、偏好数据在分布内、且参考 policy 是真正的模式锚点。这些都不完全成立。家族的每个成员都在修复一个被违反的不同假设。

## 核心概念

### DPO（Rafailov et al., 2023）

```
L_DPO = -log sigmoid(
  beta * log(pi(y_w | x) / pi_ref(y_w | x))
  - beta * log(pi(y_l | x) / pi_ref(y_l | x))
)
```

可能出现的问题：

- 隐式 reward 差距 `beta * (log(pi/pi_ref)_w - log(pi/pi_ref)_l)` 是无界的。一个微小的偏好就能产生任意大的差距。
- 损失把被选与被拒的 log-prob 推向相反方向。只要被拒的那个下降得更快，它就可以把被选的绝对 log-prob 也压低。这就是 Degraded Chosen Response 现象。
- 分布外的偏好（稀有对 vs 稀有对）会产生任意的隐式 reward。

### IPO（Azar et al., 2024）

Identity Preference Optimization 用对偏好概率的恒等映射替代 log-sigmoid。损失变成有界目标上的平方误差：

```
L_IPO = (log(pi(y_w | x) / pi_ref(y_w | x)) - log(pi(y_l | x) / pi_ref(y_l | x)) - 1/(2 beta))^2
```

边际被 `1/(2 beta)` 限制。偏好强度与隐式 reward 差距成正比。不会爆炸。

### KTO（Ethayarajh et al., 2024）

Kahneman-Tversky Optimization 完全放弃成对结构。给定单个带标签的输出和“可取”或“不可取”的二元信号，它映射到前景理论效用：

```
v(x, y) = sigma(beta * log(pi(y|x) / pi_ref(y|x)) - z_ref)
```

收益和损失使用不同权重（损失厌恶）。好处：你可以使用非成对数据，而这类数据要丰富得多。

### SimPO（Meng et al., 2024）

Simple Preference Optimization 让训练信号与生成对齐。完全去掉参考 policy，并按长度归一化对数似然：

```
L_SimPO = -log sigmoid(
  (beta / |y_w|) * log pi(y_w | x)
  - (beta / |y_l|) * log pi(y_l | x)
  - gamma
)
```

并用边际 `gamma` 来稳定。长度归一化消除了利用 DPO 长度偏置失效模式的激励（更长的 `y_w` 按构造会带来更大的 log-prob 差距）。

### ORPO（Hong et al., 2024）

Odds-Ratio Preference Optimization 在标准 SFT 负对数似然上加入一个偏好项：

```
L_ORPO = L_NLL(y_w) + lambda * L_OR
L_OR = -log sigmoid(log(odds(y_w) / odds(y_l)))
```

不需要参考 policy——SFT 项就是正则项。从基座模型到对齐模型单阶段训练。不需要单独的 SFT checkpoint。

### BPO（ICLR 2026 submission, OpenReview id=b97EwMUWu7）

它指出了 Degraded Chosen Responses 问题：DPO 保持 `y_w > y_l` 的排序，但 `y_w` 的绝对 log-prob 可能下降。BPO 加入一行式修正，惩罚被选响应的下移。报告称在 Llama-3.1-8B-Instruct 的数学推理上相对 DPO 提升 +10.1% 准确率。

### 普适结果：DAA 仍然会 over-optimize

Rafailov et al. 的 "Scaling Laws for Reward Model Overoptimization in Direct Alignment Algorithms"（NeurIPS 2024）在多个数据集上跨 KL 预算用 DPO、IPO、SLiC 训练 policy。gold-reward-vs-KL 曲线具有与 Gao et al. 相同的先达峰后崩塌形状。隐式 reward 在训练期间查询分布外样本；KL 正则并不能稳定这一点。

DAA 没有逃离 Goodhart。它们把咬人的表面从“reward model 被过度优化”改变为“参考 policy 比值被过度优化”。普适的修复——更好的数据、集成、早停——对两者都适用。

### 如何选择（2026）

- 如果你有大量成对偏好数据：用保守 beta 的 DPO；如果长度偏置明显，用 SimPO。
- 如果你有非成对的二元反馈：KTO。
- 如果你想要从基座模型出发的单阶段流水线：ORPO。
- 如果你在 DPO 日志中看到被选 log-prob 下降：BPO。
- 如果偏好强度差异很大、DPO 正在饱和：IPO。

每家实验室都会在一套评测集上跑完这五个，再按任务挑赢家。没有理由认为数学推理和安全的最优解是同一个。

```figure
dpo-margin
```

## Use It

`code/main.py` 在一个玩具偏好数据集上比较六种损失（DPO、IPO、KTO、SimPO、ORPO、BPO），其中真实偏好强度因对而异。每种损失都针对同一份 500 对样本、用一个小的 softmax policy 优化。绘制每种方法的最终胜率、被选 log-prob 漂移和隐式 reward 离散度。

## Ship It

本课产出 `outputs/skill-preference-loss-selector.md`。给定数据集统计（成对 vs 非成对、偏好强度可变 vs 均匀、长度分布）和目标（单阶段或 SFT 后接偏好训练），推荐一种偏好损失并报告它所防范的失效模式。

## Exercises

1. 运行 `code/main.py`。报告 DPO 和 BPO 最终的 chosen-log-prob 下降量。BPO 应当保留更高的被选绝对概率——验证这一点。

2. 修改偏好数据，使所有对的强度都相等。六种方法中哪个最稳健？哪个会退化？解释 IPO 在此处的优势。

3. 让被拒响应平均比被选响应长 2 倍。在不改动其他任何东西的情况下，用数值展示 DPO 的长度利用以及 SimPO 的修复。

4. Rafailov et al.（NeurIPS 2024）声称 DAA 会 over-optimize。复现其单点版本：画出被选减被拒的 KL 散度，并在大 beta 下观察 DPO 的 over-optimization。

5. 阅读 BPO 论文摘要（OpenReview b97EwMUWu7）。写下 BPO 对 DPO 增加的一行式修正。对照 `code/main.py` 中的实现确认。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| DPO | "RLHF without a reward model" | 从闭式 RLHF 最优解导出的损失；只涉及 policy 参数 |
| Implicit reward | "the log-ratio" | `beta * log(pi(y\|x) / pi_ref(y\|x))` —— DPO 隐含的 reward |
| IPO | "bounded DPO" | 用恒等映射替换 log-sigmoid；隐式 reward 差距被 `1/(2 beta)` 封顶 |
| KTO | "unpaired DPO" | 在单标签上的前景理论效用，带损失厌恶 |
| SimPO | "reference-free DPO" | 长度归一化的对数似然 + 边际；没有参考 policy |
| ORPO | "one-stage DPO" | NLL + 几率比偏好项；从基座模型一次训练完成 |
| BPO | "chosen-preserving DPO" | DPO 加上对被选响应绝对 log-prob 下降的惩罚 |
| Degraded Chosen | "chosen goes down" | 只要被拒的下降更快，DPO 就会降低被选的 log-prob |
| DAA | "direct alignment algorithm" | 任何跳过显式 RM 的偏好损失方法 |

## Further Reading

- [Rafailov et al. — Direct Preference Optimization (NeurIPS 2023, arXiv:2305.18290)](https://arxiv.org/abs/2305.18290)
- [Azar et al. — A General Theoretical Paradigm to Understand Learning from Human Preferences (AISTATS 2024, arXiv:2310.12036)](https://arxiv.org/abs/2310.12036) —— IPO
- [Ethayarajh et al. — KTO: Model Alignment as Prospect Theoretic Optimization (arXiv:2402.01306)](https://arxiv.org/abs/2402.01306)
- [Meng, Xia, Chen — SimPO (NeurIPS 2024, arXiv:2405.14734)](https://arxiv.org/abs/2405.14734)
- [Hong, Lee, Thorne — ORPO (EMNLP 2024, arXiv:2403.07691)](https://arxiv.org/abs/2403.07691)
- [BPO — Behavior Preservation Optimization (ICLR 2026 OpenReview b97EwMUWu7)](https://openreview.net/forum?id=b97EwMUWu7)
- [Rafailov et al. — Scaling Laws for RM Overoptimization in DAAs (NeurIPS 2024, arXiv:2406.02900)](https://arxiv.org/abs/2406.02900)
