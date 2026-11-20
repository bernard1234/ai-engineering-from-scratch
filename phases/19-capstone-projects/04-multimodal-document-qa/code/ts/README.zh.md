# Capstone 04 - 多模态文档问答（TypeScript）

viewer 骨架：针对某个文档返回页面图像 URL，以及被引用 bounding box 的 JSON 列表。
HTML 响应内联一小段 canvas 叠加脚本，
在页面图像之上绘制被引用区域。与 `../main.py` 中的 Python
流水线配套使用。

## 目录结构

```text
ts/
  package.json
  tsconfig.json
  src/
    index.ts        # entrypoint, demo + HTTP server
    server.ts       # hono app, /health, /, /document/:id
    fixtures.ts     # 10-K table + Nature figure fixtures
    render.ts       # HTML index + per-document overlay renderer
    types.ts        # DocumentFixture, EvidenceRegion, BoundingBox
  tests/
    fixtures.test.ts
    render.test.ts
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

交互式服务器在 `PORT` 未设置时挑选一个空闲端口，并在 stdout 打印
选中的 URL。访问 `/` 查看索引，访问 `/document/10k-acme-2025` 查看
演示叠加层，或设置 `accept: application/json` 以获得结构化响应。

## 测试

由 tsx 驱动的 `node --test` runner。测试覆盖 fixture 查找（正例与反例）、
五个敌意字符的 HTML 转义、文档 HTML 载荷结构，
以及 hono 路由（200、404、内容协商）。
