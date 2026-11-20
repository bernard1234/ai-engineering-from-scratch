# 评估契约

一个发布候选版本只有在所有必需面都通过时才通过：

- 结构：在读取配置之前，一次物理目录树预检会拒绝符号链接的根目录、父目录或条目，缺失的必需普通文件，以及特殊文件。随后目录名与 frontmatter 的 name 匹配，必需的元数据存在，runtime extensions 被显式声明，直接 references 可解析，包大小与类型限制通过，不存在明显的密钥模式，输出契约与失败契约存在，并且没有未被引用的伴生文件随包发布。
- 触发：正例 prompt 会激活，近似命中的负例保持不激活。报告混淆计数、precision、recall 以及每一条原始的单次运行预测。本地完整性把完整的观测序列和路由 fixture 绑定到其来源与 SHA-256 摘要，而不只是第零次运行或聚合率。
- 稳定性：对每个用例重复运行，并报告逐用例的通过率。
- 工件：对 baseline 与带 skill 的输出应用相同的断言。skill 的输出必须通过并体现改进。生产声明会把两个采集到的字符串绑定到其来源与 SHA-256 摘要。
- 脚本：要求来自确定性脚本测试（包括重复执行）的显式通过/失败证据。生产证据会把完整的脚本与安全检查集绑定到采集到的来源与 SHA-256 摘要。
- 安全：要求每一项已声明的权限边界用例都通过。平均值不能掩盖任何一次越界。
- 已安装树：在激活之前，对照记录的文件 manifest 校验干净的已安装副本。要求 `manifestVersion: 1` 与 `algorithm: "sha256"`。把 `assets/manifest.json` 视为保留元数据，并将它排除在自身的 `files` 映射之外；通过可信的外层发布或 registry 通道认证该 manifest。
- 可移植性：说明每个目标宿主是原生支持、需要适配器，还是不受支持。列出缺失的能力。要求至少一个宿主以及一个正向的原生宿主阈值。本地完整性把采集到的需求和宿主矩阵绑定到其探测来源与 SHA-256 摘要。

把路由 eval 与确定性的 harness 激活区分开。前者度量可发现性；后者隔离工作流与工件行为。

随课程交付的 JSON 取值是用于学习门禁的确定性 fixtures。它们可以设置 `fixturePassed`，但永远不能设置 `productionReady` 或 `passed`。对真实发布，把 `evaluationMode` 设为 `captured-observations`，把 `artifactMode` 设为 `captured-artifacts`，把 `evidenceMode` 设为 `captured-results`，把 `hostMode` 设为 `captured-capabilities`；为每次运行记录一个布尔预测，并把完整的观测集绑定到其来源与 SHA-256 摘要；用从同一任务和同一环境采集到的工件替换 baseline 与带 skill 的字符串；记录非空的采集来源与相匹配的 SHA-256 工件摘要；把每一项证据结论替换为采集到的测试结果；把完整的证据集绑定到其来源与 SHA-256 摘要；把模拟的能力矩阵替换为采集到的宿主探测结果，并把它绑定到其来源与摘要；重建 manifest；安装到一个干净的目标位置。

这些本地检查可以设置 `localEvidenceReady`。它们不能证明采集发生过，因为包作者可以重新标注 fixtures 并重算每一个摘要。因此评估器会对完整的五配置 evidence root 做哈希，并要求一个绑定它的外部 `attestationVersion: 1` JSON 对象。从包之外提供该 attestation，并通过 `--trusted-attestation-sha256` 提供其确切字节的 SHA-256，来源必须是带外可信策略。只有六层门禁加上本地完整性再加上这个 trust anchor，才能设置 `productionReady` 与 `passed`。
