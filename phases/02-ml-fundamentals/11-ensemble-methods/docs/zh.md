# 集成方法

> 一堆弱学习者，组合方式对了，就变成一个强学习者。这不是比喻，是定理。

**Type:** Build
**Language:** Python
**Prerequisites:** Phase 2, Lesson 10 (偏差-方差权衡)
**Time:** ~120 minutes

## Learning Objectives

- 从零实现 AdaBoost 和梯度提升，并解释 Boosting 怎么顺序降低偏差
- 构建 Bagging 集成，演示平均不相关模型怎么降方差而不增偏差
- 对比 Bagging、Boosting 和 Stacking 各自针对哪个误差成分
- 评估集成多样性，解释为什么多数投票准确率随更多独立弱学习者而提高

## 问题场景

单棵决策树训练快、好理解，但会过拟合。单个线性模型在复杂边界上欠拟合。你可以花几天调架构。或者你可以一堆不理想的模型组合起来，得到比它们中任何一个都好的东西。

集成方法就是做这件事的。它们是 Kaggle 表格数据竞赛里最靠谱的 technique，支撑着大部分生产 ML 系统，还把偏差-方差权衡活灵活现地演示给你看。Bagging 降方差。Boosting 降偏差。Stacking 学习在哪些输入上信任哪些模型。

## 核心概念

### 为什么集成能工作

假设你有 N 个独立分类器，每个准确率 p > 0.5。多数投票的准确率是：

```
P(多数正确) = Σ_{k > N/2} C(N,k) * p^k * (1-p)^(N-k)
```

21 个分类器每个 60% 准确率时，多数投票准确率约 74%。101 个时升到 84%。模型犯的错不一样，就能互相抵消。

关键要求是**多样性**。如果所有模型犯同样的错，组合起来什么帮助都没有。集成有效是因为它们通过以下方式产生多样化模型：

- 不同训练子集（Bagging）
- 不同特征子集（随机森林）
- 顺序纠错（Boosting）
- 不同模型家族（Stacking）

### Bagging（Bootstrap Aggregating）

Bagging 通过在训练数据的不同 bootstrap 样本上训练每个模型来创造多样性。

（mermaid 图保留）

Bootstrap 样本是从原始数据里有放回抽取的，大小和原始一样。约 63.2% 的唯一样本出现在每个 bootstrap 里。剩下的 36.8%（out-of-bag 样本）免费提供了一个验证集。

Bagging 降方差而偏差几乎不变。每棵树在自己的 bootstrap 样本上过拟合，但每棵树的过拟合方式不同，所以平均之后噪声就抵消了。

**随机森林**是 Bagging 加了个额外花活：每次分裂只考虑随机子集的特征。这强制树之间更多样化。典型候选特征数：分类问题 `sqrt(n_features)`，回归问题 `n_features / 3`。

### Boosting（顺序纠错）

Boosting 顺序训练模型。每个新模型聚焦于前面模型做错的样本。

（mermaid 图保留）

Boosting 降偏差。每个新模型修正当前集成的系统性错误。最终预测是所有模型的加权和，表现好的模型权重更高。

权衡：Boosting 如果跑太多轮会过拟合，因为它不停去拟合更难的例子，其中一些可能就是噪声。

### AdaBoost

AdaBoost（Adaptive Boosting）是第一个实用的 Boosting 算法。它和任何基学习者配合都能工作，典型就是决策树桩（深度 1 的树）。

算法：

```
1. 初始化样本权重：w_i = 1/N 对所有 i

2. 对 t = 1 到 T：
   a. 在加权数据上训练弱学习者 h_t
   b. 计算加权误差：
      err_t = Σ(w_i · I(h_t(x_i) ≠ y_i)) / Σ(w_i)
   c. 计算模型权重：
      alpha_t = 0.5 · ln((1 - err_t) / err_t)
   d. 更新样本权重：
      w_i = w_i · exp(-alpha_t · y_i · h_t(x_i))
   e. 归一化权重让总和为 1

3. 最终预测：H(x) = sign(Σ alpha_t · h_t(x))
```

误差低的模型拿更高 alpha。分类错的样本拿更高权重，让下一个模型聚焦于它们。

### 梯度提升

梯度提升把 Boosting 推广到任意损失函数。它不是重新加权样本，而是让每个新模型拟合当前集成的残差（损失的负梯度）。

```
1. 初始化：F_0(x) = argmin_c Σ(L(y_i, c))

2. 对 t = 1 到 T：
   a. 计算伪残差：
      r_i = -dL(y_i, F_{t-1}(x_i)) / dF_{t-1}(x_i)
   b. 拟合一棵树 h_t 到残差 r_i
   c. 找最优步长：
      γ_t = argmin_γ Σ(L(y_i, F_{t-1}(x_i) + γ · h_t(x_i)))
   d. 更新：
      F_t(x) = F_{t-1}(x) + learning_rate · γ_t · h_t(x)

3. 最终预测：F_T(x)
```

对平方误差损失，伪残差就是实际残差：`r_i = y_i - F_{t-1}(x_i)`。每棵树字面上在拟合前面集成的错误。

学习率（shrinkage）控制每棵树贡献多少。更小的学习率需要更多树但泛化更好。典型值：0.01 到 0.3。

### XGBoost：为什么它统治表格数据

XGBoost（eXtreme Gradient Boosting）是梯度提升加工程优化，让它快、准、抗过拟合：

- **正则化目标**：叶权重上加 L1 和 L2 惩罚，防止单棵树太自信
- **二阶近似**：同时用一阶和二阶导数做分裂决策
- **稀疏感知分裂**：在每个分裂点为缺失数据学习最佳方向，原生处理缺失值
- **列采样**：像随机森林一样，每次分裂采样特征增加多样性
- **加权分位数草图**：在分布式数据上高效找连续特征的分裂点
- **缓存感知块结构**：内存布局按 CPU 缓存行优化

对表格数据，XGBoost（和它的后继 LightGBM）始终胜过后辈神经网络。这暂时不会变。如果你的数据能塞进行列的表格里，从梯度提升开始。

### Stacking（元学习）

Stacking 把多个基模型的预测当作元学习器的特征。

（mermaid 图保留）

元学习器学习在哪些输入上信任哪些基模型。如果随机森林在某些区域更好、SVM 在另一些更好，元学习器就学会相应路由。

为了避免数据泄露，基模型预测必须在训练集上通过交叉验证产生。你永远不要用同一数据训练基模型和生成元特征。

### Voting

最简单的集成。直接组合预测。

- **硬投票**：对类别标签多数投票。
- **软投票**：平均预测概率，选平均概率最高的那个类。通常更好，因为用到了置信度信息。

```figure
f3-ensemble-average
```

## Build It

`code/ensembles.py` 里的代码从零实现了一切。从决策树桩开始：

### 第 1 步：决策树桩（基学习者）

（Python 代码逐字保留）

### 第 2 步：从零 AdaBoost

（Python 代码逐字保留）

### 第 3 步：从零梯度提升

（Python 代码逐字保留）

### 第 4 步：和 sklearn 对比

代码验证了我们的从零实现和 sklearn 的 `AdaBoostClassifier` / `GradientBoostingClassifier` 产生相近的准确率，并把所有方法并排比较。

## Use It

### 什么时候用哪个方法

| 方法 | 降低什么 | 最适合 | 注意 |
|------|----------|--------|------|
| Bagging / 随机森林 | 方差 | 噪声数据、多特征 | 对偏差没帮助 |
| AdaBoost | 偏差 | 干净数据、简单基学习者 | 对异常值和噪声敏感 |
| 梯度提升 | 偏差 | 表格数据、竞赛 | 训练慢，不调容易过拟合 |
| XGBoost / LightGBM | 两者 | 生产表格 ML | 超参数多 |
| Stacking | 两者 | 要最后 1-2% 准确率 | 复杂，元学习器有过拟合风险 |
| Voting | 方差 | 快速组合多样化模型 | 只在模型多样时才有帮助 |

### 表格数据生产栈

对大多数表格预测问题，按这个顺序试：

1. **LightGBM 或 XGBoost**，用默认参数
2. 调 n_estimators、learning_rate、max_depth、min_child_weight
3. 如果要最后 0.5%，用 3-5 个多样化模型构建 Stacking 集成
4. 全程用交叉验证

尽管持续有研究尝试，表格数据上的神经网络几乎总是不如梯度提升。TabNet、NODE 等架构偶尔能接近但很少能赢过调好的 XGBoost。

## Ship It

本课产出 `outputs/prompt-ensemble-selector.md`——一个帮你为给定数据集选对集成方法的 prompt。描述你的数据（大小、特征类型、噪声水平、类别平衡）和要解决的问题，prompt 会带你走决策检查清单，推荐方法，建议起始超参数，警告常见错误。也产出 `outputs/skill-ensemble-builder.md` 带完整选择指南。

## Exercises

1. 修改 AdaBoost 实现，追踪每轮之后的训练准确率。画准确率 vs 估计器数量。什么时候收敛？
2. 在回归树上加随机特征子采样从零实现随机森林。用 `max_features=sqrt(n_features)` 训练 100 棵树然后平均预测。和单棵树对比方差缩减。
3. 在梯度提升实现里加早停：每轮之后追踪验证损失，如果连续 10 轮没改进就停。实际需要多少棵树？
4. 用三个基模型（逻辑回归、决策树、KNN）和一个逻辑回归元学习器构建 Stacking 集成。用 5 折交叉验证产生元特征。对比每个基模型单独表现。
5. 在同一数据集上用默认参数跑 XGBoost。对比它的准确率和你的从零梯度提升。计时。速度差多大？

## Key Terms

| 术语 | 人们常说 | 实际含义 |
|------|----------|----------|
| Bagging | "在随机子集上训练" | Bootstrap Aggregating：在 bootstrap 样本上训练模型，平均预测来降方差 |
| Boosting | "聚焦难例" | 顺序训练模型，每个修正当前集成的错误来降偏差 |
| AdaBoost | "重加权数据" | 通过样本权重更新做 Boosting；分错的点下次权重更高 |
| 梯度提升 | "拟合残差" | 通过让每个新模型拟合损失函数的负梯度来做 Boosting |
| XGBoost | "Kaggle 武器" | 加了正则化、二阶优化和系统级速度技巧的梯度提升 |
| Stacking | "模型上叠模型" | 用基模型的预测作为元学习器的输入特征 |
| 随机森林 | "很多随机化的树" | 在决策树上做 Bagging，每次分裂加随机特征子采样增加多样性 |
| 集成多样性 | "要犯不同的错" | 模型的错误必须不相关，集成才能比个体好 |
| Out-of-bag 误差 | "免费验证" | bootstrap 抽取里没被抽到的样本（约 36.8%）充当验证集，不用单独留出 |

## Further Reading

- [Schapire & Freund: Boosting: Foundations and Algorithms](https://mitpress.mit.edu/9780262526036/) — AdaBoost 创造者写的书
- [Friedman: Greedy Function Approximation: A Gradient Boosting Machine (2001)](https://doi.org/10.1214/aos/1013203451) — 梯度提升原论文
- [Chen & Guestrin: XGBoost (2016)](https://arxiv.org/abs/1603.02754) — XGBoost 论文
- [Wolpert: Stacked Generalization (1992)](https://www.sciencedirect.com/science/article/abs/pii/S0893608005800231) — Stacking 原论文
- [scikit-learn Ensemble Methods](https://scikit-learn.org/stable/modules/ensemble.html) — 实用参考
