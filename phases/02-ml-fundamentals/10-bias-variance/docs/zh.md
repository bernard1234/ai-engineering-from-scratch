# Bias-Variance Tradeoff

> 偏差和方差是所有 ML 模型的根本权衡。

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 1 (Calculus, Linear Algebra), Phase 2 Lessons 1-3
**Time:** ~45 minutes

## Learning Objectives

- 分解期望泛化误差为偏差² + 方差 + 噪声三个组成部分
- 用 KNN 和线性回归的例子说明高偏差 vs 高方差的特征
- 构建学习曲线（训练/验证误差 vs 样本数）来诊断偏差和方差
- 列出降低偏差和降低方差的方法

## 核心概念

### 公式

```
Expected Error = Bias² + Variance + Noise

Bias²: 模型假设错误导致的误差。线性模型拟合弯曲数据时高。
Variance: 对训练数据微小变化的敏感度。复杂模型（高阶多项式）训练集变一点预测就大变。
Noise: 数据本身的不可约误差。无法降低。
```

### 可视化

```
偏差高（欠拟合）:
  训练误差 ≈ 验证误差 ≈ 高
  学习曲线：两者都上升后变平

方差高（过拟合）:
  训练误差 ≈ 0，验证误差高
  学习曲线：训练下降、验证上升
```

### 降低偏差

- 增加模型复杂度（更多参数、更高阶多项式、更深网络）
- 增加特征
- 减少正则化
- 训练更久

### 降低方差

- 减少模型复杂度
- 增加训练数据
- 正则化（L1/L2、Dropout、早停）
- 特征选择
- 集成（Bagging）

### 学习曲线

训练误差和验证误差 vs 训练样本数：

```
欠拟合：两者都高且接近
过拟合：训练低、验证高，且差距稳定
完美：都低且接近
```

## Build It

用 KNN 回归器（K=1, 5, 15）演示：
- K=1：低偏差、高方差（过拟合）
- K=5：平衡
- K=15：高偏差、低方差（欠拟合）

画训练/验证误差 vs K。

## Exercises

## Key Terms

## Further Reading
