# Feature Selection

> 好特征选得好，模型小一半，性能翻一倍。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 2 Lesson 8 (Feature Engineering)
**Time:** ~45 minutes

## Learning Objectives

- 区分过滤、包装和嵌入三类特征选择方法
- 从零实现方差阈值、互信息和 L1 正则化选择
- 对比 RFE（递归特征消除）和 Lasso 选择的特征
- 在高维文本数据上展示特征选择能提升性能

## 核心概念

### 三类方法

| 类型 | 怎么选 | 代表方法 | 优点 | 缺点 |
|------|--------|----------|------|------|
| 过滤 | 独立于模型 | 方差阈值、互信息、相关性 | 快、独立、无泄露 | 忽略模型交互 |
| 包装 | 用模型性能选 | RFE、RFECV、贪心搜索 | 考虑特征交互 | 慢、过拟合风险 |
| 嵌入 | 训练时选 | L1 正则化、树模型重要性 | 训练一次就得到 | 绑定特定模型 |

### 过滤方法

**方差阈值**：去掉方差低于阈值的特征。低方差 = 几乎恒定 = 没用。

**互信息**：衡量特征和目标之间的非线性依赖。比相关性（只衡量线性）好。

**相关性阈值**：去掉互相之间相关系数高于 0.95 的冗余特征（保留其中一个）。

### L1 正则化做嵌入选择

Lasso 把不重要的权重驱动到**刚好零**。自动完成特征选择。选择非零权重的特征。

### RFE（递归特征消除）

贪心包装法：从所有特征开始，每轮去掉权重最小的特征，直到剩下 K 个。

### 数据泄露警告

目标编码之后不要用和目标相关的过滤方法（比如互信息）——如果从完整训练集算，有泄露风险。交叉验证中必须在每一折内部做特征选择。

## Build It

### Step 1: 从零方差阈值 + 互信息 + 相关性过滤

### Step 2: Lasso 嵌入选择和 RFE 包装选择

### Step 3: 在高维文本数据上对比带/不带特征选择

## Use It

```python
from sklearn.feature_selection import (
    VarianceThreshold, SelectKBest, SelectFromModel, RFE, mutual_info_classif
)
```

## Exercises

## Key Terms

## Further Reading
