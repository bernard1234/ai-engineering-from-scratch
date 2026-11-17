# Time Series Forecasting

> 时间序列有自己的特殊结构：趋势、季节性、自相关性。

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 2 Lessons 1-3 (监督学习基础)
**Time:** ~60 minutes

## Learning Objectives

- 区分趋势、季节性、周期性和残差四个时间序列组成成分
- 用滑动窗口构建监督学习数据集（过去 N 步预测下一个值）
- 实现 ARIMA 或季节性分解的基础版本
- 用 Prophet 或 LSTM 做实际预测并对比结果

## 核心概念

### 四个成分

```
y(t) = Trend(t) + Seasonal(t) + Cyclic(t) + Residual(t)

Trend: 长期上升/下降（缓慢变化）
Seasonal: 固定周期（每周、每年重复）
Cyclic: 非固定周期（经济周期）
Residual: 随机噪声
```

### 经典方法 vs ML

- **经典**：ARIMA、Exponential Smoothing、Prophet
  - 可解释、快、对稳定序列好
- **ML**：把序列重构成监督学习问题
  - 滑动窗口：用 [t-N, t] 预测 t+1
  - 用任何回归器（XGBoost、LSTM、Transformer）
  - 对复杂非线性关系好

### 切分时间序列

**不能**用 train_test_split 打乱！时间是有序的。

```
train: 2020-01 到 2023-12
val:   2024-01 到 2024-06
test:  2024-07 到 2024-12
```

或滚动验证（walk-forward）：在窗口 [0, k] 上训练，验证 [k+1]，然后窗口移到 [1, k+1]。

### 自相关性

序列和它自己滞后版本的相关性。ACF（自相关函数）和 PACF（偏自相关）帮助选 ARIMA 参数。

## Build It

### Step 1: 滑动窗口重构

### Step 2: 用线性回归/XGBoost 做时间序列预测

### Step 3: Prophet 或 LSTM 预测

## Use It

## Exercises

## Key Terms

## Further Reading
