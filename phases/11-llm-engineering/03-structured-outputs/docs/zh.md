# Structured Outputs：JSON、Schema 校验、Constrained Decoding

> 你的 LLM 返回一个字符串，你的应用需要 JSON。这个落差拖垮的生产系统比任何模型幻觉都多。structured output 是自然语言与类型化数据之间的桥。做对了，你的 LLM 就变成一个可靠的 API；做错了，你就在凌晨 3 点用正则解析自由文本。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 10, Lessons 01-05 (LLMs from Scratch)
**Time:** ~90 分钟
**Related:** Phase 5 · 20（Structured Outputs & Constrained Decoding）讲 decoder 层的理论（FSM/CFG logit processor、Outlines、XGrammar）。本课聚焦生产中的 SDK 界面（OpenAI `response_format`、Anthropic tool use、Instructor）——想理解 API 之下发生了什么，请先读 Phase 5 · 20。

## Learning Objectives

- 用 OpenAI 和 Anthropic 的 API 参数实现 JSON mode 与 schema 约束的输出
- 构建一个 Pydantic 校验层，拒绝格式错误的 LLM 输出，并带着错误反馈重试
- 解释 constrained decoding 如何在 token 层面强制合法 JSON，而无需后处理
- 设计健壮的抽取 prompt，可靠地把非结构化文本转成类型化的数据结构

## 问题场景

你问 LLM："Extract the product name, price, and availability from this text."。它回答：

```
The product is the Sony WH-1000XM5 headphones, which cost $348.00 and are currently in stock.
```

这是一个完全正确的答案。对你的应用来说也完全没用。你的库存系统需要 `{"product": "Sony WH-1000XM5", "price": 348.00, "in_stock": true}`。你需要一个带特定键、特定类型、特定值约束的 JSON 对象。你不需要一个句子。

朴素的做法：在 prompt 里加一句"Respond in JSON"。90% 的情况下有效。另外 10% 里，模型会把 JSON 包在 markdown 代码围栏里，或者加一段"Here's the JSON:" 这样的开场白，或者因为提前闭合了括号而产出语法非法的 JSON。你的 JSON parser 崩了。流水线断了。你加上 try/except 和重试循环。重试有时产出不同的数据。现在你除了解析问题，又多了个一致性问题。

这不是 prompt engineering 的问题，而是解码的问题。模型从左到右生成 token。在每个位置，它从 10 万+ 的词汇表里挑最可能的下一个 token。这些候选中大多数在任意给定位置都会产出非法 JSON。如果模型刚发出 `{"price":`，下一个 token 必须是数字、引号（用于字符串）、`null`、`true`、`false` 或负号。其他任何东西都会产出非法 JSON。没有约束时，模型可能挑一个在英文上完全合理、在语法上却灾难性错误的词。

## 核心概念

### Structured output 的四级光谱

结构化输出控制有四个层级，一级比一级可靠。

```mermaid
graph LR
    subgraph Spectrum["Structured Output 光谱"]
        direction LR
        A["基于 prompt\n'返回 JSON'\n约 90% 合法"] --> B["JSON Mode\n保证合法 JSON\n不保证 schema"]
        B --> C["Schema Mode\nJSON + 匹配 schema\n保证合规"]
        C --> D["Constrained Decoding\nToken 级强制\n100% 合规"]
    end

    style A fill:#1a1a2e,stroke:#ff6b6b,color:#fff
    style B fill:#1a1a2e,stroke:#ffa500,color:#fff
    style C fill:#1a1a2e,stroke:#51cf66,color:#fff
    style D fill:#1a1a2e,stroke:#0f3460,color:#fff
```

**基于 prompt**（"Respond in valid JSON"）：没有强制。模型通常会照做，但有时不会。可靠性：约 90%。失效形式：markdown 围栏、开场白文本、输出被截断、结构错误。

**JSON mode**：API 保证输出是合法 JSON。OpenAI 的 `response_format: { type: "json_object" }` 开启它。输出能被无错解析。但它可能不符合你期望的 schema——多余的键、错误的类型、缺失的字段。

**Schema mode**：API 接收一个 JSON Schema 并保证输出符合它。到 2026 年，每个主流供应商都原生支持：OpenAI 的 `response_format: { type: "json_schema", json_schema: {...} }`（也支持 `tool_choice="required"`），Anthropic 的 tool use 配 `input_schema`，以及 Gemini 的 `response_schema` + `response_mime_type: "application/json"`。输出具有你指定的确切键、类型和约束。

**Constrained decoding**：在生成过程中的每个 token 位置，decoder 把所有会产出非法输出的 token 屏蔽掉。如果 schema 要求一个数字而模型即将发出一个字母，那个 token 的概率会被置为零。模型只能产出通向合法输出的 token。OpenAI 的 structured output 模式以及 Outlines、Guidance 这类库，底层实现的就是这个。

### JSON Schema：契约语言

JSON Schema 是你告诉模型（或校验层）输出必须具备什么形状的方式。每个主流结构化输出系统都使用它。

```json
{
  "type": "object",
  "properties": {
    "product": { "type": "string" },
    "price": { "type": "number", "minimum": 0 },
    "in_stock": { "type": "boolean" },
    "categories": {
      "type": "array",
      "items": { "type": "string" }
    }
  },
  "required": ["product", "price", "in_stock"]
}
```

这个 schema 说的是：输出必须是一个对象，包含字符串 `product`、非负数字 `price`、布尔 `in_stock`，以及一个可选的字符串数组 `categories`。任何不符合的输出都会被拒绝。

Schema 能处理难的情况：嵌套对象、带类型元素的数组、enum（把字符串限定在特定取值）、模式匹配（对字符串做正则），以及组合子（oneOf、anyOf、allOf，用于多态输出）。

### Pydantic 模式

在 Python 里，你不用手写 JSON Schema。你定义一个 Pydantic 模型，它会为你生成 schema。

```python
from pydantic import BaseModel

class Product(BaseModel):
    product: str
    price: float
    in_stock: bool
    categories: list[str] = []
```

它产出的 JSON Schema 与上面相同。Instructor 库（以及 OpenAI 的 SDK）直接接受 Pydantic 模型：传入模型类，拿回一个校验过的实例。如果 LLM 输出不匹配，Instructor 会自动重试。

### Function calling / Tool use

同一个问题的另一种接口。你不直接要求模型产出 JSON，而是定义带类型化参数的"工具"（函数）。模型输出一个带结构化参数的函数调用。OpenAI 称之为 "function calling"，Anthropic 称之为 "tool use"。结果是一样的：结构化数据。

```mermaid
graph TD
    subgraph ToolUse["Tool Use 流程"]
        U["用户：从这段评论文本\n抽取产品信息"] --> M["模型处理输入"]
        M --> TC["工具调用：\nextract_product(\n  product='Sony WH-1000XM5',\n  price=348.00,\n  in_stock=true\n)"]
        TC --> V["按函数 schema\n进行校验"]
        V --> R["结构化结果：\n{product, price, in_stock}"]
    end

    style U fill:#1a1a2e,stroke:#0f3460,color:#fff
    style TC fill:#1a1a2e,stroke:#e94560,color:#fff
    style V fill:#1a1a2e,stroke:#ffa500,color:#fff
    style R fill:#1a1a2e,stroke:#51cf66,color:#fff
```

当模型需要选择调用哪个函数、而不只是填参数时，应优先用 tool use。如果你有 10 个不同的抽取 schema，模型必须根据输入挑对的那一个，tool use 同时给你 schema 选择和结构化输出。

### 常见失效模式

即便有 schema 强制，structured output 仍可能在微妙的地方失败。

**幻觉值**：输出符合 schema，但内容凭空捏造。文本里写着 $348，模型却产出 `{"price": 299.99}`。schema 校验抓不到这个——类型正确，值错误。

**Enum 混淆**：你把某个字段限定为 `["in_stock", "out_of_stock", "preorder"]`。模型却输出 `"available"`——语义上正确，但不在允许集合里。好的 constrained decoding 能防止这一点，基于 prompt 的做法不能。

**嵌套对象深度**：深层嵌套的 schema（4 层以上）会产生更多错误。每多一层嵌套，都是模型可能跟丢结构的一个地方。

**数组长度**：模型可能在数组里产出过多或过少的元素。schema 支持 `minItems` 和 `maxItems`，但不是所有供应商都在解码层面强制执行。

**可选字段遗漏**：模型会省略那些技术上可选、但对你的用例在语义上很重要的字段。把它们在 schema 里设为 required，即便数据有时确实缺失——迫使模型显式产出 `null`。

```figure
mx-schema-funnel
```

## Build It

### 第 1 步：JSON Schema 校验器

从零构建一个校验器，检查一个 Python 对象是否符合某个 JSON Schema。这就是在输出侧验证合规性的东西。

```python
import json

def validate_schema(data, schema):
    errors = []
    _validate(data, schema, "", errors)
    return errors

def _validate(data, schema, path, errors):
    schema_type = schema.get("type")

    if schema_type == "object":
        if not isinstance(data, dict):
            errors.append(f"{path}: expected object, got {type(data).__name__}")
            return
        for key in schema.get("required", []):
            if key not in data:
                errors.append(f"{path}.{key}: required field missing")
        properties = schema.get("properties", {})
        for key, value in data.items():
            if key in properties:
                _validate(value, properties[key], f"{path}.{key}", errors)

    elif schema_type == "array":
        if not isinstance(data, list):
            errors.append(f"{path}: expected array, got {type(data).__name__}")
            return
        min_items = schema.get("minItems", 0)
        max_items = schema.get("maxItems", float("inf"))
        if len(data) < min_items:
            errors.append(f"{path}: array has {len(data)} items, minimum is {min_items}")
        if len(data) > max_items:
            errors.append(f"{path}: array has {len(data)} items, maximum is {max_items}")
        items_schema = schema.get("items", {})
        for i, item in enumerate(data):
            _validate(item, items_schema, f"{path}[{i}]", errors)

    elif schema_type == "string":
        if not isinstance(data, str):
            errors.append(f"{path}: expected string, got {type(data).__name__}")
            return
        enum_values = schema.get("enum")
        if enum_values and data not in enum_values:
            errors.append(f"{path}: '{data}' not in allowed values {enum_values}")

    elif schema_type == "number":
        if not isinstance(data, (int, float)):
            errors.append(f"{path}: expected number, got {type(data).__name__}")
            return
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and data < minimum:
            errors.append(f"{path}: {data} is less than minimum {minimum}")
        if maximum is not None and data > maximum:
            errors.append(f"{path}: {data} is greater than maximum {maximum}")

    elif schema_type == "boolean":
        if not isinstance(data, bool):
            errors.append(f"{path}: expected boolean, got {type(data).__name__}")

    elif schema_type == "integer":
        if not isinstance(data, int) or isinstance(data, bool):
            errors.append(f"{path}: expected integer, got {type(data).__name__}")
```

### 第 2 步：Pydantic 风格的模型转 schema

构建一个最小的"类转 schema"转换器。定义一个 Python 类，自动生成它的 JSON Schema。

```python
class SchemaField:
    def __init__(self, field_type, required=True, default=None, enum=None, minimum=None, maximum=None):
        self.field_type = field_type
        self.required = required
        self.default = default
        self.enum = enum
        self.minimum = minimum
        self.maximum = maximum

def python_type_to_schema(field):
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
    }

    schema = {}

    if field.field_type in type_map:
        schema["type"] = type_map[field.field_type]
    elif field.field_type == list:
        schema["type"] = "array"
        schema["items"] = {"type": "string"}
    elif isinstance(field.field_type, dict):
        schema = field.field_type

    if field.enum:
        schema["enum"] = field.enum
    if field.minimum is not None:
        schema["minimum"] = field.minimum
    if field.maximum is not None:
        schema["maximum"] = field.maximum

    return schema

def model_to_schema(name, fields):
    properties = {}
    required = []

    for field_name, field in fields.items():
        properties[field_name] = python_type_to_schema(field)
        if field.required:
            required.append(field_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }
```

### 第 3 步：受约束的 token 过滤器

模拟 constrained decoding。给定一个不完整的 JSON 字符串和一个 schema，判定当前位置哪些 token 类别是合法的。

```python
def next_valid_tokens(partial_json, schema):
    stripped = partial_json.strip()

    if not stripped:
        return ["{"]

    try:
        json.loads(stripped)
        return ["<EOS>"]
    except json.JSONDecodeError:
        pass

    last_char = stripped[-1] if stripped else ""

    if last_char == "{":
        return ['"', "}"]
    elif last_char == '"':
        if stripped.endswith('":'):
            return ['"', "0-9", "true", "false", "null", "[", "{"]
        return ["a-z", '"']
    elif last_char == ":":
        return [" ", '"', "0-9", "true", "false", "null", "[", "{"]
    elif last_char == ",":
        return [" ", '"', "{", "["]
    elif last_char in "0123456789":
        return ["0-9", ".", ",", "}", "]"]
    elif last_char == "}":
        return [",", "}", "]", "<EOS>"]
    elif last_char == "]":
        return [",", "}", "<EOS>"]
    elif last_char == "[":
        return ['"', "0-9", "true", "false", "null", "{", "[", "]"]
    else:
        return ["any"]

def demonstrate_constrained_decoding():
    partial_states = [
        '',
        '{',
        '{"product"',
        '{"product":',
        '{"product": "Sony"',
        '{"product": "Sony",',
        '{"product": "Sony", "price":',
        '{"product": "Sony", "price": 348',
        '{"product": "Sony", "price": 348}',
    ]

    print(f"{'Partial JSON':<45} {'Valid Next Tokens'}")
    print("-" * 80)
    for state in partial_states:
        valid = next_valid_tokens(state, {})
        display = state if state else "(empty)"
        print(f"{display:<45} {valid}")
```

### 第 4 步：抽取流水线

把所有东西组合成一条抽取流水线：定义 schema，模拟 LLM 产出结构化输出，校验输出，并处理重试。

```python
def simulate_llm_extraction(text, schema, attempt=0):
    if "headphones" in text.lower() or "sony" in text.lower():
        if attempt == 0:
            return '{"product": "Sony WH-1000XM5", "price": 348.00, "in_stock": true, "categories": ["audio", "headphones"]}'
        return '{"product": "Sony WH-1000XM5", "price": 348.00, "in_stock": true}'

    if "laptop" in text.lower():
        return '{"product": "MacBook Pro 16", "price": 2499.00, "in_stock": false, "categories": ["computers"]}'

    return '{"product": "Unknown", "price": 0, "in_stock": false}'

def extract_with_retry(text, schema, max_retries=3):
    for attempt in range(max_retries):
        raw = simulate_llm_extraction(text, schema, attempt)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"  Attempt {attempt + 1}: JSON parse error -- {e}")
            continue

        errors = validate_schema(data, schema)
        if not errors:
            return data

        print(f"  Attempt {attempt + 1}: Schema validation errors -- {errors}")

    return None

product_schema = {
    "type": "object",
    "properties": {
        "product": {"type": "string"},
        "price": {"type": "number", "minimum": 0},
        "in_stock": {"type": "boolean"},
        "categories": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["product", "price", "in_stock"],
}
```

### 第 5 步：运行完整流水线

```python
def run_demo():
    print("=" * 60)
    print("  Structured Output Pipeline Demo")
    print("=" * 60)

    print("\n--- Schema Definition ---")
    product_fields = {
        "product": SchemaField(str),
        "price": SchemaField(float, minimum=0),
        "in_stock": SchemaField(bool),
        "categories": SchemaField(list, required=False),
    }
    generated_schema = model_to_schema("Product", product_fields)
    print(json.dumps(generated_schema, indent=2))

    print("\n--- Schema Validation ---")
    test_cases = [
        ({"product": "Test", "price": 10.0, "in_stock": True}, "Valid object"),
        ({"product": "Test", "price": -5.0, "in_stock": True}, "Negative price"),
        ({"product": "Test", "in_stock": True}, "Missing price"),
        ({"product": "Test", "price": "ten", "in_stock": True}, "String as price"),
        ("not an object", "String instead of object"),
    ]

    for data, label in test_cases:
        errors = validate_schema(data, product_schema)
        status = "PASS" if not errors else f"FAIL: {errors}"
        print(f"  {label}: {status}")

    print("\n--- Constrained Decoding Simulation ---")
    demonstrate_constrained_decoding()

    print("\n--- Extraction Pipeline ---")
    texts = [
        "The Sony WH-1000XM5 headphones are priced at $348 and currently available.",
        "The new MacBook Pro 16-inch laptop costs $2499 but is sold out.",
        "This is a random sentence with no product info.",
    ]

    for text in texts:
        print(f"\n  Input: {text[:60]}...")
        result = extract_with_retry(text, product_schema)
        if result:
            print(f"  Output: {json.dumps(result)}")
        else:
            print(f"  Output: FAILED after retries")
```

## Use It

### OpenAI Structured Outputs

```python
# from openai import OpenAI
# from pydantic import BaseModel
#
# client = OpenAI()
#
# class Product(BaseModel):
#     product: str
#     price: float
#     in_stock: bool
#
# response = client.beta.chat.completions.parse(
#     model="gpt-5-mini",
#     messages=[
#         {"role": "system", "content": "Extract product information."},
#         {"role": "user", "content": "Sony WH-1000XM5, $348, in stock"},
#     ],
#     response_format=Product,
# )
#
# product = response.choices[0].message.parsed
# print(product.product, product.price, product.in_stock)
```

OpenAI 的 structured output 模式内部使用 constrained decoding。模型生成的每个 token 都保证产出符合 Pydantic schema 的输出。不需要重试，不需要校验。约束直接烙进了解码过程。

### Anthropic Tool Use

```python
# import anthropic
#
# client = anthropic.Anthropic()
#
# response = client.messages.create(
#     model="claude-opus-4-7",
#     max_tokens=1024,
#     tools=[{
#         "name": "extract_product",
#         "description": "Extract product information from text",
#         "input_schema": {
#             "type": "object",
#             "properties": {
#                 "product": {"type": "string"},
#                 "price": {"type": "number"},
#                 "in_stock": {"type": "boolean"},
#             },
#             "required": ["product", "price", "in_stock"],
#         },
#     }],
#     messages=[{"role": "user", "content": "Extract: Sony WH-1000XM5, $348, in stock"}],
# )
```

Anthropic 通过 tool use 实现结构化输出。模型发出一个工具调用，参数符合 input_schema。结果相同，API 界面不同。

### Instructor 库

```python
# pip install instructor
# import instructor
# from openai import OpenAI
# from pydantic import BaseModel
#
# client = instructor.from_openai(OpenAI())
#
# class Product(BaseModel):
#     product: str
#     price: float
#     in_stock: bool
#
# product = client.chat.completions.create(
#     model="gpt-5-mini",
#     response_model=Product,
#     messages=[{"role": "user", "content": "Sony WH-1000XM5, $348, in stock"}],
# )
```

Instructor 包装任意 LLM 客户端，并加上带校验的自动重试。如果第一次尝试未通过校验，它会把错误作为上下文发回模型，要求其修正输出。这对任何供应商都有效，不只是 OpenAI。

## Ship It

本课产出 `outputs/prompt-structured-extractor.md`——一个可复用的 prompt 模板，给定 schema 定义就能从任意文本中抽取结构化数据。喂给它一个 JSON Schema 和一段非结构化文本，它返回校验过的 JSON。

它还产出 `outputs/skill-structured-outputs.md`——一个决策框架，根据你的供应商、可靠性要求和 schema 复杂度选择正确的 structured output 策略。

## Exercises

1. 扩展 schema 校验器以支持 `oneOf`（数据必须恰好匹配若干 schema 中的一个）。这能处理多态输出——例如，一个字段既可能是 `Product` 也可能是形状不同的 `Service` 对象。

2. 构建一个 "schema diff" 工具，比较两个 schema，识别破坏性变更（删除了必填字段、改变了类型）与非破坏性变更（新增可选字段、放宽了约束）。这对在生产中对抽取 schema 做版本管理至关重要。

3. 实现一个更真实的 constrained decoding 模拟器。给定一个 JSON Schema 和一个 100 个 token 的词汇表（字母、数字、标点、关键字），逐步走完生成过程，在每个位置屏蔽非法 token。度量每一步有多大比例的词汇是合法的。

4. 构建一个抽取评测套件。创建 50 条产品描述，并手工标注对应的 JSON 输出。在全部 50 条上运行你的抽取流水线，测量 exact match、字段级准确率和类型合规率。找出哪些字段最难正确抽取。

5. 为抽取流水线加上"置信度分数"。对每个抽取出的字段，估计模型有多确信（基于 token 概率，或者把抽取跑 3 次衡量一致性）。把低置信度的字段标记出来交人工复核。

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|------|----------------|----------------------|
| JSON mode | "返回 JSON" | 一个 API 开关，保证输出的 JSON 语法合法，但不强制任何特定 schema |
| Structured output | "带类型的 JSON" | 符合特定 JSON Schema 的输出，键、类型、约束都正确 |
| Constrained decoding | "受引导的生成" | 在每个 token 位置屏蔽会产出非法输出的 token——保证 100% 的 schema 合规 |
| JSON Schema | "一个 JSON 模板" | 描述 JSON 数据结构、类型和约束的声明式语言（OpenAPI、JSON Forms 等都在用） |
| Pydantic | "Python 的 dataclasses+" | 带类型校验、用于定义数据模型的 Python 库，FastAPI 和 Instructor 用它生成 JSON Schema |
| Function calling | "Tool use" | LLM 输出结构化的函数调用（名字 + 类型化参数）而非自由文本——OpenAI 和 Anthropic 都支持 |
| Instructor | "给 LLM 用的 Pydantic" | 包装 LLM 客户端、返回校验过的 Pydantic 实例的 Python 库，校验失败会自动重试 |
| Token masking | "过滤词汇表" | 在生成时把特定 token 的概率置零，使模型无法产出它们 |
| Schema compliance | "形状对得上" | 输出拥有所有必填字段、正确的类型、约束范围内的值，且没有多余的、不被允许的字段 |
| Retry loop | "反复试到成功" | 把校验错误发回模型，要求它修正输出——Instructor 自动这么做，重试次数有可配置上限 |

## Further Reading

- [OpenAI Structured Outputs Guide](https://platform.openai.com/docs/guides/structured-outputs) -- OpenAI API 中基于 JSON Schema 的 constrained decoding 官方文档
- [Willard & Louf, 2023 -- "Efficient Guided Generation for Large Language Models"](https://arxiv.org/abs/2307.09702) -- Outlines 论文，讲述如何把 JSON Schema 编译成有限状态机以实现 token 级约束
- [Instructor documentation](https://python.useinstructor.com/) -- 从任意 LLM 获取带 Pydantic 校验和重试的结构化输出的标准库
- [Anthropic Tool Use Guide](https://docs.anthropic.com/en/docs/tool-use) -- Claude 如何通过带 JSON Schema input_schema 的 tool use 实现结构化输出
- [JSON Schema specification](https://json-schema.org/) -- 每个主流结构化输出系统所用 schema 语言的完整规范
- [Outlines library](https://github.com/outlines-dev/outlines) -- 开源约束生成库，用正则和编译成有限状态机的 JSON Schema 来实现
- [Dong et al., "XGrammar: Flexible and Efficient Structured Generation Engine for Large Language Models" (MLSys 2025)](https://arxiv.org/abs/2411.15100) -- 当前最先进的语法引擎；下推自动机编译，约每 token 100 ns 完成掩码。
- [Beurer-Kellner et al., "Prompting Is Programming: A Query Language for Large Language Models" (LMQL)](https://arxiv.org/abs/2212.06094) -- LMQL 论文，把 constrained decoding 表述为一种带类型和值约束的查询语言。
- [Microsoft Guidance (framework docs)](https://github.com/guidance-ai/guidance) -- 模板驱动的约束生成；与供应商无关，是 Outlines 和 XGrammar 的补充。
