# Anomaly Detection

> 在大海里捞一根针——大海是正常数据，针是你要找的异常。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 2 Lesson 7 (Unsupervised Learning)
**Time:** ~60 minutes

## Learning Objectives

- 区分点异常、集合异常和上下文异常
- 从零实现 Isolation Forest（孤立森林），解释它怎么利用路径长度
- 对比孤立森林、One-Class SVM 和 LOF 的适用场景
- 用股票价格或网络日志做实际的异常检测

## 核心概念

### 三种异常

- **点异常**：单个点偏离其他点（最常见）
- **集合异常**：一段时间整体异常（网络流量突增）
- **上下文异常**：值在某个上下文正常、另一个异常（周末购物量 vs 工作日）

### 孤立森林（Isolation Forest）

核心洞察：异常值更容易被孤立。随机特征 + 随机阈值建树，随机点平均需要更少分裂就把异常分出去了。

归一化路径长度就是异常分数。

优点：快 O(n log n)、自动给分数、不需要知道分布。

### One-Class SVM

拟合正常数据的最小包围球。球外的点是异常。非线性核可以拟合复杂形状。

### LOF（局部异常因子）

基于局部密度偏差。在均匀密集的数据上效果一般，但在密度变化大时比 IF 好。

### 评估异常检测

没有标签时无法精确评估。如果有少量标签：
- Precision @ K（前 K 个分数最高的点里有多少真异常）
- ROC-AUC（如果有标签）

## Build It

### Step 1: 从零 Isolation Forest

### Step 2: One-Class SVM 和 LOF 对比

### Step 3: 股票价格异常检测 demo

## Use It

```python
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.neighbors import LocalOutlierFactor
```

## Exercises

## Key Terms

## Further Reading
