# 公平性准则 — 群体、个体、反事实

> 三大类准则构成了公平性文献的结构。群体公平：demographic parity、equalized odds、conditional use accuracy equality——受保护群体之间平均比率相等。个体公平（Dwork et al. 2012）：相似的个体得到相似的决策；决策映射上的 Lipschitz 条件。反事实公平（Kusner et al. 2017）：如果当敏感属性被反事实地改变时决策不变，则该决策对个体是公平的。2024 年理论结果（NeurIPS 2024）：CF 与准确率之间存在内在权衡；一种模型无关方法可以把最优但不公平的预测器转换为 CF 预测器，准确率损失有界。回溯反事实（backtracking counterfactuals，arXiv:2401.13935，2024 年 1 月）：新范式，避免要求对法律受保护属性做干预。哲学调和（ICLR Blogposts 2024）：在给定因果图的条件下，满足某些群体公平度量蕴含反事实公平。

**Type:** Learn
**Languages:** Python (stdlib, 三准则比较)
**Prerequisites:** 第 18 阶段，第 20 课（bias），第 02 阶段（classical ML）
**Time:** ~60 分钟

## Learning Objectives

- 陈述三种群体公平准则（demographic parity、equalized odds、conditional use accuracy equality）以及一个不可能性结果。
- 描述 Dwork et al. 2012 Lipschitz 表述下的个体公平。
- 描述反事实公平及其对因果图的依赖。
- 解释回溯反事实，以及它们为何绕开了“对受保护属性做干预”的问题。

## 问题场景

第 20 课讲的是测量 bias。第 21 课讲的是定义测量所服务的公平标准。三大类准则给出了结构上不同的标准——一个模型可以群体公平而个体不公平，可以反事实公平而群体不公平。选择标准是政策决策；没有哪个标准是普遍最优的。

## 核心概念

### 群体公平

- **Demographic parity。** P(Y=1 | A=a) = P(Y=1 | A=a') 对所有群体成立。接受率相等。
- **Equalized odds。** P(Y=1 | Y*=y, A=a) = P(Y=1 | Y*=y, A=a')。各群体间的 TPR 与 FPR 相等。
- **Conditional use accuracy equality。** P(Y*=y | Y=y, A=a) = P(Y*=y | Y=y, A=a')。各群体间的预测值相等。

不可能性（Chouldechova、Kleinberg-Mullainathan-Raghavan 2017）：在基率不等时，这三者无法同时满足。

### 个体公平

Dwork et al. 2012。若存在某个 Lipschitz 常数 L，使得 |f(x) - f(x')| <= L * d(x, x')，则决策映射 f 相对于任务特定的相似度度量 d 是个体公平的。相似的个体得到相似的决策。

需要定义 d。这是政策问题，不是统计问题。

### 反事实公平

Kusner et al. 2017。在总体的因果模型下，如果改变个体 i 的敏感属性的反事实值时决策不变，则该决策对 i 是反事实公平的。

需要因果 DAG。DAG 是一种建模选择。反事实公平的合理性只与 DAG 的合理性相当。

### CF 与准确率之间的权衡

NeurIPS 2024 理论：反事实公平与预测准确率之间存在内在权衡。一种模型无关方法可以把最优但不公平的预测器转换为 CF 预测器，准确率代价有界。准确率代价取决于最优不公平预测器中敏感属性系数的量级。

### 回溯反事实

arXiv:2401.13935（2024 年 1 月）。传统反事实要求对敏感属性做干预——“如果这个人是另一种性别，决策会改变吗”。在法律上这有问题：分类法律不允许对受保护属性做干预。

回溯反事实把方向翻转过来：不干预属性，而是问个体的实际特征取哪种组合本会产生反事实结果。这绕开了法律异议。

### 哲学调和

ICLR Blogposts 2024。在掌握因果图的情况下，满足某些群体公平度量蕴含反事实公平。三大类准则并非彼此正交；它们是同一底层因果结构的不同侧面。

这并不能消解不可能性定理（基率不等仍然阻止同时满足群体公平）。但它表明，“群体”与“个体 / 反事实”之间表面上的对立，部分是不明确因果模型造成的假象。

### 本课在 Phase 18 中的位置

第 20 课是 bias 测量。第 21 课是公平性定义。第 22 课是隐私（differential privacy）。第 23 课是水印。这些是与分配相邻的课程，与第 7 至 11 课那批与欺骗相邻的课程互为补充。

```figure
an-fairness-trilemma
```

## Use It

`code/main.py` 构建一个带敏感属性和不等基率的玩具级二分类数据集。在一个简单分类器上计算 demographic parity、equalized odds 与 conditional use accuracy equality。观察三个指标互相矛盾。施加一个面向 demographic parity 的重加权，并观察它在另外两个指标上的代价。

## Ship It

本课产出 `outputs/skill-fairness-criterion.md`。给定一个公平性主张或政策，识别它声称的是哪条准则、在所声称的不等基率下模型能否满足其余准则，以及该主张依赖什么因果 DAG。

## Exercises

1. 运行 `code/main.py`。在默认数据上报告三个群体指标。施加面向 demographic parity 的重加权并重新报告。

2. 在非敏感特征上用 L2 实现 Dwork et al. 2012 的个体公平度量。报告有多少对在常数 L=1 下违反 Lipschitz。

3. 阅读 Kusner et al. 2017。为简历打分构造一个简单的双特征因果 DAG，并识别它所蕴含的反事实公平条件。

4. 2024 年的回溯反事实论文避免对受保护属性做干预。描述一个这对法律合规很重要的场景。

5. ICLR 2024 的调和论证认为群体公平与反事实公平是同一结构的不同侧面。从 `code/main.py` 的三条准则中挑两条，陈述能让它们等价所需的因果假设。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Demographic parity | “比率相等” | P(Y=1 | A=a) 在各组间相等 |
| Equalized odds | “TPR/FPR 相等” | 各群体间的真阳性率与假阳性率相等 |
| Conditional use accuracy | “PPV/NPV 相等” | 各群体间的预测值相等 |
| Individual fairness | “Lipschitz 条件” | 相似的个体得到相似的决策 |
| Counterfactual fairness | “因果改变不变性” | 反事实地改变属性时决策不变 |
| Backtracking counterfactual | “通过实际情况解释” | 反事实从结果反向推理，而不是从属性正向推理 |
| Impossibility theorem | “三者冲突” | Chouldechova / KMR 2017：基率不等时群体准则互斥 |

## Further Reading

- [Dwork et al. — Fairness through Awareness（arXiv:1104.3913）](https://arxiv.org/abs/1104.3913) —— 个体公平
- [Kusner, Loftus, Russell, Silva — Counterfactual Fairness（arXiv:1703.06856）](https://arxiv.org/abs/1703.06856) —— 反事实公平
- [Chouldechova — Fair prediction with disparate impact（arXiv:1703.00056）](https://arxiv.org/abs/1703.00056) —— 不可能性
- [Backtracking Counterfactuals（arXiv:2401.13935）](https://arxiv.org/abs/2401.13935) —— 面向受保护属性干预的新范式
