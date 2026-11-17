# Imbalanced Learning

> 少数类是你真正关心的——但模型看不见它们。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 2 Lessons 3 (Logistic Regression), 9 (Model Evaluation)
**Time:** ~60 minutes

## Learning Objectives

- 识别类别不平衡问题（信用卡欺诈、癌症筛查）和 Accuracy 的误导性
- 从零实现 SMOTE 过采样算法
- 对比欠采样、过采样、class_weight 和代价敏感学习的效果
- 在不平衡数据集上用 PR 曲线和 AUC-PR 替代 Accuracy

## 核心概念

### 问题

不平衡数据中，Accuracy = 95% 可能是在永远预测多数类。少数类才是你真正关心的（欺诈、癌症、故障）。

### 策略

**class_weight="balanced"**：给少数类样本更高权重。最简单、最先试。

**欠采样多数类**：简单，但丢弃信息。

**过采样少数类**：复制或合成新样本。

**SMOTE**：合成少数类样本。在少数类点和它的 K 近邻之间线性插值：

```
x_new = x + rand(0,1) * (x_nearest_neighbor - x)
```

比随机过采样好——不只是复制，而是生成新的。

**代价敏感学习**：告诉模型少数类错误比多数类错误代价更高。

### 必须做的事

- 切分数据**之后**重采样（防泄露！）
- 分层交叉验证
- 用 Precision、Recall、F1、PR-AUC 评估，不要只看 Accuracy
- PR 曲线比 ROC 曲线在不平衡下更有信息量

## Build It

### Step 1: 从零实现 SMOTE

### Step 2: 对比原始 vs class_weight vs SMOTE

### Step 3: PR 曲线 vs ROC 曲线可视化

## Use It

```python
from imblearn.over_sampling import SMOTE, ADASYN
from imblearn.pipeline import Pipeline
```

## Exercises

## Key Terms

## Further Reading
