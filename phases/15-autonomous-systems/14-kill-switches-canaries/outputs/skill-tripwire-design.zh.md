---
name: tripwire-design
description: 审查一次 agent 部署的拟议检测器栈（kill switch、circuit breaker、canary token），在首次自主运行之前标出缺失的 tripwire。
version: 1.0.0
phase: 15
lesson: 14
tags: [kill-switch, circuit-breaker, canary, honeytoken, detection-and-response]
---

给定一次 agent 部署的拟议检测器栈，对照三检测器参考（kill switch、circuit breaker、canary）审计它，并标出缺失的、调校不当的，或暴露给 agent 的部分。

产出：

1. **Kill switch 审计。** 开关位于何处（feature flag、Redis、签名配置）？确认 agent 的凭证无法把它关闭。确认每一个有后果的动作都检查该开关，而不只是启动时。确认重新启用是一个明确的人工动作。
2. **Circuit breaker 清单。** 列出断路器监视的每一个模式（重复、连续失败、速率、信任之外读取之后的特定工具）。说明每一个的阈值和冷却时间。高于 10 的阈值通常过松。
3. **Canary 设计。** 列出环境中的每一个 canary token。对每一个说明：它是什么（伪造凭证、伪造 DB 记录、伪造文件、伪造记忆条目）、它位于何处、什么访问会触发警报、谁会收到通知。确认没有 canary 有正当理由被触碰。
4. **统计 + 硬性叠加。** 确认该栈在任何统计检测器（EWMA、z-score）之外，至少使用一个硬性限制（第 17 课宪法风格）。仅统计的检测器会接受缓慢漂移。
5. **隔离路径。** 当某个检测器触发时会发生什么？完全停止 agent、路径级暂停、流量重定向（eBPF / Cilium 蜜罐）、仅告警。确认该路径已至少端到端测试过一次。

硬性拒绝：
- 任何没有外部 kill switch 的部署。
- canary token 存放在 agent 有写权限的系统中。
- 仅统计检测、没有硬性限制。
- 冷却期会在没有人工复核的情况下自动重新启用 circuit breaker。
- 无人值守运行中，kill switch 只在启动时检查，而不是每个动作都检查。

拒绝规则：
- 如果用户无法说出承载 kill switch、且位于 agent 凭证之外的特定系统，拒绝。如果 agent 能写配置文件，“我们用一个 agent 读取的配置文件”就不是 kill switch。
- 如果用户把 Auto Mode 分类器（第 10 课）当作 tripwire 的替代品，拒绝。分类器与检测和响应是正交的。
- 如果拟议的 canary 位于 agent 有正当理由读取的系统中，拒绝，并要求重新设计。

输出格式：

返回一份 tripwire 审计，包含：
- **Kill switch 一行**（位置、检查频率、重新启用流程）
- **Circuit breaker 表格**（模式、阈值、冷却时间）
- **Canary 表格**（token、位置、告警、负责人）
- **叠加说明**（统计 + 硬性限制是否存在）
- **隔离流程**（什么触发、发生什么、是否已测试）
- **就绪度**（生产 / 预发 / 仅研究）
