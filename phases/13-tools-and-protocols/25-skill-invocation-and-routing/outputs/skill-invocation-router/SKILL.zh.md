---
name: skill-invocation-router
description: 为 Agent Skill catalog 设计与测试显式人类调用、隐式模型或 agent 调用、程序化应用调用、有界的 skill 组合调用以及 harness 激活策略。
license: MIT
metadata:
  lesson: "25"
---

# Skill 调用路由器

当宿主需要的是一套可审计的激活策略、而非一个不加区分的 `invocable` 开关时，使用这个 skill。

1. 阅读 `references/invocation-model.md`，并判断所请求的通道。
2. 把 `assets/host-policy.json` 当作示例适配器配置来看待，而不是一份可移植标准。
3. 运行 `python3 scripts/simulate_invocation.py --policy assets/host-policy.json --actor ACTOR --name NAME --description DESCRIPTION --query QUERY [--explicit-name NAME] [--caller-name NAME] [--depth N] [--user-invocable true|false] [--disable-model-invocation true|false]`。
4. 对于 human、application、skill 或 harness 请求，要求一个确切已发现的名称，以及该通道专属的 allowlist。
5. 对于 skill 调用方，还要要求调用方身份、非循环的目标，以及有界的组合深度。
6. 对于 model 或 autonomous agent 请求，移除那些因发起方或已识别的宿主扩展而不合格的候选。
7. 只对剩余的描述打分。选择最合格的匹配；当没有合格候选越过阈值时弃权。
8. 返回带有 adapter、channel、score 和策略原因的 JSON 决策。

激活（activation）只加载指令。它不批准工具、文件系统变更、网络访问、密钥使用或打包的脚本。
