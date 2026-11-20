---
name: skill-production-checklist
description: 将 LLM 应用交付上生产时的决策框架——覆盖每个组件，并给出具体阈值与通过/失败判定标准
version: 1.0.0
phase: 11
lesson: 13
tags: [production, deployment, llm, architecture, scaling, cost, observability, guardrails]
---

# 生产级 LLM 检查清单

交付 LLM 应用时，按顺序走完这份检查清单。每一节都给出带具体阈值的通过/失败判定标准。

## 1. Security（发版阻断项）

这里每一项都必须在任何部署之前通过。

| 检查项 | 通过标准 | 验证方式 |
|-------|--------------|---------------|
| API key 放在环境变量中 | 代码库中零硬编码 key | `grep -r "sk-" --include="*.py"` 返回空 |
| 输入 guardrails 生效 | prompt injection 模式被阻断 | 发送 "Ignore all previous instructions" —— 返回被阻断的响应 |
| PII 脱敏 | SSN、信用卡、邮箱模式被捕获 | 发送 "My SSN is 123-45-6789" —— 调用 LLM 前完成 PII 脱敏 |
| 输出过滤 | 危险内容被阻断 | 模型无法返回 `DROP TABLE`、`rm -rf`、`exec()` 这类模式 |
| 限流 | 按用户执行请求上限 | 同一用户在 10 秒内发 100 个请求 —— 后 50+ 个被拒绝 |
| 所有 endpoint 都有鉴权 | 不存在未鉴权的 LLM 访问 | 不带 token 执行 `curl /v1/chat` 返回 401 |
| 限制 CORS | 仅允许生产域 | `Origin: evil.com` 的请求被拒绝 |
| 最大输入 token 限制 | 超限请求被拒绝 | 发送 50K token 输入 —— 返回 413 或截断 |

## 2. Reliability（首周存活）

这些检查能避免你第一次 on-call 事故。

| 检查项 | 通过标准 | 验证方式 |
|-------|--------------|---------------|
| 带退避的重试 | 5xx 重试 3 次，指数退避 | 在请求中途杀掉 LLM mock —— 日志中可看到重试 |
| 兜底模型链 | 链中至少 2 个模型 | 主模型不可用 —— 响应仍从兜底模型返回 |
| 请求超时 | 所有外部调用最多 30s | 慢速 LLM mock（60s）—— 请求在 30s 时超时 |
| 优雅降级 | cache/RAG 故障不会让服务崩溃 | 停掉 cache —— 请求仍然成功（更慢、更贵） |
| 健康检查 endpoint | 返回依赖状态 | `GET /health` 返回 `{"status": "healthy", "cache": ..., "llm": ...}` |
| 流式输出可用 | 首个 token 在 500ms 内 | 测量 time-to-first-token，稳定 < 500ms |
| 错误信息安全 | 内部错误绝不泄露给用户 | 强制 500 —— 用户看到通用错误，而非 stack trace |

## 3. Cost Control（首月经济性）

这些检查能避免那张 $50K 的意外账单。

| 检查项 | 通过标准 | 验证方式 |
|-------|--------------|---------------|
| 每请求成本追踪 | 每个请求记录 token 数 + 美元成本 | 请求日志包含 `input_tokens`、`output_tokens`、`cost_usd` 字段 |
| 语义 cache 生效 | 重复模式命中率 > 20% | 跑完 1000 个测试请求后，cache 统计显示命中率 |
| cache TTL 已配置 | 条目会过期（默认：1 小时） | 插入条目 —— TTL 后不再返回 |
| 按用户成本追踪 | 成本按 user_id 聚合 | dashboard/API 显示成本最高的 10 个用户 |
| 成本告警 | 日预算用到 80% 时告警 | 设 $10 日预算，发 $8.50 的请求 —— 告警触发 |
| 按成本做模型路由 | 低复杂度查询走更便宜的模型 | 简单问题路由到 gpt-4o-mini，复杂问题路由到 gpt-4o |
| 设置最大输出 token | 每个 template 的响应有上限 | max_output_tokens=512 的 template —— 响应绝不超过它 |

**成本估算公式：**
```
Monthly LLM cost = DAU x queries_per_user x 30 x (1 - cache_hit_rate) x (avg_input_tokens x input_price + avg_output_tokens x output_price) / 1,000,000
```

**按规模给出的基准阈值：**

| DAU | 每请求目标成本 | 月度预算 |
|-----|-------------------|----------------|
| 1K | < $0.005 | < $750 |
| 10K | < $0.003 | < $4,500 |
| 100K | < $0.001 | < $15,000 |

## 4. Observability（生产环境调试）

你无法修复你看不见的东西。

| 检查项 | 通过标准 | 验证方式 |
|-------|--------------|---------------|
| 结构化 JSON 日志 | 每个请求产生一行 JSON 日志 | 日志包含：request_id、user_id、model、tokens、latency_ms、cost |
| 请求追踪 | 端到端 trace，含各组件耗时 | 单个请求显示：guardrail（5ms）+ cache（2ms）+ llm（3200ms）+ eval（1ms） |
| 延迟追踪 | 测量 P50、P95、P99 | 1000 个请求后：P50 < 2s，P99 < 10s |
| 错误率监控 | 错误被计数并分类 | dashboard 显示：0.5% API 错误、0.1% guardrail 阻断、0.01% 超时 |
| cache 指标 | 命中率、未命中率、条目数可见 | `GET /v1/cache/stats` 返回当前数字 |
| A/B 测试指标 | 每个变体的质量指标被记录 | 每个请求记录 prompt_template + version 以便对比 |
| eval 日志 | 每个请求记录质量信号 | 响应长度、延迟、模型、template 版本被存储以供离线分析 |

## 5. Prompt 管理

Prompt 就是代码。像对待代码一样对待它们。

| 检查项 | 通过标准 | 验证方式 |
|-------|--------------|---------------|
| 带版本的 template | 每个 template 都有 name + version 字符串 | template 变更产生新版本，旧版本保留 |
| 支持 A/B 测试 | 按确定性用户哈希分流 | 同一用户在同一实验内总看到同一变体 |
| 可回滚 | 1 分钟内回退到上一版本 | 改实验配置 —— 流量立刻切换 |
| template 校验 | 渲染前校验变量 | template 缺变量时抛出清晰错误，而不是 KeyError |
| system prompt 分离 | system 与 user 消息放在不同字段 | system prompt 不被拼接进 user 消息 |

## 6. 扩展就绪度

上线时不需要。10 倍流量时需要。

| 检查项 | 通过标准 | 验证方式 |
|-------|--------------|---------------|
| 异步 LLM 调用 | API 调用不阻塞线程 | 50 个并发请求 —— 服务器 CPU 保持 < 30% |
| 连接池 | HTTP 连接被复用 | 网络 trace 显示到 LLM 提供商的持久连接 |
| 水平扩展 | 无状态服务器设计 | 负载均衡后 2 个实例 —— 所有请求成功 |
| 队列支持 | 非实时任务进队列 | 摘要请求返回 job_id，结果可通过轮询获取 |
| 已做负载测试 | 100 并发用户，错误率 < 5% | `wrk` 或 `locust` 测试在目标并发下通过 |

## 新项目的实现顺序

1. **第 1 天：** API server + prompt template + 带重试的单次 LLM 调用
2. **第 2 天：** 输入 guardrails + 输出 guardrails + 错误处理
3. **第 3 天：** 语义 cache + 每请求成本追踪
4. **第 4 天：** 流式（SSE）+ 健康检查 endpoint
5. **第 5 天：** 结构化日志 + 请求追踪 + eval 日志
6. **第 2 周：** A/B 测试 + prompt 版本管理 + 回滚
7. **第 3 周：** 兜底模型链 + 优雅降级
8. **第 4 周：** 负载测试 + 异步优化 + 水平扩展

## 快速诊断

生产环境出问题时，按这个顺序检查：

1. **用户反馈报错？** 先查健康检查 endpoint，再查日志里的错误率，最后查 LLM 提供商状态页
2. **响应慢？** 先查 P99 延迟，再查 cache 命中率，最后查 trace 里 LLM 的响应时间
3. **成本飙升？** 先查每请求成本趋势，再查 cache 命中率，再查按成本排序的头部用户，最后找有没有增大 token 数的 prompt template 变更
4. **质量下降？** 查是否部署了新的 prompt 版本，查 RAG 检索准确率是否变化，查模型提供商是否改了默认模型版本
5. **安全事故？** 查 guardrail 阻断率（骤降 = guardrails 被关闭），查请求日志里的异常模式，立刻轮换 API key
