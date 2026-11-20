# Capstone 06 - DevOps Troubleshooting Agent（TypeScript）

`../main.py` 中当班 agent 的 Slack 集成骨架。它暴露一个
slash command 端点和一个交互（按钮点击）端点，两者都由
Slack 的 HMAC-SHA256 请求签名加 5 分钟重放窗口把关。
破坏性修复只在 Slack 卡片获批后才运行。

## 布局

```text
ts/
  package.json
  tsconfig.json
  src/
    index.ts          # entrypoint, demo + HTTP server
    server.ts         # hono app, /slack/command + /slack/interactivity
    slack_verify.ts   # HMAC v0 verification + timing-safe compare
    agent.ts          # mocked hypothesis ranker
    blocks.ts         # Block Kit response builder
    types.ts          # Hypothesis, AgentReport, SlackResponse, OutboundCall
  tests/
    slack_verify.test.ts
    agent.test.ts
    server.test.ts
```

## 运行

```bash
npm install
npm run typecheck
npm test
npm start          # one self-check pass, exits 0
npm run serve      # interactive HTTP server on 127.0.0.1:<port>
```

设置 `SLACK_SIGNING_SECRET=...` 可覆盖占位密钥。交互式
服务器会打印所选端口（`PORT` 未设置时随机）。

## 测试

通过 tsx 运行的 `node --test`。覆盖范围：

- Slack 签名校验：有效签名通过，被篡改的签名被
  拒绝，过期时间戳（>5 分钟偏差）被拒绝，非数字时间戳被
  拒绝，长度不匹配路径在常量时间比较之前被触发。
- Mock agent：OOM 关键字路径、CrashLoop 关键字路径、兜底路径。
- Server：`/health`、`/slack/command` 的 happy/tampered/stale 路径、
  `/slack/interactivity` 的 approve 动作。
