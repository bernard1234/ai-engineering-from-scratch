---
name: computer-use-safety
description: 为 computer-use agent 构建逐步安全分类器 + 确认门，带允许清单导航与注入标记过滤。
version: 1.0.0
phase: 14
lesson: 21
tags: [computer-use, safety, claude, openai-cua, gemini]
---

给定一个 computer-use agent 和一列目标应用，产出在每次动作执行前对其进行分类的安全层。

产出：

1. `SafetyClassifier.assess(action, screen) -> SafetyVerdict`，带字段 `allow`、`reason`、`needs_confirmation`。
2. agent 可点击元素标签的允许清单；否则拒绝。
3. agent 可导航到的 URL 允许清单；重定向出清单即拒绝。
4. 对 DOM 文本、检索内容和输入文本的注入标记过滤。任何匹配即拦截动作。
5. 敏感动作（登录、购买、删除、发布）的确认门。人工介入回调接口。
6. trace 发射器：每个决策都记录（action、verdict、reason）。

硬性拒绝：

- 只在第一个动作上运行的安全分类器。每个动作都必须被分类。
- 形如 `*` 的允许清单。一个允许一切的允许清单不是允许清单。
- 因为模型「看起来很有信心」而跳过确认。信心不等于安全。

拒绝规则：

- 如果 agent 在没有逐步安全的情况下拥有 computer-use 访问权限，拒绝交付。
- 如果 agent 可以导航到任意 URL，拒绝。要求允许清单或阻止清单。
- 如果敏感动作在任何模式下绕过确认门，拒绝。

输出：`classifier.py`、`allowlist.py`、`confirmation.py`、`trace.py`、`README.md`，说明门策略、注入标记和允许清单维护流程。结尾以「接下来读什么」指向第 27 课（prompt 注入）和第 23 课（安全决策的 OTel span 归属）。
