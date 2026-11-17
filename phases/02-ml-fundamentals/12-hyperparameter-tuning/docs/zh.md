# Hyperparameter Tuning

> 默认参数几乎永远不是最优的。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 2 Lessons 9 (Evaluation), 10 (Bias-Variance)
**Time:** ~60 minutes

## Learning Objectives

- 对比网格搜索、随机搜索和贝叶斯优化的优缺点
- 从零实现网格搜索和随机搜索，并验证随机搜索在高维上更高效
- 用 Optuna 或 Hyperopt 做贝叶斯优化
- 说明为什么早停是调参的重要辅助手段

## 核心概念

### 三种搜索策略

**网格搜索**：对每个参数的固定候选值做笛卡尔积遍历。小参数空间（< 20 组合）。组合数爆炸。

**随机搜索**：在参数空间随机采样。Bengio & Bergstra (2012) 论文证明它比网格搜索高效得多——因为很多参数是不重要的，随机搜索给重要参数更多尝试。

**贝叶斯优化**：用概率模型（通常高斯过程）建模 f(x)，选下一个最有前景的点。最智能但实现复杂。工具：Optuna、Hyperopt、Spearmint。

### 早停

训练过程中监控验证损失。如果连续 N 轮（patience）验证损失没有改善，就停止训练，回到最好的检查点。自动决定训练轮次。

### 调参流程

1. 粗搜索（大范围、少迭代）
2. 锁定好区域
3. 精细搜索（小范围、多迭代）
4. 验证集上选最优
5. 用 train + val 重训最终模型

### 交叉验证 + 调参

调参时也要用交叉验证。每个参数组合都跑 K 折。报告 mean ± std。

## Build It

### Step 1: 从零网格搜索

### Step 2: 从零随机搜索

### Step 3: Optuna 贝叶斯优化

## Use It

```python
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
import optuna
```

## Exercises

## Key Terms

## Further Reading
