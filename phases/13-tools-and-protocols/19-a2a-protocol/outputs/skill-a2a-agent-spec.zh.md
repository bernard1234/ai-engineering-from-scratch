---
name: a2a-agent-spec
description: 为需要通过 A2A 被调用的 agent 产出 Agent Card 与 skills schema。
version: 1.0.0
phase: 13
lesson: 18
tags: [a2a, agent-card, task-lifecycle, delegation]
---

给定 agent 的能力与预期的协作者，产出它的 A2A Agent Card 与 skill 定义。

产出：

1. Agent Card。`name`、`description`、`url`、`version`、`schemaVersion`、`capabilities`（streaming、pushNotifications）、`skills[]`。
2. Skills 列表。每项包含 `id`、`name`、`description`、`inputModes`、`outputModes`。在 description 中使用 “Use when X. Do not use for Y.” 模式。
3. Task 状态方案。对每个 skill，给出预期的状态转换以及 input_required 路径。
4. 签名方案。是否通过 AP2 对 card 签名（对外部可调用的 agent 推荐这样做）。
5. Transport。基于 HTTP 的 JSON-RPC（默认）或 gRPC。说明与 v1.0 的向后兼容情况。

硬性拒绝：
- 任何没有稳定 URL 的 Agent Card。这会破坏 discovery。
- 任何未声明 input 与 output modes 的 skill。调用方无法判断兼容性。
- 任何外部可调用但没有 AP2 签名方案的 agent。这是冒充风险面。

拒绝规则：
- 如果 agent 的用例只是单次 tool 调用，拒绝搭建 A2A 骨架；推荐 MCP。
- 如果 agent 暴露了不该暴露的内部信息（tool 调用轨迹、思维链），拒绝并要求保持不透明性。
- 如果 agent 需要用 A2A 处理支付（AP2 用例），确认 AP2 扩展版本，并指出 AP2 独立于核心 A2A。

输出：一页 Agent Card JSON、每个操作的 skills schema、状态转换方案、签名与 transport 选择。结尾给出该 agent 承诺的最小 v1.0 向后兼容保证。
