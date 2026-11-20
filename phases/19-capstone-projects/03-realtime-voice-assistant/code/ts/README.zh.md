# Capstone 19/03 — 实时语音助手（TypeScript）

面向流式语音流水线的多文件 TypeScript web client harness，流水线详见
`../docs/en.md`。离线状态机模拟，外加一个由 `ws` 包支撑的实时
WebSocket 服务器。

## 目录结构

```text
src/
  index.ts        entry point; runs two offline sessions, probes the live ws, exits 0
  server.ts       hono /healthz + ws upgrade via WebSocketServer
  orchestrator.ts IDLE -> LISTENING -> WAITING -> THINKING -> SPEAKING with barge-in
  vad.ts          turn-completion scorer + synthetic 20ms-frame generator
  protocol.ts     zod-validated frame envelope (event / summary)
  types.ts        AudioChunk, Metrics, SessionOptions, SessionSummary
tests/
  vad.test.ts
  orchestrator.test.ts
  protocol.test.ts
```

## 运行

```bash
npm install
npm start                # runs two offline sessions + ws self-probe, exits 0
npm start -- --serve     # keep ws server up; ctrl-c to stop
npm test                 # node --test runner via tsx
npm run typecheck        # tsc --noEmit
```

非交互的 `npm start` 路径会断言干净会话到达
`first_audio_out`，barge-in 会话至少登记一次 barge-in 事件，
且实时 WebSocket 探测在关闭前收到一个 `summary` 帧。
