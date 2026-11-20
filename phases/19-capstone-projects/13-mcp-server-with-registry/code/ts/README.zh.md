# 第 13 课 - 无状态 MCP Server（TypeScript）

capstone 的 TypeScript 部分。Python 侧（`code/main.py`）交付
注册表与策略门；本项目是 MCP 传输层：在 stdio 上手写的
换行分隔 JSON-RPC 2.0，带三个 mock 事故工具。它
直接实现 MCP `2026-07-28`，不依赖 `@modelcontextprotocol/sdk`，
因此你可以检查线路上的每一个字节。

协议是无状态的，尽管 mock 事故存储会持久化数据。
每个请求都在 `params._meta` 中重复其协议版本与客户端
capabilities；没有任何连接、进程或更早的请求会建立
会话。server 暴露必需的 `server/discover`，在每个成功结果中标明
自身身份，并发布确定性、可缓存的 tool 列表。
`tools/call` 依据 `tools/list` 返回的同一套有界 schema
校验参数；已知 tool 的畸形参数会返回一个完整的 tool 结果，
带 `isError: true`，且永远不会到达其执行器。

运行时身份是 `com.example/internal-incidents`。它使用已认证
`example.com` 发布者的反向 DNS 命名空间。一份匹配的已发布
`server.json` 必须使用同一个名字，即使本地 npm 包有其
自己的私有项目名。

## Layout

```text
src/
  index.ts      entry: fixture demo (default) or stdio loop (--serve)
  transport.ts  stdin readline + fixture replay
  protocol.ts   request validation / server/discover / tools/list / tools/call
  tools.ts      three incident tools + executors
  types.ts      JSON-RPC + tool shapes
tests/
  protocol.test.ts  stateless metadata, discovery, tools, errors, roundtrip
```

## Run

```bash
npm install
npm run typecheck
npm test
npm start            # self-terminating fixture demo
npm run serve        # real stdio loop (waits on stdin)
```

演示是自终止的。真正的 stdio server 会一直存活，直到其输入
流关闭；没有 MCP shutdown 请求或初始化握手。
