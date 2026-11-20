---
name: skill-release-gate
description: 在发布前评估 Agent Skill 包的结构完整性、触发质量、工件改进、脚本正确性、安全性、已安装树的完整性以及目标宿主的可移植性。
license: MIT
metadata:
  lesson: "27"
---

# Skill 发布门禁

在发布或分发 Agent Skill 目录包之前使用这个 skill。

## 流程

1. 把 `SKILL_ROOT` 解析为包含这份已安装 `SKILL.md` 的绝对目录。不要假设进程的 cwd 就是已安装的包。
2. 从原始工作区工作目录解析 `TARGET_ROOT`，并把用户提供的候选目录解析为绝对路径 `TARGET_BUNDLE`。
3. 从 `SKILL_ROOT` 读取 `references/eval-contract.md`。
4. 检查 `TARGET_BUNDLE` 下 `evals/cases.json` 中的正例与近似命中触发用例。
5. 检查 `TARGET_BUNDLE` 下 `evals/artifacts.json` 中共享的 baseline 与带 skill 的断言。
6. 检查 `TARGET_BUNDLE` 下 `evals/evidence.json` 中显式的脚本与安全结果。
7. 检查 `TARGET_BUNDLE` 下 `assets/hosts.json` 中声明的运行时能力，并对照其 `assets/manifest.json` 校验目标文件的哈希。
8. 用于生产时，把确定性的预测、工件、证据和宿主能力替换为采集到的结果；设置全部四个 captured 模式；并把每一条原始触发观测、两个工件、完整证据集以及非空的宿主矩阵绑定到非空来源和相匹配的 SHA-256 provenance 摘要。这些本地检查可以设置 `localEvidenceReady`，但可在本地重算的哈希不能证明采集发生过。
9. 获取一份外部 JSON attestation，其 `evidenceRoot` 与报告相匹配，并从独立的可信策略或发布通道获取其确切字节的 SHA-256。该 attestation 必须是目标包之外的一个普通文件。
10. 在执行之前，展示确切解析出的 argv。已安装的评估器是 `SKILL_ROOT` 下的 `scripts/evaluate_skill.py`。对随课程交付的教具 fixture，用 `python3`、该评估器的绝对路径、`--fixture-demo` 和绝对的 `TARGET_BUNDLE` 构建 argv。用于生产时，使用同一个已安装脚本，配合 `--attestation`、`--trusted-attestation-sha256` 和绝对的 `TARGET_BUNDLE`，不带 `--fixture-demo`。
11. 返回 `checksPassed`、`fixturePassed`、`localEvidenceReady`、`trustAnchorValid`、`productionReady` 和 `passed`，并附上 evidence root、评估模式、失败的检查、precision、recall、每一条原始触发观测、逐用例的重复运行通过率、工件对比、脚本与安全证据、已安装树校验以及可移植性矩阵。同时包含解析出的脚本路径、解析出的目标路径、cwd、确切的 argv 和退出码。把无法获得的观测标记为待验证。

## 输出契约

返回完整的 JSON 评估报告。保留每一项按层划分的检查及其证据，使一个通过的聚合结果无法掩盖路由、工件、脚本、安全、已安装树或可移植性方面的失败。`fixturePassed` 报告的是教具 fixture 成功。`localEvidenceReady` 只报告本地摘要完整性。只有当 `productionReady` 同时拥有一份有效的包外 trust anchor 时，`passed` 才为 true。

## 失败行为

如果配置无效、provenance 缺失或不匹配、可信 attestation 缺失或无效、某个文件哈希不同、某项必需能力缺失，或任何生产门禁失败，就以非零结果停止，并报告失败的那一层。显式的 `--fixture-demo` 路径只有在 `fixturePassed` 为 true 时才可能成功退出，并且它永远不会做出发布声明。绝不要自动发布、安装到别处、修复证据、创建信任决策或放宽阈值。

不要仅仅因为 SKILL.md 能被解析，或一个正例 prompt 能激活它，就发布一个包。当目标宿主丢弃必需的伴生文件，或忽略必需的 runtime extensions 时，不要把该包标注为可移植。
