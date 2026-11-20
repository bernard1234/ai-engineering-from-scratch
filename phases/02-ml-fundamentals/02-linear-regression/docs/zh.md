# Linear Regression

> 线性回归在数据之间画出最佳直线。它是机器学习的 "Hello World"。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 1 (Linear Algebra, Calculus, Optimization), Phase 2 Lesson 1
**Time:** \~90 minutes

## Learning Objectives

- 推导均方误差的梯度下降更新规则，并从零实现线性回归
- 从计算复杂度和使用时机方面对比梯度下降和正规方程
- 构建带特征标准化的多元线性回归模型，并解释学到的权重
- 说明 Ridge 回归（L2 正则化）如何通过惩罚大权重防止过拟合

## 问题场景

你有数据：房子面积和售价。你想根据面积预测新房价格。散点图上能看个大概，但你需要一个公式——一条最贴合数据的直线，这样你输入任何面积就能得到价格预测。

线性回归给你这条直线。更重要的是，它引入了完整的 ML 训练循环：定义模型 → 定义损失函数 → 优化参数。每个 ML 算法都遵循这个模式。在这里用最简单的情况掌握它，之后你会到处认出这个套路。

这不是只给简单问题用的。生产系统里用线性回归做需求预测、A/B 测试分析、金融建模，以及作为每个回归任务的基线。

## 核心概念

### 模型

线性回归假设输入 (x) 和输出 (y) 之间是线性关系：

```
y = wx + b
```

- `w`（权重/斜率）：x 增加 1 时 y 变化多少
- `b`（偏置/截距）：x = 0 时 y 的值

多个输入（特征）时，扩展为：

```
y = w1*x1 + w2*x2 + ... + wn*xn + b
```

向量形式：`y = w^T * x + b`

目标：找到 w 和 b 的值，让预测的 y 在所有训练样本上尽可能接近实际的 y。

### 损失函数（均方误差）

怎么衡量 "尽可能接近"？你需要一个数字来量化预测有多错。最常用的选择是均方误差（MSE）：

```
MSE = (1/n) * sum((y_predicted - y_actual)^2)
```

为什么要平方？两个原因。第一，它对大错误的惩罚比小错误更重（误差 10 是误差 1 的 100 倍糟，不是 10 倍）。第二，平方函数处处光滑可导，使优化变得直接。

损失函数构成一个曲面。对于单个权重 w 和偏置 b，MSE 曲面像一个碗（凸的旋转抛物面）。碗底就是 MSE 最小的地方。训练就是找那个底。

### 梯度下降

梯度下降通过沿坡向下走找到碗底。

```mermaid
flowchart TD
    A[Initialize w and b randomly] --> B[Compute predictions: y_hat = wx + b]
    B --> C[Compute cost: MSE]
    C --> D[Compute gradients: dMSE/dw, dMSE/db]
    D --> E[Update parameters]
    E --> F{Cost low enough?}
    F -->|No| B
    F -->|Yes| G[Done: optimal w and b found]
```

梯度告诉你两件事：每个参数应该往哪个方向走，以及走多少。

对于 MSE 和 y\_hat = wx + b：

```
dMSE/dw = (2/n) * sum((y_hat - y) * x)
dMSE/db = (2/n) * sum(y_hat - y)
```

更新规则：

```
w = w - learning_rate * dMSE/dw
b = b - learning_rate * dMSE/db
```

学习率控制步长。太大：冲过最优点发散。太小：训练到天荒地老。典型起点：0.01、0.001 或 0.0001。

### 正规方程（闭式解）

专门针对线性回归，有一个直接公式能不给迭代就给出最优权重：

```
w = (X^T * X)^(-1) * X^T * y
```

它通过矩阵求逆一步解出 w。对小数据集完美适用。对大数据集（几百万行或几千特征），矩阵求逆在特征数上是 O(n³)，更倾向用梯度下降。

### 多元线性回归

多个特征时，模型变成：

```
y = w1*x1 + w2*x2 + ... + wn*xn + b
```

一切照旧：MSE 是损失函数，梯度下降同时更新所有权重。唯一的区别是你在拟合一个超平面而不是一条直线。

特征缩放在这里很重要。如果一个特征范围是 0 到 1，另一个是 0 到 1,000,000，梯度下降会很费劲，因为损失曲面变得细长。训练前先标准化特征（减均值、除标准差）。

### 多项式回归

如果关系不是线性的呢？你仍然可以用线性回归，方法是构造多项式特征：

```
y = w1*x + w2*x^2 + w3*x^3 + b
```

这仍然是 "线性" 回归，因为模型对权重（w1, w2, w3）来说是线性的。你只是用了 x 的非线性特征。

更高次的多项式能拟合更复杂的曲线，但容易过拟合。一个 10 次多项式会穿过 10 点数据集里的每个点，但在新数据上预测很差。

### R-Squared 分数

MSE 告诉你有多错，但这个数字依赖于 y 的尺度。R-squared (R²) 给出一个尺度无关的度量：

```
R^2 = 1 - (sum of squared residuals) / (sum of squared deviations from mean)
    = 1 - SS_res / SS_tot
```

- R² = 1.0：完美预测
- R² = 0.0：模型不比每次都预测均值好
- R² < 0.0：模型比预测均值还差

### 正则化预览（Ridge 回归）

当你有很多特征时，模型可能通过给大权重来过拟合。Ridge 回归（L2 正则化）加一个惩罚项：

```
Cost = MSE + lambda * sum(w_i^2)
```

惩罚项抑制大权重。超参数 lambda 控制权衡：lambda 越高，权重越小，正则化越强。这在后续课程里深入讲。现在先知道它存在，以及为什么有用。

```figure
linear-regression-fit
```

## Build It

### 第 1 步：生成示例数据

```python
import random
import math

random.seed(42)

TRUE_W = 3.0
TRUE_B = 7.0
N_SAMPLES = 100

X = [random.uniform(0, 10) for _ in range(N_SAMPLES)]
y = [TRUE_W * x + TRUE_B + random.gauss(0, 2.0) for x in X]

print(f"Generated {N_SAMPLES} samples")
print(f"True relationship: y = {TRUE_W}x + {TRUE_B} (+ noise)")
print(f"First 5 points: {[(round(X[i], 2), round(y[i], 2)) for i in range(5)]}")
```

### 第 2 步：从零实现带梯度下降的线性回归

```python
class LinearRegression:
    def __init__(self, learning_rate=0.01):
        self.w = 0.0
        self.b = 0.0
        self.lr = learning_rate
        self.cost_history = []

    def predict(self, X):
        return [self.w * x + self.b for x in X]

    def compute_cost(self, X, y):
        predictions = self.predict(X)
        n = len(y)
        cost = sum((pred - actual) ** 2 for pred, actual in zip(predictions, y)) / n
        return cost

    def compute_gradients(self, X, y):
        predictions = self.predict(X)
        n = len(y)
        dw = (2 / n) * sum((pred - actual) * x for pred, actual, x in zip(predictions, y, X))
        db = (2 / n) * sum(pred - actual for pred, actual in zip(predictions, y))
        return dw, db

    def fit(self, X, y, epochs=1000, print_every=200):
        for epoch in range(epochs):
            dw, db = self.compute_gradients(X, y)
            self.w -= self.lr * dw
            self.b -= self.lr * db
            cost = self.compute_cost(X, y)
            self.cost_history.append(cost)
            if epoch % print_every == 0:
                print(f"  Epoch {epoch:4d} | Cost: {cost:.4f} | w: {self.w:.4f} | b: {self.b:.4f}")
        return self

    def r_squared(self, X, y):
        predictions = self.predict(X)
        y_mean = sum(y) / len(y)
        ss_res = sum((actual - pred) ** 2 for actual, pred in zip(y, predictions))
        ss_tot = sum((actual - y_mean) ** 2 for actual in y)
        return 1 - (ss_res / ss_tot)


print("=== Training Linear Regression (Gradient Descent) ===")
model = LinearRegression(learning_rate=0.005)
model.fit(X, y, epochs=1000, print_every=200)
print(f"\nLearned: y = {model.w:.4f}x + {model.b:.4f}")
print(f"True:    y = {TRUE_W}x + {TRUE_B}")
print(f"R-squared: {model.r_squared(X, y):.4f}")
```

### 第 3 步：正规方程（闭式解）

```python
class LinearRegressionNormal:
    def __init__(self):
        self.w = 0.0
        self.b = 0.0

    def fit(self, X, y):
        n = len(X)
        x_mean = sum(X) / n
        y_mean = sum(y) / n
        numerator = sum((X[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((X[i] - x_mean) ** 2 for i in range(n))
        self.w = numerator / denominator
        self.b = y_mean - self.w * x_mean
        return self

    def predict(self, X):
        return [self.w * x + self.b for x in X]

    def r_squared(self, X, y):
        predictions = self.predict(X)
        y_mean = sum(y) / len(y)
        ss_res = sum((actual - pred) ** 2 for actual, pred in zip(y, predictions))
        ss_tot = sum((actual - y_mean) ** 2 for actual in y)
        return 1 - (ss_res / ss_tot)


print("\n=== Normal Equation (Closed-Form) ===")
model_normal = LinearRegressionNormal()
model_normal.fit(X, y)
print(f"Learned: y = {model_normal.w:.4f}x + {model_normal.b:.4f}")
print(f"R-squared: {model_normal.r_squared(X, y):.4f}")
```

### 第 4 步：多元线性回归

```python
class MultipleLinearRegression:
    def __init__(self, n_features, learning_rate=0.01):
        self.weights = [0.0] * n_features
        self.bias = 0.0
        self.lr = learning_rate
        self.cost_history = []

    def predict_single(self, x):
        return sum(w * xi for w, xi in zip(self.weights, x)) + self.bias

    def predict(self, X):
        return [self.predict_single(x) for x in X]

    def compute_cost(self, X, y):
        predictions = self.predict(X)
        n = len(y)
        return sum((pred - actual) ** 2 for pred, actual in zip(predictions, y)) / n

    def fit(self, X, y, epochs=1000, print_every=200):
        n = len(y)
        n_features = len(X[0])
        for epoch in range(epochs):
            predictions = self.predict(X)
            errors = [pred - actual for pred, actual in zip(predictions, y)]
            for j in range(n_features):
                grad = (2 / n) * sum(errors[i] * X[i][j] for i in range(n))
                self.weights[j] -= self.lr * grad
            grad_b = (2 / n) * sum(errors)
            self.bias -= self.lr * grad_b
            cost = self.compute_cost(X, y)
            self.cost_history.append(cost)
            if epoch % print_every == 0:
                print(f"  Epoch {epoch:4d} | Cost: {cost:.4f}")
        return self

    def r_squared(self, X, y):
        predictions = self.predict(X)
        y_mean = sum(y) / len(y)
        ss_res = sum((actual - pred) ** 2 for actual, pred in zip(y, predictions))
        ss_tot = sum((actual - y_mean) ** 2 for actual in y)
        return 1 - (ss_res / ss_tot)


random.seed(42)
N = 100
X_multi = []
y_multi = []
for _ in range(N):
    size = random.uniform(500, 3000)
    bedrooms = random.randint(1, 5)
    age = random.uniform(0, 50)
    price = 50 * size + 10000 * bedrooms - 1000 * age + 50000 + random.gauss(0, 20000)
    X_multi.append([size, bedrooms, age])
    y_multi.append(price)


def standardize(X):
    n_features = len(X[0])
    means = [sum(X[i][j] for i in range(len(X))) / len(X) for j in range(n_features)]
    stds = []
    for j in range(n_features):
        variance = sum((X[i][j] - means[j]) ** 2 for i in range(len(X))) / len(X)
        stds.append(variance ** 0.5)
    X_scaled = []
    for i in range(len(X)):
        row = [(X[i][j] - means[j]) / stds[j] if stds[j] > 0 else 0 for j in range(n_features)]
        X_scaled.append(row)
    return X_scaled, means, stds


y_mean_val = sum(y_multi) / len(y_multi)
y_std_val = (sum((yi - y_mean_val) ** 2 for yi in y_multi) / len(y_multi)) ** 0.5
y_scaled = [(yi - y_mean_val) / y_std_val for yi in y_multi]

X_scaled, x_means, x_stds = standardize(X_multi)

print("\n=== Multiple Linear Regression (3 features) ===")
print("Features: house size, bedrooms, age")
multi_model = MultipleLinearRegression(n_features=3, learning_rate=0.01)
multi_model.fit(X_scaled, y_scaled, epochs=1000, print_every=200)

print(f"\nWeights (standardized): {[round(w, 4) for w in multi_model.weights]}")
print(f"Bias (standardized): {multi_model.bias:.4f}")
print(f"R-squared: {multi_model.r_squared(X_scaled, y_scaled):.4f}")
```

### 第 5 步：多项式回归

```python
class PolynomialRegression:
    def __init__(self, degree, learning_rate=0.01):
        self.degree = degree
        self.weights = [0.0] * degree
        self.bias = 0.0
        self.lr = learning_rate

    def make_features(self, X):
        return [[x ** (d + 1) for d in range(self.degree)] for x in X]

    def predict(self, X):
        features = self.make_features(X)
        return [sum(w * f for w, f in zip(self.weights, row)) + self.bias for row in features]

    def fit(self, X, y, epochs=1000, print_every=200):
        features = self.make_features(X)
        n = len(y)
        for epoch in range(epochs):
            predictions = [sum(w * f for w, f in zip(self.weights, row)) + self.bias for row in features]
            errors = [pred - actual for pred, actual in zip(predictions, y)]
            for j in range(self.degree):
                grad = (2 / n) * sum(errors[i] * features[i][j] for i in range(n))
                self.weights[j] -= self.lr * grad
            grad_b = (2 / n) * sum(errors)
            self.bias -= self.lr * grad_b
            if epoch % print_every == 0:
                cost = sum(e ** 2 for e in errors) / n
                print(f"  Epoch {epoch:4d} | Cost: {cost:.6f}")
        return self

    def r_squared(self, X, y):
        predictions = self.predict(X)
        y_mean = sum(y) / len(y)
        ss_res = sum((actual - pred) ** 2 for actual, pred in zip(y, predictions))
        ss_tot = sum((actual - y_mean) ** 2 for actual in y)
        return 1 - (ss_res / ss_tot)


random.seed(42)
X_poly = [x / 10.0 for x in range(0, 50)]
y_poly = [0.5 * x ** 2 - 2 * x + 3 + random.gauss(0, 1.0) for x in X_poly]

x_max = max(abs(x) for x in X_poly)
X_poly_norm = [x / x_max for x in X_poly]
y_poly_mean = sum(y_poly) / len(y_poly)
y_poly_std = (sum((yi - y_poly_mean) ** 2 for yi in y_poly) / len(y_poly)) ** 0.5
y_poly_norm = [(yi - y_poly_mean) / y_poly_std for yi in y_poly]

print("\n=== Polynomial Regression (degree 2 vs degree 5) ===")
print("True relationship: y = 0.5x^2 - 2x + 3")

print("\nDegree 2:")
poly2 = PolynomialRegression(degree=2, learning_rate=0.1)
poly2.fit(X_poly_norm, y_poly_norm, epochs=2000, print_every=500)
print(f"  R-squared: {poly2.r_squared(X_poly_norm, y_poly_norm):.4f}")

print("\nDegree 5:")
poly5 = PolynomialRegression(degree=5, learning_rate=0.1)
poly5.fit(X_poly_norm, y_poly_norm, epochs=2000, print_every=500)
print(f"  R-squared: {poly5.r_squared(X_poly_norm, y_poly_norm):.4f}")

print("\nDegree 2 fits the true curve well. Degree 5 fits training data slightly better")
print("but risks overfitting on new data.")
```

### 第 6 步：Ridge 回归（L2 正则化）

```python
class RidgeRegression:
    def __init__(self, n_features, learning_rate=0.01, alpha=1.0):
        self.weights = [0.0] * n_features
        self.bias = 0.0
        self.lr = learning_rate
        self.alpha = alpha

    def predict_single(self, x):
        return sum(w * xi for w, xi in zip(self.weights, x)) + self.bias

    def predict(self, X):
        return [self.predict_single(x) for x in X]

    def fit(self, X, y, epochs=1000, print_every=200):
        n = len(y)
        n_features = len(X[0])
        for epoch in range(epochs):
            predictions = self.predict(X)
            errors = [pred - actual for pred, actual in zip(predictions, y)]
            mse = sum(e ** 2 for e in errors) / n
            reg_term = self.alpha * sum(w ** 2 for w in self.weights)
            cost = mse + reg_term
            for j in range(n_features):
                grad = (2 / n) * sum(errors[i] * X[i][j] for i in range(n))
                grad += 2 * self.alpha * self.weights[j]
                self.weights[j] -= self.lr * grad
            grad_b = (2 / n) * sum(errors)
            self.bias -= self.lr * grad_b
            if epoch % print_every == 0:
                print(f"  Epoch {epoch:4d} | Cost: {cost:.4f} | L2 penalty: {reg_term:.4f}")
        return self


print("\n=== Ridge Regression (L2 Regularization) ===")
print("Same data as multiple regression, with alpha=0.1")
ridge = RidgeRegression(n_features=3, learning_rate=0.01, alpha=0.1)
ridge.fit(X_scaled, y_scaled, epochs=1000, print_every=200)
print(f"\nRidge weights: {[round(w, 4) for w in ridge.weights]}")
print(f"Plain weights: {[round(w, 4) for w in multi_model.weights]}")
print("Ridge weights are smaller (shrunk toward zero) due to the L2 penalty.")
```

## Use It

现在用 scikit-learn 做同样的事——生产环境里你实际会用这个。

```python
from sklearn.linear_model import LinearRegression as SklearnLR
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np

np.random.seed(42)
X_sk = np.random.uniform(0, 10, (100, 1))
y_sk = 3.0 * X_sk.squeeze() + 7.0 + np.random.normal(0, 2.0, 100)

X_train, X_test, y_train, y_test = train_test_split(X_sk, y_sk, test_size=0.2, random_state=42)

lr = SklearnLR()
lr.fit(X_train, y_train)
y_pred = lr.predict(X_test)

print("=== Scikit-learn Linear Regression ===")
print(f"Coefficient (w): {lr.coef_[0]:.4f}")
print(f"Intercept (b): {lr.intercept_:.4f}")
print(f"R-squared (test): {r2_score(y_test, y_pred):.4f}")
print(f"MSE (test): {mean_squared_error(y_test, y_pred):.4f}")

poly = PolynomialFeatures(degree=2, include_bias=False)
X_poly_sk = poly.fit_transform(X_train)
X_poly_test = poly.transform(X_test)

lr_poly = SklearnLR()
lr_poly.fit(X_poly_sk, y_train)
print(f"\nPolynomial degree 2 R-squared: {r2_score(y_test, lr_poly.predict(X_poly_test)):.4f}")

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

ridge = Ridge(alpha=1.0)
ridge.fit(X_train_scaled, y_train)
print(f"Ridge R-squared: {r2_score(y_test, ridge.predict(X_test_scaled)):.4f}")
print(f"Ridge coefficient: {ridge.coef_[0]:.4f}")
```

你从零实现的版本和 scikit-learn 产生同样的结果。区别在于 scikit-learn 处理了边界情况、数值稳定性和性能优化。生产环境用库，从零实现用来理解发生了什么。

## Ship It

本课产出：

- `outputs/skill-regression.md` — 根据问题选择合适回归方法的 skill

## Exercises

1. 实现批量梯度下降、随机梯度下降（SGD）和小批量梯度下降。在同一数据集上比较收敛速度。哪个收敛最快？哪个的损失曲线最平滑？
2. 从三次函数（y = ax³ + bx² + cx + d + 噪声）生成数据。拟合 1、3、10 次多项式。比较训练 R² 和测试 R²。在多少次时过拟合变得明显？
3. 实现 Lasso 回归（L1 正则化：惩罚项 = alpha \* sum(|w\_i|)）。在多特征房价数据上训练。对比哪些权重变成零 vs Ridge。为什么 L1 产生稀疏解而 L2 不会？

## Key Terms

| 术语                    | 人们常说                              | 实际含义                                                |
| --------------------- | --------------------------------- | --------------------------------------------------- |
| Linear regression     | "Draw a line through data"        | 找到权重 w 和偏置 b，最小化 wx+b 与实际 y 值之间的平方差之和               |
| Cost function         | "How bad the model is"            | 把模型参数映射到单个数字来衡量预测误差的函数，优化过程试图最小化它                   |
| Mean squared error    | "Average of squared errors"       | (1/n) \* sum of (predicted - actual)²，对大错误给予不成比例的惩罚 |
| Gradient descent      | "Walk downhill"                   | 用偏导数迭代地沿减小损失函数的方向调整参数                               |
| Learning rate         | "Step size"                       | 控制每次梯度下降步骤参数变化量的标量                                  |
| Normal equation       | "Solve it directly"               | 闭式解 w = (X^T X)^-1 X^T y，不给迭代就给出最优权重                |
| R-squared             | "How good the fit is"             | 模型解释的 y 方差比例，范围从负无穷到 1.0                            |
| Feature scaling       | "Make features comparable"        | 把特征变换到相近范围（比如零均值、单位方差），使梯度下降收敛更快                    |
| Regularization        | "Penalize complexity"             | 在损失函数上加一个缩小权重的项，防止过拟合                               |
| Ridge regression      | "L2 regularization"               | 在 MSE 上加 lambda \* sum(w\_i²) 惩罚的线性回归               |
| Polynomial regression | "Fitting curves with linear math" | 在多项式特征（x, x², x³, …）上做的线性回归，对权重仍然是线性的               |
| Overfitting           | "Memorizing training data"        | 使用过于复杂的模型，把训练数据里的噪声也拟合了，新数据上失败                      |

## Further Reading

- [An Introduction to Statistical Learning (ISLR)](https://www.statlearning.com/) — 免费 PDF，第 3 章和第 6 章讲线性回归和正则化，附实用 R 例子
- [The Elements of Statistical Learning (ESL)](https://hastie.su.domains/ElemStatLearn/) — 免费 PDF，ISLR 更数学化的伴侣，更深入地讲了 ridge 和 lasso
- [Stanford CS229 Lecture Notes on Linear Regression](https://cs229.stanford.edu/main_notes.pdf) — Andrew Ng 的笔记，从第一性原理推导正规方程和梯度下降
- [scikit-learn LinearRegression documentation](https://scikit-learn.org/stable/modules/linear_model.html) — LinearRegression、Ridge、Lasso、ElasticNet 的实用参考，附代码例子

