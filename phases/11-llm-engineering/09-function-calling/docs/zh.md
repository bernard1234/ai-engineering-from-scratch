# Function Calling 与 Tool Use

> LLM 什么都做不了。它们生成文本。这就是全部能力。它们不能查天气、查数据库、发邮件、跑代码或读文件。你见过的每一个「AI agent」，都是一个 LLM 在生成 JSON，说明该调用哪个函数 —— 然后由你的代码真正去调用。模型是大脑。Tool 是双手。Function calling 是连接两者的神经系统。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 11 Lesson 03 (Structured Outputs)
**Time:** ~75 分钟
**Related:** Phase 11 · 14（Model Context Protocol）—— 当一个 tool 需要在多个 host 之间共享时，就从内联 function calling 升级到 MCP server。本课讲内联情形；MCP 讲协议情形。

## Learning Objectives

- 实现一个 function calling 循环：定义 tool schema，解析模型返回的 tool-call JSON，执行函数，再返回结果
- 设计描述清晰、参数带类型的 tool schema，让模型能可靠地调用
- 构建一个多轮 agent 循环，串起多次函数调用以回答复杂查询
- 处理 function calling 的边界情况：并行 tool 调用、错误传播，以及防止无限的 tool 循环

## 问题场景

你做了一个聊天机器人。用户问：「东京现在的天气怎么样？」

模型回答：「我无法访问实时天气数据，但根据季节判断，东京现在大概在 15 摄氏度左右……」

那是一句披着免责声明的幻觉。模型不知道天气。它永远也不会知道。天气每小时都在变。模型的训练数据是几个月前的。

正确答案需要调用 OpenWeatherMap API，拿到当前温度，返回真实数字。模型不能调 API。你的代码能。缺的那块拼图是：一套结构化协议，让模型能说「我需要用这些参数调用天气 API」，让你的代码去执行，再把结果喂回去。

这就是 function calling。模型输出结构化 JSON，描述要调用哪个函数、用什么参数。你的应用执行该函数。结果回到对话里。模型用这个结果产出最终答案。

没有 function calling，LLM 是百科全书。有了它，LLM 变成 agent。

## 核心概念

### Function Calling 循环

每一次 tool 使用交互都遵循同样的 5 步循环。

```mermaid
sequenceDiagram
    participant U as 用户
    participant A as 应用
    participant M as 模型
    participant T as Tool

    U->>A: "东京的天气怎么样？"
    A->>M: messages + tool 定义
    M->>A: tool_call: get_weather(city="Tokyo")
    A->>T: 执行 get_weather("Tokyo")
    T->>A: {"temp": 18, "condition": "cloudy"}
    A->>M: tool_result + 对话
    M->>A: "东京 18 摄氏度，多云。"
    A->>U: 最终回复
```

第 1 步：用户发消息。第 2 步：模型收到消息，同时收到 tool 定义（描述可用函数的 JSON Schema）。第 3 步：模型不返回文本，而是输出一个 tool call —— 一个带函数名和参数的结构化 JSON 对象。第 4 步：你的代码执行函数并捕获结果。第 5 步：结果回到模型，模型现在有真实数据来产出最终答案。

模型从不执行任何东西。它只决定调用什么、用什么参数。你的代码是执行者。

### Tool 定义：JSON Schema 契约

每个 tool 由一个 JSON Schema 定义，告诉模型这个函数做什么、接受什么参数、参数必须是什么类型。

```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Get current weather for a city. Returns temperature in Celsius and conditions.",
    "parameters": {
      "type": "object",
      "properties": {
        "city": {
          "type": "string",
          "description": "City name, e.g. 'Tokyo' or 'San Francisco'"
        },
        "units": {
          "type": "string",
          "enum": ["celsius", "fahrenheit"],
          "description": "Temperature units"
        }
      },
      "required": ["city"]
    }
  }
}
```

`description` 字段至关重要。模型通过读它们来决定何时以及如何使用这个 tool。像「gets weather」这样含糊的描述，选出来的 tool 会比「Get current weather for a city. Returns temperature in Celsius and conditions.」差。description 就是写给 tool 选择用的 prompt。

### 各家 Provider 对比

每一家主流 provider 都支持 function calling，但 API 表面各不相同。

| Provider | API 参数 | Tool 调用格式 | 并行调用 | 强制调用 |
|----------|--------------|-----------------|---------------|----------------|
| OpenAI（GPT-5、o4） | `tools` | `tool_calls[].function` | 是（每轮多个） | `tool_choice="required"` |
| Anthropic（Claude 4.6/4.7） | `tools` | `content[].type="tool_use"` | 是（多个 block） | `tool_choice={"type":"any"}` |
| Google（Gemini 3） | `function_declarations` | `functionCall` | 是 | `function_calling_config` |
| Open-weight（Llama 4、Qwen3、DeepSeek-V3） | Llama 4 原生 `tools`；其他模型用 Hermes 或 ChatML | 混合 | 取决于模型 | 基于 prompt，或（若支持）`tool_choice` |

到 2026 年，三家闭源 provider 已经收敛到几乎相同的、基于 JSON-Schema 的格式。Llama 4 自带与 OpenAI 形状一致的 `tools` 字段。开放权重的微调模型仍然各有差异 —— Hermes 格式（NousResearch）是第三方微调模型里最常见的。对于需要跨 host 共享的 tool，优先用 MCP（Phase 11 · 14）而不是内联 function calling —— server 对所有 host 都是同一个。

### Tool Choice：Auto、Required、Specific

你可以控制模型何时使用 tool。

**Auto**（默认）：模型自己决定是调用 tool 还是直接回答。「What's 2+2?」—— 直接回答。「What's the weather?」—— 调用 tool。

**Required**：模型必须至少调用一个 tool。当你确切知道用户意图需要 tool 时用它。这能防止模型去猜，而不是去查真实数据。

**Specific function**：强制模型调用某个特定函数。`tool_choice={"type":"function", "function": {"name": "get_weather"}}` 保证天气 tool 被调用，无论查询是什么。用它来做路由 —— 当上游逻辑已经决定了需要哪个 tool 时。

### 并行 Function Calling

GPT-4o 和 Claude 都能在一轮里调用多个函数。用户问：「What's the weather in Tokyo and New York?」模型同时输出两个 tool call：

```json
[
  {"name": "get_weather", "arguments": {"city": "Tokyo"}},
  {"name": "get_weather", "arguments": {"city": "New York"}}
]
```

你的代码执行这两个调用（最好并发执行），返回两个结果，模型把它们综合成一个回复。这把往返次数从 2 次降到 1 次。对于每次查询要做 5-10 次 tool 调用的 agent，并行调用能把延迟降低 60-80%。

### Structured Outputs 与 Function Calling 的区别

第 03 课讲过 structured outputs。Function calling 用的是同一套 JSON Schema 机制，但目的不同。

**Structured outputs**：强制模型以特定形状产出数据。输出就是最终产物。例如：从文本中提取产品信息为 `{name, price, in_stock}`。

**Function calling**：模型声明执行某个动作的意图。输出是一个中间步骤。例如：`get_weather(city="Tokyo")` —— 模型是在请求一个动作，而不是在产出最终答案。

想要数据抽取时用 structured outputs。想让模型与外部系统交互时用 function calling。

### 安全：不可妥协的规则

Function calling 是你能给 LLM 的最危险的能力。模型选择执行什么。如果你的 tool 集包含数据库查询，模型就构造这些查询。如果包含 shell 命令，模型就写这些命令。

**规则 1：绝不要把模型生成的 SQL 直接传给数据库。** 模型会、也确实会生成 DROP TABLE、UNION 注入，或者返回每一行的查询。永远参数化。永远校验。永远使用操作白名单。

**规则 2：给函数做白名单。** 模型只能调用你显式定义的函数。绝不要构建一个通用的「按名字执行任意函数」tool。如果你有 50 个内部函数，只暴露用户需要的 5 个。

**规则 3：校验参数。** 模型可能传来一个城市名 `"; DROP TABLE users; --"`。执行前要按预期类型、范围和格式校验每一个参数。

**规则 4：清洗 tool 结果。** 如果某个 tool 返回敏感数据（API key、PII、内部错误），在把它发回模型之前过滤掉。模型会把 tool 结果原样写进回复。

**规则 5：限制 tool 调用速率。** 处于循环中的模型可能调用 tool 数百次。设置一个上限（每次对话 10-20 次是合理的）。打断无限循环。

### 错误处理

Tool 会失败。API 会超时。数据库会挂。文件不存在。模型需要知道 tool 什么时候失败、为什么失败。

把错误作为结构化的 tool 结果返回，而不是抛异常：

```json
{
  "error": true,
  "message": "City 'Toky' not found. Did you mean 'Tokyo'?",
  "code": "CITY_NOT_FOUND"
}
```

模型读到它，调整参数，重试。模型很擅长从结构化错误信息中自我纠正。它们不擅长从空响应或笼统的「something went wrong」错误中恢复。

### MCP：Model Context Protocol

MCP 是 Anthropic 提出的 tool 互操作开放标准。与其每个应用都定义自己的 tool，MCP 提供了一套通用协议：tool 由 MCP server 提供，由 MCP client（比如 Claude Code、Cursor 或你的应用）消费。

一个 MCP server 可以把 tool 暴露给任何兼容的 client。一个 Postgres MCP server 让任何兼容 MCP 的 agent 获得数据库访问能力。一个 GitHub MCP server 让任何 agent 获得仓库访问能力。Tool 定义一次，到处使用。

MCP 之于 function calling，就像 HTTP 之于网络。它把传输层标准化，让 tool 变得可移植。

```figure
mx-tool-call-loop
```

## Build It

### 第 1 步：定义 Tool 注册表

构建一个注册表，存放 tool 定义及其实现。每个 tool 有一个 JSON Schema 定义（模型看到的东西）和一个 Python 函数（你的代码执行的东西）。

```python
import ast
import json
import math
import time
import hashlib


TOOL_REGISTRY = {}


def register_tool(name, description, parameters, function):
    TOOL_REGISTRY[name] = {
        "definition": {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        },
        "function": function,
    }
```

### 第 2 步：实现 5 个 Tool

构建一个计算器、天气查询、网页搜索模拟器、文件读取器，以及代码运行器。

```python
def calculator(expression, precision=2):
    allowed = set("0123456789+-*/.() ")
    if not all(c in allowed for c in expression):
        return {"error": True, "message": f"Invalid characters in expression: {expression}"}
    try:
        result = eval(expression, {"__builtins__": {}}, {"math": math})
        return {"result": round(float(result), precision), "expression": expression}
    except Exception as e:
        return {"error": True, "message": str(e)}


WEATHER_DB = {
    "tokyo": {"temp_c": 18, "condition": "cloudy", "humidity": 72, "wind_kph": 14},
    "new york": {"temp_c": 22, "condition": "sunny", "humidity": 45, "wind_kph": 8},
    "london": {"temp_c": 12, "condition": "rainy", "humidity": 88, "wind_kph": 22},
    "san francisco": {"temp_c": 16, "condition": "foggy", "humidity": 80, "wind_kph": 18},
    "sydney": {"temp_c": 25, "condition": "sunny", "humidity": 55, "wind_kph": 10},
}


def get_weather(city, units="celsius"):
    key = city.lower().strip()
    if key not in WEATHER_DB:
        suggestions = [c for c in WEATHER_DB if c.startswith(key[:3])]
        return {
            "error": True,
            "message": f"City '{city}' not found.",
            "suggestions": suggestions,
            "code": "CITY_NOT_FOUND",
        }
    data = WEATHER_DB[key].copy()
    if units == "fahrenheit":
        data["temp_f"] = round(data["temp_c"] * 9 / 5 + 32, 1)
        del data["temp_c"]
    data["city"] = city
    return data


SEARCH_DB = {
    "python function calling": [
        {"title": "OpenAI Function Calling Guide", "url": "https://platform.openai.com/docs/guides/function-calling", "snippet": "Learn how to connect LLMs to external tools."},
        {"title": "Anthropic Tool Use", "url": "https://docs.anthropic.com/en/docs/tool-use", "snippet": "Claude can interact with external tools and APIs."},
    ],
    "MCP protocol": [
        {"title": "Model Context Protocol", "url": "https://modelcontextprotocol.io", "snippet": "An open standard for connecting AI models to data sources."},
    ],
    "weather API": [
        {"title": "OpenWeatherMap API", "url": "https://openweathermap.org/api", "snippet": "Free weather API with current, forecast, and historical data."},
    ],
}


def web_search(query, max_results=3):
    key = query.lower().strip()
    for db_key, results in SEARCH_DB.items():
        if db_key in key or key in db_key:
            return {"query": query, "results": results[:max_results], "total": len(results)}
    return {"query": query, "results": [], "total": 0}


FILE_SYSTEM = {
    "data/config.json": '{"model": "gpt-4o", "temperature": 0.7, "max_tokens": 4096}',
    "data/users.csv": "name,email,role\nAlice,alice@example.com,admin\nBob,bob@example.com,user",
    "README.md": "# My Project\nA tool-use agent built from scratch.",
}


def read_file(path):
    if ".." in path or path.startswith("/"):
        return {"error": True, "message": "Path traversal not allowed.", "code": "FORBIDDEN"}
    if path not in FILE_SYSTEM:
        available = list(FILE_SYSTEM.keys())
        return {"error": True, "message": f"File '{path}' not found.", "available_files": available, "code": "NOT_FOUND"}
    content = FILE_SYSTEM[path]
    return {"path": path, "content": content, "size_bytes": len(content), "lines": content.count("\n") + 1}


def run_code(code, language="python"):
    if language != "python":
        return {"error": True, "message": f"Language '{language}' not supported. Only 'python' is available."}
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"error": True, "message": f"SyntaxError: {e}", "code": "SYNTAX_ERROR"}
    unsafe_names = {"exec", "eval", "compile", "__import__", "open", "globals", "locals", "vars", "getattr", "setattr", "delattr"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return {"error": True, "message": "Forbidden operation: import is not allowed", "code": "SECURITY_VIOLATION"}
        if isinstance(node, ast.Attribute) and node.attr.startswith("__") and node.attr.endswith("__"):
            return {"error": True, "message": "Forbidden operation: dunder attribute access is not allowed", "code": "SECURITY_VIOLATION"}
        if isinstance(node, ast.Name) and node.id in unsafe_names:
            return {"error": True, "message": f"Forbidden operation: {node.id} is not allowed", "code": "SECURITY_VIOLATION"}
    try:
        local_vars = {}
        exec(code, {"__builtins__": {"print": print, "range": range, "len": len, "str": str, "int": int, "float": float, "list": list, "dict": dict, "sum": sum, "min": min, "max": max, "abs": abs, "round": round, "sorted": sorted, "enumerate": enumerate, "zip": zip, "map": map, "filter": filter, "math": math}}, local_vars)
        result = local_vars.get("result", None)
        return {"success": True, "result": result, "variables": {k: str(v) for k, v in local_vars.items() if not k.startswith("_")}}
    except Exception as e:
        return {"error": True, "message": f"{type(e).__name__}: {e}"}
```

子串黑名单把代码当文本读，所以任何字符串匹配没有逐字写出的东西都会被漏掉。把代码解析成语法树再遍历，就能让这道防线按结构、而不是按拼写来拒绝 `import` 语句、dunder 属性访问（那条通向真实解释器的 `__class__` 与 `__globals__` 链条），以及不安全的 builtin 名字。即便如此，也要把它当作教学用的过滤器，而不是真实的边界。任何进程内守卫都与它运行的代码共享同一个解释器，有心的调用者仍然能找到可达对象。生产系统在独立进程或容器里运行不可信代码（降权后的子进程、gVisor、Firecracker，或托管代码运行器），一旦逃逸，攻击者落进的也是一个一次性盒子，而不是你的服务。

### 第 3 步：注册所有 Tool

```python
def register_all_tools():
    register_tool(
        "calculator", "Evaluate a mathematical expression. Supports +, -, *, /, parentheses, and decimals. Returns the numeric result.",
        {"type": "object", "properties": {"expression": {"type": "string", "description": "Math expression, e.g. '(10 + 5) * 3'"}, "precision": {"type": "integer", "description": "Decimal places in result", "default": 2}}, "required": ["expression"]},
        calculator,
    )
    register_tool(
        "get_weather", "Get current weather for a city. Returns temperature, condition, humidity, and wind speed.",
        {"type": "object", "properties": {"city": {"type": "string", "description": "City name, e.g. 'Tokyo' or 'San Francisco'"}, "units": {"type": "string", "enum": ["celsius", "fahrenheit"], "description": "Temperature units, defaults to celsius"}}, "required": ["city"]},
        get_weather,
    )
    register_tool(
        "web_search", "Search the web for information. Returns a list of results with title, URL, and snippet.",
        {"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}, "max_results": {"type": "integer", "description": "Maximum results to return", "default": 3}}, "required": ["query"]},
        web_search,
    )
    register_tool(
        "read_file", "Read the contents of a file. Returns the file content, size, and line count.",
        {"type": "object", "properties": {"path": {"type": "string", "description": "Relative file path, e.g. 'data/config.json'"}}, "required": ["path"]},
        read_file,
    )
    register_tool(
        "run_code", "Run a small Python snippet behind a static-analysis guard and a restricted interpreter. This is a teaching filter, not real isolation. Set a 'result' variable to return output.",
        {"type": "object", "properties": {"code": {"type": "string", "description": "Python code to execute"}, "language": {"type": "string", "enum": ["python"], "description": "Programming language"}}, "required": ["code"]},
        run_code,
    )
```

### 第 4 步：构建 Function Calling 循环

这是核心引擎。它模拟模型决定调用哪个 tool，执行该 tool，再把结果喂回去。

```python
def simulate_model_decision(user_message, tools, conversation_history):
    msg = user_message.lower()

    if any(word in msg for word in ["weather", "temperature", "forecast"]):
        cities = []
        for city in WEATHER_DB:
            if city in msg:
                cities.append(city)
        if not cities:
            for word in msg.split():
                if word.capitalize() in [c.title() for c in WEATHER_DB]:
                    cities.append(word)
        if not cities:
            cities = ["tokyo"]
        calls = []
        for city in cities:
            calls.append({"name": "get_weather", "arguments": {"city": city.title()}})
        return calls

    if any(word in msg for word in ["calculate", "compute", "math", "what is", "how much"]):
        for token in msg.split():
            if any(c in token for c in "+-*/"):
                return [{"name": "calculator", "arguments": {"expression": token}}]
        if "+" in msg or "-" in msg or "*" in msg or "/" in msg:
            expr = "".join(c for c in msg if c in "0123456789+-*/.() ")
            if expr.strip():
                return [{"name": "calculator", "arguments": {"expression": expr.strip()}}]
        return [{"name": "calculator", "arguments": {"expression": "0"}}]

    if any(word in msg for word in ["search", "find", "look up", "google"]):
        query = msg.replace("search for", "").replace("look up", "").replace("find", "").strip()
        return [{"name": "web_search", "arguments": {"query": query}}]

    if any(word in msg for word in ["read", "file", "open", "cat", "show"]):
        for path in FILE_SYSTEM:
            if path.split("/")[-1].split(".")[0] in msg:
                return [{"name": "read_file", "arguments": {"path": path}}]
        return [{"name": "read_file", "arguments": {"path": "README.md"}}]

    if any(word in msg for word in ["run", "execute", "code", "python"]):
        return [{"name": "run_code", "arguments": {"code": "result = 'Hello from the sandbox!'", "language": "python"}}]

    return []


def execute_tool_call(tool_call):
    name = tool_call["name"]
    args = tool_call["arguments"]

    if name not in TOOL_REGISTRY:
        return {"error": True, "message": f"Unknown tool: {name}", "code": "UNKNOWN_TOOL"}

    tool = TOOL_REGISTRY[name]
    func = tool["function"]
    start = time.time()

    try:
        result = func(**args)
    except TypeError as e:
        result = {"error": True, "message": f"Invalid arguments: {e}"}

    elapsed_ms = round((time.time() - start) * 1000, 2)
    return {"tool": name, "result": result, "execution_time_ms": elapsed_ms}


def run_function_calling_loop(user_message, max_iterations=5):
    conversation = [{"role": "user", "content": user_message}]
    tool_definitions = [t["definition"] for t in TOOL_REGISTRY.values()]
    all_tool_results = []

    for iteration in range(max_iterations):
        tool_calls = simulate_model_decision(user_message, tool_definitions, conversation)

        if not tool_calls:
            break

        results = []
        for call in tool_calls:
            result = execute_tool_call(call)
            results.append(result)

        conversation.append({"role": "assistant", "content": None, "tool_calls": tool_calls})

        for result in results:
            conversation.append({"role": "tool", "content": json.dumps(result["result"]), "tool_name": result["tool"]})

        all_tool_results.extend(results)
        break

    return {"conversation": conversation, "tool_results": all_tool_results, "iterations": iteration + 1 if tool_calls else 0}
```

### 第 5 步：参数校验

构建一个校验器，在执行前按 JSON Schema 检查 tool call 的参数。

```python
def validate_tool_arguments(tool_name, arguments):
    if tool_name not in TOOL_REGISTRY:
        return [f"Unknown tool: {tool_name}"]

    schema = TOOL_REGISTRY[tool_name]["definition"]["function"]["parameters"]
    errors = []

    if not isinstance(arguments, dict):
        return [f"Arguments must be an object, got {type(arguments).__name__}"]

    for required_field in schema.get("required", []):
        if required_field not in arguments:
            errors.append(f"Missing required argument: {required_field}")

    properties = schema.get("properties", {})
    for arg_name, arg_value in arguments.items():
        if arg_name not in properties:
            errors.append(f"Unknown argument: {arg_name}")
            continue

        prop_schema = properties[arg_name]
        expected_type = prop_schema.get("type")

        type_checks = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict}
        if expected_type in type_checks:
            if not isinstance(arg_value, type_checks[expected_type]):
                errors.append(f"Argument '{arg_name}': expected {expected_type}, got {type(arg_value).__name__}")

        if "enum" in prop_schema and arg_value not in prop_schema["enum"]:
            errors.append(f"Argument '{arg_name}': '{arg_value}' not in {prop_schema['enum']}")

    return errors
```

### 第 6 步：运行 demo

```python
def run_demo():
    register_all_tools()

    print("=" * 60)
    print("  Function Calling & Tool Use Demo")
    print("=" * 60)

    print("\n--- Registered Tools ---")
    for name, tool in TOOL_REGISTRY.items():
        desc = tool["definition"]["function"]["description"][:60]
        params = list(tool["definition"]["function"]["parameters"].get("properties", {}).keys())
        print(f"  {name}: {desc}...")
        print(f"    params: {params}")

    print(f"\n--- Argument Validation ---")
    validation_tests = [
        ("get_weather", {"city": "Tokyo"}, "Valid call"),
        ("get_weather", {}, "Missing required arg"),
        ("get_weather", {"city": "Tokyo", "units": "kelvin"}, "Invalid enum value"),
        ("calculator", {"expression": 123}, "Wrong type (int for string)"),
        ("unknown_tool", {"x": 1}, "Unknown tool"),
    ]
    for tool_name, args, label in validation_tests:
        errors = validate_tool_arguments(tool_name, args)
        status = "VALID" if not errors else f"ERRORS: {errors}"
        print(f"  {label}: {status}")

    print(f"\n--- Tool Execution ---")
    direct_tests = [
        {"name": "calculator", "arguments": {"expression": "(10 + 5) * 3 / 2"}},
        {"name": "get_weather", "arguments": {"city": "Tokyo"}},
        {"name": "get_weather", "arguments": {"city": "Mars"}},
        {"name": "web_search", "arguments": {"query": "python function calling"}},
        {"name": "read_file", "arguments": {"path": "data/config.json"}},
        {"name": "read_file", "arguments": {"path": "../etc/passwd"}},
        {"name": "run_code", "arguments": {"code": "result = sum(range(1, 101))"}},
        {"name": "run_code", "arguments": {"code": "import os; os.system('rm -rf /')"}},
    ]
    for call in direct_tests:
        result = execute_tool_call(call)
        print(f"\n  {call['name']}({json.dumps(call['arguments'])})")
        print(f"    -> {json.dumps(result['result'], indent=None)[:100]}")
        print(f"    time: {result['execution_time_ms']}ms")

    print(f"\n--- Full Function Calling Loop ---")
    test_queries = [
        "What's the weather in Tokyo?",
        "Calculate (100 + 250) * 0.15",
        "Search for MCP protocol",
        "Read the config file",
        "Run some Python code",
        "Tell me a joke",
    ]
    for query in test_queries:
        print(f"\n  User: {query}")
        result = run_function_calling_loop(query)
        if result["tool_results"]:
            for tr in result["tool_results"]:
                print(f"    Tool: {tr['tool']} ({tr['execution_time_ms']}ms)")
                print(f"    Result: {json.dumps(tr['result'], indent=None)[:90]}")
        else:
            print(f"    [No tool called -- direct response]")
        print(f"    Iterations: {result['iterations']}")

    print(f"\n--- Parallel Tool Calls ---")
    multi_city_query = "What's the weather in tokyo and london?"
    print(f"  User: {multi_city_query}")
    result = run_function_calling_loop(multi_city_query)
    print(f"  Tool calls made: {len(result['tool_results'])}")
    for tr in result["tool_results"]:
        city = tr["result"].get("city", "unknown")
        temp = tr["result"].get("temp_c", "N/A")
        print(f"    {city}: {temp}C, {tr['result'].get('condition', 'N/A')}")

    print(f"\n--- Security Checks ---")
    security_tests = [
        ("read_file", {"path": "../../etc/passwd"}),
        ("run_code", {"code": "import subprocess; subprocess.run(['ls'])"}),
        ("calculator", {"expression": "__import__('os').system('ls')"}),
    ]
    for tool_name, args in security_tests:
        result = execute_tool_call({"name": tool_name, "arguments": args})
        blocked = result["result"].get("error", False)
        print(f"  {tool_name}({list(args.values())[0][:40]}): {'BLOCKED' if blocked else 'ALLOWED'}")
```

## Use It

### OpenAI Function Calling

```python
# from openai import OpenAI
#
# client = OpenAI()
#
# tools = [{
#     "type": "function",
#     "function": {
#         "name": "get_weather",
#         "description": "Get current weather for a city",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "city": {"type": "string"},
#                 "units": {"type": "string", "enum": ["celsius", "fahrenheit"]}
#             },
#             "required": ["city"]
#         }
#     }
# }]
#
# response = client.chat.completions.create(
#     model="gpt-4o",
#     messages=[{"role": "user", "content": "Weather in Tokyo?"}],
#     tools=tools,
#     tool_choice="auto",
# )
#
# tool_call = response.choices[0].message.tool_calls[0]
# args = json.loads(tool_call.function.arguments)
# result = get_weather(**args)
#
# final = client.chat.completions.create(
#     model="gpt-4o",
#     messages=[
#         {"role": "user", "content": "Weather in Tokyo?"},
#         response.choices[0].message,
#         {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)},
#     ],
# )
# print(final.choices[0].message.content)
```

OpenAI 把 tool call 放在 `response.choices[0].message.tool_calls` 里返回。每个调用都有一个 `id`，返回结果时必须带上。模型用这个 ID 把结果与调用对上。GPT-4o 可以在单个响应里返回多个 tool call —— 遍历并全部执行。

### Anthropic Tool Use

```python
# import anthropic
#
# client = anthropic.Anthropic()
#
# response = client.messages.create(
#     model="claude-sonnet-5",
#     max_tokens=1024,
#     tools=[{
#         "name": "get_weather",
#         "description": "Get current weather for a city",
#         "input_schema": {
#             "type": "object",
#             "properties": {
#                 "city": {"type": "string"},
#                 "units": {"type": "string", "enum": ["celsius", "fahrenheit"]}
#             },
#             "required": ["city"]
#         }
#     }],
#     messages=[{"role": "user", "content": "Weather in Tokyo?"}],
# )
#
# tool_block = next(b for b in response.content if b.type == "tool_use")
# result = get_weather(**tool_block.input)
#
# final = client.messages.create(
#     model="claude-sonnet-5",
#     max_tokens=1024,
#     tools=[...],
#     messages=[
#         {"role": "user", "content": "Weather in Tokyo?"},
#         {"role": "assistant", "content": response.content},
#         {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_block.id, "content": json.dumps(result)}]},
#     ],
# )
```

Anthropic 把 tool call 作为 `type: "tool_use"` 的 content block 返回。tool 结果放在一条 `type: "tool_result"` 的 user 消息里。注意关键差异：Anthropic 用 `input_schema` 定义 tool 参数，而 OpenAI 用 `parameters`。

### MCP Integration

```python
# MCP servers expose tools over a standardized protocol.
# Any MCP-compatible client can discover and call these tools.
#
# Example: connecting to a Postgres MCP server
#
# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client
#
# server_params = StdioServerParameters(
#     command="npx",
#     args=["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"],
# )
#
# async with stdio_client(server_params) as (read, write):
#     async with ClientSession(read, write) as session:
#         await session.initialize()
#         tools = await session.list_tools()
#         result = await session.call_tool("query", {"sql": "SELECT count(*) FROM users"})
```

MCP 把 tool 的实现与 tool 的消费解耦。Postgres server 懂 SQL。GitHub server 懂 API。你的 agent 只管发现和调用 tool —— 不需要为每个集成都写 provider 专属代码。

## Ship It

本课产出 `outputs/prompt-tool-designer.md` —— 一个可复用的 prompt 模板，用于设计 tool 定义。给它一段描述，说明你想让 tool 做什么，它就会产出完整的 JSON Schema 定义，包括 description、类型和约束。

它还产出 `outputs/skill-function-calling-patterns.md` —— 一个在生产中实现 function calling 的决策框架，涵盖 tool 设计、错误处理、安全，以及各 provider 专属的模式。

## Exercises

1. **添加第 6 个 tool：数据库查询。** 实现一个带内存表的模拟 SQL tool。该 tool 接受表名和过滤条件（不是原始 SQL）。校验表名在白名单内，且过滤操作符限制为 `=`、`>`、`<`、`>=`、`<=`。把匹配的行以 JSON 返回。

2. **实现带错误反馈的重试。** 当 tool 调用失败时（例如城市未找到），把错误信息喂回模型决策函数，让它修正参数。记录每次调用用了几次重试。每次 tool 调用最多重试 3 次。

3. **构建一个多步 agent。** 有些查询需要串联 tool 调用：「Read the config file and tell me what model is configured, then search the web for that model's pricing.」实现一个循环，持续运行到模型认为不再需要 tool 为止，并把累积的结果传入每一步决策。限制最多 10 次迭代以防无限循环。

4. **衡量 tool 选择准确率。** 创建 30 条带预期 tool 名称的测试查询。在你的决策函数上跑全部 30 条，测量它选中正确 tool 的比例。找出哪些查询最容易让各个 tool 之间产生混淆。

5. **实现 tool 调用缓存。** 如果同一个 tool 在 60 秒内被相同的参数调用，直接返回缓存结果，而不是重新执行。用一个以 `(tool_name, frozenset(args.items()))` 为键的字典。在一个含 20 条查询的对话中测量缓存命中率。

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|----------------------|
| Function calling | 「Tool use」 | 模型输出结构化 JSON，描述要以特定参数调用的函数 —— 执行的是你的代码，不是模型 |
| Tool definition | 「Function schema」 | 一个 JSON Schema 对象，描述 tool 的名称、用途、参数和类型 —— 模型读它来决定何时以及如何使用该 tool |
| Tool choice | 「调用模式」 | 控制模型必须调用 tool（required）、可以调用 tool（auto），还是必须调用某个特定 tool（named） |
| Parallel calling | 「多 tool」 | 模型在单个回合里输出多个 tool call，减少往返 —— GPT-4o 和 Claude 都支持 |
| Tool result | 「函数输出」 | 执行 tool 的返回值，作为一条消息发回模型，让它能在回复中使用真实数据 |
| Argument validation | 「输入检查」 | 在执行 tool 之前，校验模型生成的参数是否符合预期类型、范围和约束 |
| MCP | 「Tool 协议」 | Model Context Protocol —— Anthropic 的开放标准，通过 server 暴露 tool，任何兼容 client 都能发现并调用 |
| Agent loop | 「ReAct loop」 | 模型决定 tool、代码执行 tool、结果回灌，如此迭代，直到模型有足够信息回复 |
| Tool poisoning | 「通过 tool 做 prompt injection」 | 一种攻击：tool 结果中包含操纵模型行为的指令 —— 要清洗所有 tool 输出 |
| Rate limiting | 「调用预算」 | 设定每次对话的 tool 调用上限，防止无限循环和失控的 API 成本 |

## Further Reading

- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling) —— GPT-4o tool use 的权威参考，涵盖并行调用、强制调用和结构化参数
- [Anthropic Tool Use Guide](https://docs.anthropic.com/en/docs/tool-use) —— Claude 的 tool use 实现，含 input_schema、多 tool 响应和 tool_choice 配置
- [Model Context Protocol Specification](https://modelcontextprotocol.io) —— 跨 AI 应用的 tool 互操作开放标准，采用 server/client 架构
- [Schick et al., 2023 -- "Toolformer: Language Models Can Teach Themselves to Use Tools"](https://arxiv.org/abs/2302.04761) —— 训练 LLM 决定何时以及如何调用外部 tool 的基础论文
- [Patil et al., 2023 -- "Gorilla: Large Language Model Connected with Massive APIs"](https://arxiv.org/abs/2305.15334) —— 微调 LLM 在 1,645 个 API 上做准确调用，并降低幻觉
- [Berkeley Function Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html) —— 实时 benchmark，对比 GPT-4o、Claude、Gemini 和开放模型上的 function calling 准确率
- [Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models" (ICLR 2023)](https://arxiv.org/abs/2210.03629) —— Thought-Action-Observation 循环，即每次 tool 调用外围的 agent 外层循环；本课到此为止，Phase 14 从这里接上。
- [Anthropic — Building effective agents (Dec 2024)](https://www.anthropic.com/research/building-effective-agents) —— 五种可组合模式（prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer），全部建立在单一的 tool-use 原语之上。
