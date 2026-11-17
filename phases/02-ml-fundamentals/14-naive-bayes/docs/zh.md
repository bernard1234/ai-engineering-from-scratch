# Naive Bayes

> "朴素" 地假设特征独立，但效果常常出人意料地好。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 1 (Probability, Bayes' Theorem), Phase 2 Lesson 3 (Logistic Regression)
**Time:** ~45 minutes

## Learning Objectives

- 推导朴素贝叶斯公式并理解为什么 "朴素" 假设虽然不成立但模型仍有效
- 从零实现高斯朴素贝叶斯和多项式朴素贝叶斯，用于连续和文本特征
- 用 Laplace 平滑处理未见过的类别
- 在文本分类任务（垃圾邮件过滤器）上与逻辑回归对比准确率和推理速度

## 核心概念

### 从贝叶斯定理开始

```
P(y|x) = P(x|y) * P(y) / P(x)
```

朴素贝叶斯假设给定 y 时所有特征 x_i 条件独立：

```
P(x|y) = ∏ P(x_i | y)
```

这当然不成立（词之间肯定有依赖），但分类时分母 P(x) 对所有 y 相同，所以只需要：

```
y* = argmax_y P(y) * ∏ P(x_i | y)
```

### 三种变体

| 变体 | P(x_i | y) 假设 | 适用场景 |
|------|-----------------|----------|
| 高斯 | 正态分布 | 连续数值特征 |
| 多项式 | 多项分布 + 计数 | 文本计数、整数特征 |
| 伯努利 | 二元特征 | 存在/不存在 |

### 为什么管用

- 训练极快 O(n * d)
- 推理极快 O(d)
- 对小数据集友好
- 独立假设的违反被高维特征下所有 P(x_i|y) 项的乘积主导——即使每个都不准，相对大小排序还是对的

### Laplace 平滑

未见过的特征值会让 P(x_i|y) = 0，整个乘积变成零。用平滑：

```
P(x_i = k | y) = (count(x_i=k, y) + α) / (count(y) + α*K)
```

α=1 是拉普拉斯平滑。α 可调。

## Build It

### Step 1: 高斯朴素贝叶斯（连续特征）

### Step 2: 多项式朴素贝叶斯（文本分类）

### Step 3: 垃圾邮件过滤器 demo

## Use It

```python
from sklearn.naive_bayes import GaussianNB, MultinomialNB
```

## Exercises

## Key Terms

## Further Reading
