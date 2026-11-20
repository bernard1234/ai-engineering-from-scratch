# 第 16 课 - GitHub Issue-to-PR Agent（TypeScript webhook 接收端）

本 capstone 的 TypeScript 部分。Python 侧交付 agent 循环与
dispatcher；YAML 侧交付 Actions workflow。本项目是 GitHub
App 的 webhook 接收端：对原始请求体做 HMAC 校验、按事件类型路由、为
`issues.opened` 分发一个 stub agent。

## 目录结构

```text
src/
  index.ts    entry: demo (default) or HTTP server (--serve)
  server.ts   Hono webhook receiver (POST /webhook)
  verify.ts   X-Hub-Signature-256 HMAC, timing-safe
  router.ts   event-type routing (ping, issues, pull_request)
  agent.ts    stub agent + audit log
  types.ts    payload + audit shapes
tests/
  verify.test.ts  signature pass, tampered, router pathing
```

## 运行

```bash
npm install
npm run typecheck
npm test
npm start            # self-terminating demo (in-process replays)
npm run serve        # HTTP server on :8081
```

HMAC 密钥从 `GH_WEBHOOK_SECRET` 读取（demo 下默认
为 `demo-shared-secret`）。
