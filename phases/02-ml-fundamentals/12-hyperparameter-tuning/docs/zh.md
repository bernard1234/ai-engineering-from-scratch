# 超参数调优

> 超参数是你在训练开始前拧的旋钮。拧得好不好决定了平庸模型和优秀模型之间的差距。

**Type:** Build
**Language:** Python
**Prerequisites:** Phase 2, Lesson 11 (集成方法)
**Time:** ~90 minutes

## Learning Objectives

- 从零实现网格搜索、随机搜索和贝叶斯优化，对比它们的样本效率
- 解释为什么当大部分超参数有效维度低时，随机搜索胜网格搜索
- 构建使用代理模型和采集函数的贝叶斯优化循环来指导搜索
- 设计通过正确交叉验证避免对验证集过拟合的超参数调优策略

## 问题场景

你的梯度提升模型有学习率、树数、最大深度、叶节点最小样本数、子采样率、列采样率——六个超参数。如果每个有 5 个合理值，网格就是 5⁶ = 15,625 个组合。训练每个要 10 秒。全部试完要 43 小时算力。

网格搜索是最显而易见的方法，也是规模上最差的。随机搜索用更少算力做得更好。贝叶斯优化做得还更好，因为它从过去的评估里学习。知道用哪个策略、以及哪些超参数真的重要，能省下几天被浪费的 GPU 时间。

## 核心概念

### 参数 vs 超参数

参数在训练中学习（权重、偏置、分裂阈值）。超参数在训练开始前设置，控制学习怎么发生。

| 超参数 | 控制什么 | 典型范围 |
|--------|----------|----------|
| 学习率 | 每次更新步长 | 0.001 到 1.0 |
| 树数 / epoch 数 | 训练多久 | 10 到 10,000 |
| 最大深度 | 模型复杂度 | 1 到 30 |
| 正则化（λ） | 防过拟合 | 0.0001 到 100 |
| Batch size | 梯度估计噪声 | 16 到 512 |
| Dropout rate | 关掉的神经元比例 | 0.0 到 0.5 |

### 网格搜索

网格搜索评估所有指定值的组合。它穷举、易懂，但随超参数数量指数放大。

（ASCII 示例保留）

网格搜索有个根本缺陷：如果一个超参数重要、另一个不重要，大部分评估都浪费了。你从 9 次评估里只拿到了 3 个重要参数的唯一值。

### 随机搜索

随机搜索从分布里采超参数而不是从网格里采。同样的 9 次预算，你能拿到每个超参数 9 个唯一值。

（mermaid 图保留）

为什么随机胜网格（Bergstra & Bengio, 2012）：
- 大部分超参数有效维度低。给定问题 6 个超参数里通常只有 1-2 个真的重要。
- 网格搜索在不重要的维度上浪费评估。
- 随机搜索用同样预算更密地覆盖了重要维度。
- 60 次随机试验时，你有 95% 的概率找到离最优值 5% 以内的点（如果搜索空间里存在）。

### 贝叶斯优化

随机搜索不看结果。它不知道高学习率导致发散、深度 3 一贯地胜过深度 10。贝叶斯优化用过去的评估来决定接下来往哪搜。

（mermaid 图保留）

两个核心组件：

**代理模型**：便宜的近似模型（通常是高斯过程），近似那个昂贵的目标函数。它在搜索空间里任何点给出预测和不确定性估计。

**采集函数**：通过平衡开发（在已知好点附近搜）和探索（在不确定性高的地方搜）来决定下一个评估哪里。常见选择：
- **Expected Improvement (EI)**：我们在这个点期待的相对当前最优的提升有多少？
- **Upper Confidence Bound (UCB)**：预测值加不确定性的倍数。高 UCB 意味着要么有前景，要么还没探索过。
- **Probability of Improvement (PI)**：这个点胜过当前最优的概率是多少？

贝叶斯优化通常用少 2-5 倍的评估次数就比随机搜索找到更好的超参数。拟合代理模型的开销和训练实际模型相比可忽略。

### 早停

不是每个训练 run 都需要跑完。如果一个配置在 10 个 epoch 后明显很糟，就停它换下一个。这是超参数搜索语境下的早停。

策略：
- **Patience-based**：如果验证损失连续 N 个 epoch 没改进就停
- **中位数剪枝**：如果试验的中间结果比同一步已完成试验的中位数还差就停
- **Hyperband**：给很多配置分配小预算，然后逐渐给最好的那些加预算

Hyperband 特别有效。它用 1 epoch 启动 81 个配置，保留前三分之一，给它们 3 epoch，再保留前三分之一，依此类推。这比用完整预算评估所有配置快 10-50 倍找到好配置。

### 学习率调度器

学习率几乎总是最重要的超参数。与其保持恒定，调度器在训练期间调整它。

| 调度器 | 公式 | 什么时候用 |
|--------|------|------------|
| Step decay | 每 N 个 epoch 乘以 0.1 | 经典 CNN 训练 |
| Cosine annealing | lr · 0.5 · (1 + cos(πt/T)) | 现代默认 |
| Warmup + decay | 线性爬升然后 cosine 下降 | Transformer |
| One-cycle | 增加然后在一个周期内减少 | 快速收敛 |
| Reduce on plateau | 指标停滞时按系数减少 | 安全默认 |

### 超参数重要性

不是所有超参数同等重要。对随机森林（Probst et al., 2019）和梯度提升的研究显示一致的模式：

**高重要性：**
- 学习率（总是先调它）
- 估计器数 / epoch 数（改用早停代替调这个）
- 正则化强度

**中重要性：**
- 最大深度 / 层数
- 叶节点最小样本数 / weight decay
- 子采样率

**低重要性：**
- 最大特征数（随机森林）
- 具体激活函数选择
- Batch size（合理范围内）

先调重要的，其余留默认值。

### 实用策略

（mermaid 图保留）

具体工作流：

1. **从库默认值开始。** 它们由有经验的实践者选过，通常已经达到了 80% 的效果。
2. **粗随机搜索。** 范围宽，20-50 次试验。用早停快速干掉差的 run。
3. **分析结果。** 哪些超参数和性能相关？缩小搜索空间。
4. **精细搜索。** 贝叶斯优化或聚焦的随机搜索，50-100 次试验。
5. **用找到的最好超参数在全部训练数据上重训。**

### 交叉验证集成

在单个验证切分上调超参数有风险。最好的超参数可能对某个验证折过拟合。嵌套交叉验证通过用两个循环来解决：

- **外层循环**（评估）：把数据切成 train+val 和 test。报告无偏性能。
- **内层循环**（调优）：把 train+val 切成 train 和 val。找最好的超参数。

（mermaid 图保留）

每个外层折独立找自己的最好超参数。外层分数是泛化性能的无偏估计。

```python
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.ensemble import GradientBoostingRegressor

inner_cv = GridSearchCV(
    GradientBoostingRegressor(),
    param_grid={
        "learning_rate": [0.01, 0.05, 0.1],
        "max_depth": [2, 3, 5],
        "n_estimators": [50, 100, 200],
    },
    cv=5,
    scoring="neg_mean_squared_error",
)

outer_scores = cross_val_score(
    inner_cv, X, y, cv=5, scoring="neg_mean_squared_error"
)

print(f"Nested CV MSE: {-outer_scores.mean():.4f} +/- {outer_scores.std():.4f}")
```

这比较贵（5 外层折 × 5 内层折 × 27 网格点 = 675 次模型拟合），但给你值得信任的性能估计。用在论文报告最终结果或决策赌注高的时候。

### 实用技巧

**从学习率开始。** 它总是梯度方法里最重要的超参数。坏的学习率让其他一切都无关。固定其他超参数为默认值，先扫学习率。

**学习率和正则化用 log-uniform 分布。** 0.001 和 0.01 的差异和 0.1 和 1.0 的差异一样大。线性搜索会在大端浪费预算。

**用早停代替调 n_estimators。** 对 Boosting 和神经网络，把 n_estimators 或 epochs 设高，让早停决定什么时候停。这把一个超参数从搜索里拿掉了。

**预算分配。** 60% 的调优预算花在前两个最重要的超参数上。剩下 40% 给其他一切。前两个决定了大部分性能变化。

**尺度问题。** Batch size 永远别在 log 尺度上搜（16, 32, 64 就行）。学习率永远在 log 尺度上搜。搜索分布要匹配超参数怎么影响模型。

| 模型类型 | 顶级超参数 | 推荐搜索 | 预算 |
|----------|-----------|----------|------|
| 随机森林 | n_estimators, max_depth, min_samples_leaf | 随机搜索，50 次 | 低（训练快） |
| 梯度提升 | learning_rate, n_estimators, max_depth | 贝叶斯，100 次 + 早停 | 中 |
| 神经网络 | learning_rate, weight_decay, batch_size | 贝叶斯或随机，100+ 次 | 高（训练慢） |
| SVM | C, gamma（RBF 核） | 对数尺度网格，25-50 次 | 低（2 个参数） |
| Lasso/Ridge | alpha | 对数尺度 1D 搜索，20 次 | 非常低 |
| XGBoost | learning_rate, max_depth, subsample, colsample | 贝叶斯，100-200 次 + 早停 | 中 |

**拿不准的时候：** 随机搜索，试验次数 ≥ 超参数数量的 2 倍（比如 6 个超参数 = 至少 12 次）。你会惊讶地发现 50 次随机搜索多少次能赢过仔细设计的网格搜索。

```figure
k-fold-cv
```

## Build It

`code/tuning.py` 里的代码从零实现了网格搜索、随机搜索和一个简化贝叶斯优化器。

### 第 1 步：从零网格搜索

```python
def grid_search(model_fn, param_grid, X_train, y_train, X_val, y_val):
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    best_score = -float("inf")
    best_params = None
    n_evals = 0

    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        model = model_fn(**params)
        model.fit(X_train, y_train)
        score = evaluate(model, X_val, y_val)
        n_evals += 1

        if score > best_score:
            best_score = score
            best_params = params

    return best_params, best_score, n_evals
```

### 第 2 步：从零随机搜索

```python
def random_search(model_fn, param_distributions, X_train, y_train,
                  X_val, y_val, n_iter=50, seed=42):
    rng = np.random.RandomState(seed)
    best_score = -float("inf")
    best_params = None

    for _ in range(n_iter):
        params = {k: sample(v, rng) for k, v in param_distributions.items()}
        model = model_fn(**params)
        model.fit(X_train, y_train)
        score = evaluate(model, X_val, y_val)

        if score > best_score:
            best_score = score
            best_params = params

    return best_params, best_score, n_iter
```

### 第 3 步：贝叶斯优化（简化版）

核心想法：把高斯过程拟合到观测到的（超参数，分数）对上，然后用采集函数决定接下来往哪看。

```python
class SimpleBayesianOptimizer:
    def __init__(self, search_space, n_initial=5):
        self.search_space = search_space
        self.n_initial = n_initial
        self.X_observed = []
        self.y_observed = []

    def _kernel(self, x1, x2, length_scale=1.0):
        dists = np.sum((x1[:, None, :] - x2[None, :, :]) ** 2, axis=2)
        return np.exp(-0.5 * dists / length_scale ** 2)

    def _fit_gp(self, X_new):
        X_obs = np.array(self.X_observed)
        y_obs = np.array(self.y_observed)
        y_mean = y_obs.mean()
        y_centered = y_obs - y_mean

        K = self._kernel(X_obs, X_obs) + 1e-4 * np.eye(len(X_obs))
        K_star = self._kernel(X_new, X_obs)

        L = np.linalg.cholesky(K)
        alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_centered))
        mu = K_star @ alpha + y_mean

        v = np.linalg.solve(L, K_star.T)
        var = 1.0 - np.sum(v ** 2, axis=0)
        var = np.maximum(var, 1e-6)

        return mu, var

    def _expected_improvement(self, mu, var, best_y):
        sigma = np.sqrt(var)
        z = (mu - best_y) / (sigma + 1e-10)
        ei = sigma * (z * norm_cdf(z) + norm_pdf(z))
        return ei

    def suggest(self):
        if len(self.X_observed) < self.n_initial:
            return sample_random(self.search_space)

        candidates = [sample_random(self.search_space) for _ in range(500)]
        X_cand = np.array([to_vector(c) for c in candidates])
        mu, var = self._fit_gp(X_cand)
        ei = self._expected_improvement(mu, var, max(self.y_observed))
        return candidates[np.argmax(ei)]

    def observe(self, params, score):
        self.X_observed.append(to_vector(params))
        self.y_observed.append(score)
```

GP 代理在每个候选点给两个东西：预测分数（μ）和不确定性（σ）。Expected Improvement 平衡两者：它偏好模型预测高分数**或**不确定性高的点。早期大部分点不确定性高，所以优化器在探索。后期它聚焦到最有前景的区域。

### 第 4 步：对比所有方法

同样预算下，贝叶斯优化通常最快找到最好分数，因为它不在明显差的区域浪费评估。随机搜索比网格搜索覆盖更多地盘。网格搜索只在你有很少超参数且能穷举时才赢。

```python
def synthetic_objective(params):
    lr = params["learning_rate"]
    depth = params["max_depth"]
    return -(np.log10(lr) + 2) ** 2 - (depth - 4) ** 2 + 10

param_grid = {
    "learning_rate": [0.001, 0.01, 0.1, 1.0],
    "max_depth": [2, 3, 4, 5, 6, 7, 8],
}

grid_best = None
grid_score = -float("inf")
grid_history = []
for combo in itertools.product(*param_grid.values()):
    params = dict(zip(param_grid.keys(), combo))
    score = synthetic_objective(params)
    grid_history.append((params, score))
    if score > grid_score:
        grid_score = score
        grid_best = params

param_dist = {
    "learning_rate": ("log_float", 0.001, 1.0),
    "max_depth": ("int", 2, 8),
}

rand_best = None
rand_score = -float("inf")
rand_history = []
rng = np.random.RandomState(42)
for _ in range(28):
    params = {k: sample(v, rng) for k, v in param_dist.items()}
    score = synthetic_objective(params)
    rand_history.append((params, score))
    if score > rand_score:
        rand_score = score
        rand_best = params

optimizer = SimpleBayesianOptimizer(param_dist, n_initial=5)
bayes_history = []
for _ in range(28):
    params = optimizer.suggest()
    score = synthetic_objective(params)
    optimizer.observe(params, score)
    bayes_history.append((params, score))
bayes_score = max(s for _, s in bayes_history)

print(f"{'Method':<20} {'Best Score':>12} {'Evaluations':>12}")
print("-" * 50)
print(f"{'Grid Search':<20} {grid_score:>12.4f} {len(grid_history):>12}")
print(f"{'Random Search':<20} {rand_score:>12.4f} {len(rand_history):>12}")
print(f"{'Bayesian Opt':<20} {bayes_score:>12.4f} {len(bayes_history):>12}")
```

## Use It

### Optuna 实战

Optuna 是严肃超参数调优推荐的库。原生支持剪枝、分布式搜索和可视化。

```python
import optuna

def objective(trial):
    lr = trial.suggest_float("learning_rate", 1e-4, 1e-1, log=True)
    n_est = trial.suggest_int("n_estimators", 50, 500)
    max_depth = trial.suggest_int("max_depth", 2, 10)

    model = GradientBoostingRegressor(
        learning_rate=lr,
        n_estimators=n_est,
        max_depth=max_depth,
    )
    model.fit(X_train, y_train)
    return mean_squared_error(y_val, model.predict(X_val))

study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=100)

print(f"Best params: {study.best_params}")
print(f"Best MSE: {study.best_value:.4f}")
```

### 带剪枝的 Optuna

剪枝提前停掉没前景的试验，省大量算力。

```python
import optuna
from sklearn.model_selection import cross_val_score

def objective(trial):
    params = {
        "learning_rate": trial.suggest_float("lr", 1e-4, 0.5, log=True),
        "max_depth": trial.suggest_int("max_depth", 2, 10),
        "n_estimators": trial.suggest_int("n_estimators", 50, 500),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
    }

    model = GradientBoostingRegressor(**params)
    scores = cross_val_score(model, X_train, y_train, cv=3,
                             scoring="neg_mean_squared_error")
    mean_score = -scores.mean()

    trial.report(mean_score, step=0)
    if trial.should_prune():
        raise optuna.TrialPruned()

    return mean_score

pruner = optuna.pruners.MedianPruner(n_startup_trials=10, n_warmup_steps=5)
study = optuna.create_study(direction="minimize", pruner=pruner)
study.optimize(objective, n_trials=200)
```

`MedianPruner` 在中间值比同一步所有已完成试验的中位数还差时停掉试验。剪枝通常省 40-60% 总算力。

### sklearn 内置调优器

快速实验用 sklearn 提供 `GridSearchCV`、`RandomizedSearchCV` 和 `HalvingRandomSearchCV`：

```python
from sklearn.model_selection import RandomizedSearchCV
from scipy.stats import loguniform, randint

param_dist = {
    "learning_rate": loguniform(1e-4, 0.5),
    "max_depth": randint(2, 10),
    "n_estimators": randint(50, 500),
}

search = RandomizedSearchCV(
    GradientBoostingRegressor(),
    param_dist,
    n_iter=100,
    cv=5,
    scoring="neg_mean_squared_error",
    random_state=42,
    n_jobs=-1,
)
search.fit(X_train, y_train)
print(f"Best params: {search.best_params_}")
print(f"Best CV MSE: {-search.best_score_:.4f}")
```

学习率和正则化用 scipy 的 `loguniform`。整数超参数用 `randint`。`n_jobs=-1` 在所有 CPU 核上并行。

**预处理导致的数据泄露。** 如果你在交叉验证之前就在整个数据集上拟合 scaler，验证折的信息泄露进训练。永远把预处理放进 `Pipeline` 里，让它只在训练折上拟合。

**对验证集过拟合。** 跑数千次试验相当于在验证集上训练。对最终性能估计用嵌套交叉验证，或者留一个你在调优期间从不碰的测试集。

**搜索范围太窄。** 如果你的最好值恰好在搜索空间的边界上，你没搜够广。最优值可能在你的范围之外。永远检查最好参数是不是在边界上。

**忽略交互效应。** 学习率和估计器数在 Boosting 里交互很强。低学习率需要更多估计器。独立调它们比一起调得到更差的结果。

**迭代模型不用早停。** 对梯度提升和神经网络，把 n_estimators 或 epochs 设高然后用早停。这比把迭代次数当超参数调严格更好。

## Exercises

1. 用相同总预算（比如 50 次评估）跑网格搜索和随机搜索。对比找到的最好分数。用不同种子做 10 次实验。随机搜索赢的比例是多少？
2. 从零实现 Hyperband。从 81 个配置每个训练 1 epoch 开始。每轮保留前 1/3 并把预算翻三倍。对比总算力（所有配置的所有 epoch 加总）和让 81 个配置跑完整预算。
3. 在第 11 课的梯度提升实现里加学习率调度器（cosine annealing）。和固定学习率相比有帮助吗？
4. 用 Optuna 在真实数据集（比如 sklearn 的 breast cancer 数据集）上调 RandomForestClassifier。用 `optuna.visualization.plot_param_importances(study)` 看哪些超参数最重要。和本课的重要性排序匹配吗？
5. 实现简单采集函数（Expected Improvement）并演示探索 vs 开发。画出代理模型的均值和不确定性，以及 EI 选择在哪里评估下一次。

## Key Terms

| 术语 | 人们常说 | 实际含义 |
|------|----------|----------|
| Hyperparameter | "你选的一个设置" | 训练前设置、控制学习过程的值，不是从数据里学的 |
| 网格搜索 | "试每个组合" | 穷举指定参数网格上的每一种组合。指数级成本。 |
| 随机搜索 | "就随机采样" | 从分布里采超参数。比网格搜索更好地覆盖重要维度。 |
| 贝叶斯优化 | "聪明地搜" | 用目标的代理模型决定接下来评估哪里，平衡探索和开发 |
| 代理模型 | "便宜的近似" | 从观测评估里近似昂贵目标函数的模型（通常是高斯过程） |
| 采集函数 | "下一个看哪里" | 通过平衡预期提升和不确定性给候选点打分。EI 和 UCB 是常见选择。 |
| 早停 | "别浪费时间" | 验证性能停止提升时提前终止训练 |
| Hyperband | "配置的锦标赛淘汰赛" | 自适应资源分配：小预算启动很多配置，保留最好的加预算 |
| 学习率调度器 | "训练过程中改 lr" | 训练过程中调整学习率以获得更好收敛的函数 |

## Further Reading

- [Bergstra & Bengio: Random Search for Hyper-Parameter Optimization (2012)](https://jmlr.org/papers/v13/bergstra12a.html) — 随机胜过网格的论文
- [Snoek et al., Practical Bayesian Optimization of Machine Learning Algorithms (2012)](https://arxiv.org/abs/1206.2944) — 用于 ML 的贝叶斯优化
- [Li et al., Hyperband (2018)](https://jmlr.org/papers/v18/16-558.html) — Hyperband 论文
- [Optuna: A Next-generation Hyperparameter Optimization Framework](https://arxiv.org/abs/1907.10902) — Optuna 论文
- [Probst et al., Tunability: Importance of Hyperparameters (2019)](https://jmlr.org/papers/v20/18-444.html) — 哪些超参数重要
