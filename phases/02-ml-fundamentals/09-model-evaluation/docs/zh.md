# Model Evaluation & Cross-Validation

> 评估模型不止看一个数字。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 2 Lessons 1-3 (What Is ML, Linear Regression, Logistic Regression)
**Time:** ~60 minutes

## Learning Objectives

- 从零实现 K 折交叉验证和分层 K 折
- 为分类和回归问题选择合适的评估指标并解释原因
- 构建 ROC 曲线、PR 曲线和混淆矩阵，计算 AUC
- 区分训练集、验证集、测试集，并说明为什么测试集只能用一次

## 核心概念

### 为什么评估很难

单一数字（"准确率 85%"）掩盖了很多信息。模型可能只擅长多数类、可能在某个关键段预测特别差、或者过拟合到了验证集。

### 切分数据

训练/验证/测试三分。测试集是神圣的——只在最后用一次。

对于小数据集（< 10k 样本），用 K 折交叉验证代替单次切分：

```
对 K=5：
折 1：用 2-5 训练，1 验证
折 2：用 1,3-5 训练，2 验证
...
最后平均 K 次验证分数
```

分类问题用**分层 K 折**——每折中类别的比例和整体一致。

### 分类指标

| 指标 | 公式 | 何时用 |
|------|------|--------|
| Accuracy | (TP+TN)/total | 类别平衡时 |
| Precision | TP/(TP+FP) | 假阳性代价高 |
| Recall | TP/(TP+FN) | 假阴性代价高 |
| F1 | 2PR/(P+R) | 平衡精确率和召回率 |
| AUC-ROC | ROC 曲线下面积 | 阈值无关，比较模型排序质量 |

### 回归指标

| 指标 | 公式 | 特点 |
|------|------|------|
| MAE | mean(|y_pred - y_true|) | 鲁棒，和目标同单位 |
| RMSE | sqrt(mean((y_pred - y_true)²)) | 惩罚大误差 |
| R² | 1 - SS_res/SS_tot | 0-1 归一化 |

### ROC 和 PR 曲线

ROC 曲线：TPR vs FPR，阈值从 0 扫到 1。AUC 衡量排序能力。

PR 曲线：Precision vs Recall。不平衡数据下 PR 曲线比 ROC 曲线更有信息量。

## Build It

### Step 1: 混淆矩阵和基础指标

### Step 2: 从零实现 K 折交叉验证

### Step 3: ROC 曲线和 AUC

（详见 `code/evaluation.py`）

## Use It

## Exercises

## Key Terms

## Further Reading
