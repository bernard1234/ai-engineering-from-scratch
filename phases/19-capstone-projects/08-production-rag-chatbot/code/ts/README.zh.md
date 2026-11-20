# Capstone 08 - Production RAG Chatbot（TypeScript）

聊天 UI 骨架，通过 Server-Sent
Events 流式返回以引用为锚的响应。它与 `../main.py` 中的 Python 流水线配套。会话状态存于
一个以 `sessionId` 为键的进程内 Map，因此同一个 session id 可以驱动
多轮对话。

## 布局

```text
ts/
  package.json
  tsconfig.json
  src/
    index.ts        # entrypoint, demo + HTTP server
    server.ts      # hono app, /, /chat/stream (SSE), /sessions, /health
    session.ts     # SessionStore (Map<sessionId, Session>)
    stream.ts      # SSE frame encoder + parser + mock retrieval + tokenizer
    types.ts        # Session, Turn, Citation, KbEntry, SseEvent
  tests/
    session.test.ts
    stream.test.ts
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

交互式服务器在 `PORT` 未设置时选一个空闲端口，把聊天
HTML 客户端挂到 `/`，并通过 `GET /chat/stream?sessionId=...&q=...` 流式传输。演示
客户端使用 `EventSource`，监听 `session`、`citations`、`token`
和 `done` 事件。

## 测试

通过 tsx 运行的 `node --test`。覆盖范围：

- SessionStore：创建、查找、追加、列举，缺失 id 时无操作。
- SSE 编码器 + 解析器往返；按管辖标签提升检索；
  tokenizer 兜底 +“See also”尾巴。
- Server：`/`、`/health`、`/chat/stream` 的 happy path（session + citations +
  token + done）、缺少 q 时返回 400、多轮会话持久化、
  `/sessions` 列举。
