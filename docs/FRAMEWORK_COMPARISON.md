# AI Agent 框架详细对比

## 概览

针对你的架构需求（主 Agent + 多 Tools + 可创建子 Agent），对比以下方案：

| 方案 | GitHub Stars | 维护方 | 成熟度 |
|------|-------------|--------|--------|
| Pydantic AI | 7k+ | Pydantic 团队 | 较新但稳定 |
| Agno | 18k+ | Phidata 团队 | 成熟 |
| LangGraph | 10k+ | LangChain | 成熟 |
| 自己实现 | - | 你自己 | 完全可控 |

---

## 1. Pydantic AI

### 核心理念
> "像写 FastAPI 一样写 AI Agent"

### 代码示例

```python
# ============ 安装 ============
# pip install pydantic-ai

# ============ 基础 Agent ============
from pydantic_ai import Agent

agent = Agent(
    'claude-sonnet-4-20250514',
    system_prompt='你是一个个人助手，帮助用户管理笔记和查询股票。'
)

result = await agent.run('你好')
print(result.data)

# ============ 定义 Tools ============
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel

# 定义输出结构（自动验证）
class StockInfo(BaseModel):
    symbol: str
    price: float
    change_percent: float

# 定义依赖（类似 FastAPI 的依赖注入）
class Dependencies:
    def __init__(self, notion_token: str, stock_api_key: str):
        self.notion = NotionClient(notion_token)
        self.stock_api = StockAPI(stock_api_key)

agent = Agent(
    'claude-sonnet-4-20250514',
    deps_type=Dependencies,
    result_type=StockInfo,  # 强制输出格式
    system_prompt='你是一个个人助手...'
)

# 注册工具
@agent.tool
async def stock_quote(ctx: RunContext[Dependencies], symbol: str) -> str:
    """查询股票实时行情

    Args:
        symbol: 股票代码，如 AAPL, GOOGL
    """
    data = await ctx.deps.stock_api.get_quote(symbol)
    return f"{symbol}: ${data['price']} ({data['change']}%)"

@agent.tool
async def notion_search(ctx: RunContext[Dependencies], query: str) -> str:
    """搜索 Notion 笔记

    Args:
        query: 搜索关键词
    """
    results = await ctx.deps.notion.search(query)
    return "\n".join([f"- {r['title']}" for r in results])

@agent.tool
async def notion_create(
    ctx: RunContext[Dependencies],
    title: str,
    content: str,
    database: str = "Notes"
) -> str:
    """创建 Notion 笔记

    Args:
        title: 笔记标题
        content: 笔记内容
        database: 数据库名称
    """
    page = await ctx.deps.notion.create_page(database, title, content)
    return f"已创建笔记: {page['url']}"

# ============ 使用 ============
async def main():
    deps = Dependencies(
        notion_token="xxx",
        stock_api_key="xxx"
    )

    result = await agent.run(
        "苹果现在股价多少？帮我记到笔记里",
        deps=deps
    )
    print(result.data)  # StockInfo 对象，已验证

# ============ 多模型支持 ============
from pydantic_ai.models import ClaudeModel, DeepSeekModel

# 不同任务用不同模型
simple_agent = Agent(DeepSeekModel('deepseek-chat'))
complex_agent = Agent(ClaudeModel('claude-sonnet-4-20250514'))

# ============ 流式输出 ============
async with agent.run_stream('分析一下苹果的股票') as response:
    async for text in response.stream():
        print(text, end='', flush=True)

# ============ 对话历史 ============
result1 = await agent.run('苹果股价多少？')
result2 = await agent.run(
    '那谷歌呢？',
    message_history=result1.all_messages()  # 带上历史
)
```

### 优点
- ✅ **类型安全**：输出自动验证，格式错误会自动重试
- ✅ **依赖注入**：和 FastAPI 一样的模式
- ✅ **多模型**：支持 Claude、OpenAI、Gemini、DeepSeek 等
- ✅ **流式输出**：原生支持
- ✅ **代码简洁**：Pythonic

### 缺点
- ❌ 没有内置的记忆持久化（需要自己实现）
- ❌ 没有内置 UI
- ❌ 子 Agent 需要手动编排

### 适合场景
- 已有 FastAPI 项目
- 需要严格的输出格式
- 偏好类型安全

---

## 2. Agno (原 Phidata)

### 核心理念
> "极致性能 + 开箱即用"

### 代码示例

```python
# ============ 安装 ============
# pip install agno

# ============ 基础 Agent ============
from agno import Agent

agent = Agent(
    name="Personal Assistant",
    model="claude-sonnet-4-20250514",
    instructions="你是一个个人助手，帮助用户管理笔记和查询股票。",
    markdown=True,
)

agent.print_response("你好")

# ============ 定义 Tools ============
from agno import Agent, tool

@tool
def stock_quote(symbol: str) -> str:
    """查询股票实时行情

    Args:
        symbol: 股票代码，如 AAPL, GOOGL
    """
    data = stock_api.get_quote(symbol)
    return f"{symbol}: ${data['price']} ({data['change']}%)"

@tool
def notion_search(query: str) -> str:
    """搜索 Notion 笔记"""
    results = notion.search(query)
    return "\n".join([f"- {r['title']}" for r in results])

@tool
def notion_create(title: str, content: str, database: str = "Notes") -> str:
    """创建 Notion 笔记"""
    page = notion.create_page(database, title, content)
    return f"已创建笔记: {page['url']}"

agent = Agent(
    name="Personal Assistant",
    model="claude-sonnet-4-20250514",
    tools=[stock_quote, notion_search, notion_create],
    instructions="你是一个个人助手...",
)

# ============ 内置记忆 ============
from agno import Agent
from agno.memory import SqliteMemory

agent = Agent(
    name="Personal Assistant",
    model="claude-sonnet-4-20250514",
    memory=SqliteMemory(db_path="memory.db"),  # 内置持久化
    add_history_to_messages=True,  # 自动加载历史
)

# ============ 子 Agent（Team）============
# 创建专业子 Agent
stock_analyst = Agent(
    name="Stock Analyst",
    model="deepseek-chat",  # 用便宜的模型
    tools=[stock_quote, stock_history, stock_news],
    instructions="你是一个股票分析专家，专注于技术分析和基本面分析。"
)

note_manager = Agent(
    name="Note Manager",
    model="deepseek-chat",
    tools=[notion_search, notion_create, notion_update],
    instructions="你是一个笔记管理专家，帮助用户整理和管理 Notion 笔记。"
)

# 主 Agent，可以调用子 Agent
main_agent = Agent(
    name="Personal Assistant",
    model="claude-sonnet-4-20250514",
    team=[stock_analyst, note_manager],  # 子 Agent 团队
    instructions="""
    你是一个个人助手。根据用户需求：
    - 股票相关问题，交给 Stock Analyst
    - 笔记相关问题，交给 Note Manager
    - 简单问题，直接回答
    """,
)

main_agent.print_response("分析一下苹果的股票，然后帮我记个笔记")

# ============ 多模型 ============
from agno import Agent, Claude, DeepSeek, Gemini

# 方式1：直接指定
agent = Agent(model="claude-sonnet-4-20250514")
agent = Agent(model="deepseek-chat")
agent = Agent(model="gemini-2.0-flash")

# 方式2：使用 Model 类
agent = Agent(model=Claude(id="claude-sonnet-4-20250514"))
agent = Agent(model=DeepSeek(id="deepseek-chat"))

# ============ 流式输出 ============
for chunk in agent.run("分析苹果股票", stream=True):
    print(chunk.content, end="")

# ============ 内置 UI ============
# 启动 Agent UI（自带的 Web 界面）
# agno ui
# 然后访问 http://localhost:7777

# ============ 定时任务 ============
from agno import Agent
from agno.tools import ScheduleTool

agent = Agent(
    tools=[ScheduleTool()],  # 内置定时任务工具
)

agent.print_response("每天早上9点给我发送股票简报")
```

### 优点
- ✅ **极致性能**：官方称比其他框架快 10000 倍
- ✅ **内置记忆**：SqliteMemory, PostgresMemory 等
- ✅ **内置子 Agent**：Team 机制
- ✅ **内置 UI**：自带 Web 界面
- ✅ **多模型**：支持 23+ 模型提供商
- ✅ **代码极简**

### 缺点
- ❌ 类型安全不如 Pydantic AI
- ❌ 定制化程度稍低

### 适合场景
- 需要快速搭建
- 需要内置 UI
- 需要内置记忆
- 需要子 Agent 协作

---

## 3. LangGraph

### 核心理念
> "状态机 + 图结构 = 复杂工作流"

### 代码示例

```python
# ============ 安装 ============
# pip install langgraph langchain-anthropic

# ============ 基础结构 ============
from langgraph.graph import StateGraph, MessagesState
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

# 定义工具
@tool
def stock_quote(symbol: str) -> str:
    """查询股票行情"""
    return f"{symbol}: $185.50"

@tool
def notion_search(query: str) -> str:
    """搜索笔记"""
    return f"找到关于 {query} 的笔记..."

# 创建模型
model = ChatAnthropic(model="claude-sonnet-4-20250514")
model_with_tools = model.bind_tools([stock_quote, notion_search])

# 定义节点
def call_model(state: MessagesState):
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def call_tools(state: MessagesState):
    # 执行工具调用
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls
    results = []
    for tc in tool_calls:
        if tc["name"] == "stock_quote":
            result = stock_quote.invoke(tc["args"])
        elif tc["name"] == "notion_search":
            result = notion_search.invoke(tc["args"])
        results.append(ToolMessage(content=result, tool_call_id=tc["id"]))
    return {"messages": results}

def should_continue(state: MessagesState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return "end"

# 构建图
graph = StateGraph(MessagesState)
graph.add_node("agent", call_model)
graph.add_node("tools", call_tools)
graph.add_edge("__start__", "agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": "__end__"})
graph.add_edge("tools", "agent")

# 编译
app = graph.compile()

# 使用
result = app.invoke({"messages": [("user", "苹果股价多少？")]})

# ============ 状态持久化 ============
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("state.db")
app = graph.compile(checkpointer=checkpointer)

# 带 thread_id 的调用（自动保存/恢复状态）
config = {"configurable": {"thread_id": "user-123"}}
result = app.invoke({"messages": [("user", "苹果股价多少？")]}, config)
```

### 优点
- ✅ **状态管理强**：内置 Checkpoint，支持复杂状态
- ✅ **工作流灵活**：分支、循环、条件等
- ✅ **生态丰富**：LangChain 生态

### 缺点
- ❌ **复杂度高**：概念多，学习曲线陡
- ❌ **代码冗长**：简单任务也需要写很多代码
- ❌ **过度设计**：对于你的需求可能太重了

### 适合场景
- 复杂的多步骤工作流
- 需要精确的状态控制
- 已经在用 LangChain

---

## 4. 自己实现（直接用 Claude API）

### 核心理念
> "最少依赖，完全可控"

### 代码示例

```python
# ============ 安装 ============
# pip install anthropic

# ============ 完整实现 ============
import anthropic
import json
from typing import Callable

class SimpleAgent:
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        system_prompt: str = ""
    ):
        self.client = anthropic.Client()
        self.model = model
        self.system_prompt = system_prompt
        self.tools: dict[str, Callable] = {}
        self.tool_schemas: list[dict] = []
        self.messages: list[dict] = []

    def tool(self, func: Callable) -> Callable:
        """装饰器：注册工具"""
        # 从函数签名生成 schema
        schema = {
            "name": func.__name__,
            "description": func.__doc__ or "",
            "input_schema": self._generate_schema(func)
        }
        self.tools[func.__name__] = func
        self.tool_schemas.append(schema)
        return func

    def _generate_schema(self, func: Callable) -> dict:
        """从函数签名生成 JSON Schema"""
        import inspect
        sig = inspect.signature(func)
        properties = {}
        required = []
        for name, param in sig.parameters.items():
            properties[name] = {"type": "string"}  # 简化处理
            if param.default == inspect.Parameter.empty:
                required.append(name)
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    async def run(self, user_input: str) -> str:
        """运行 Agent"""
        self.messages.append({"role": "user", "content": user_input})

        while True:
            # 调用 LLM
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tool_schemas if self.tool_schemas else None,
                messages=self.messages
            )

            # 处理响应
            assistant_message = {"role": "assistant", "content": response.content}
            self.messages.append(assistant_message)

            # 检查是否需要调用工具
            tool_calls = [
                block for block in response.content
                if block.type == "tool_use"
            ]

            if not tool_calls:
                # 没有工具调用，返回文本
                text_blocks = [
                    block.text for block in response.content
                    if hasattr(block, 'text')
                ]
                return "\n".join(text_blocks)

            # 执行工具调用
            tool_results = []
            for tc in tool_calls:
                func = self.tools.get(tc.name)
                if func:
                    result = func(**tc.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": str(result)
                    })

            self.messages.append({"role": "user", "content": tool_results})

# ============ 使用 ============
agent = SimpleAgent(
    system_prompt="你是一个个人助手，帮助用户管理笔记和查询股票。"
)

@agent.tool
def stock_quote(symbol: str) -> str:
    """查询股票实时行情

    Args:
        symbol: 股票代码
    """
    # 实际调用股票 API
    return f"{symbol}: $185.50 (+1.2%)"

@agent.tool
def notion_search(query: str) -> str:
    """搜索 Notion 笔记"""
    # 实际调用 Notion API
    return f"找到 3 条关于 {query} 的笔记"

@agent.tool
def notion_create(title: str, content: str) -> str:
    """创建 Notion 笔记"""
    return f"已创建笔记: {title}"

# 运行
import asyncio
result = asyncio.run(agent.run("苹果股价多少？帮我记一下"))
print(result)
```

### 优点
- ✅ **完全可控**：每一行代码都清楚
- ✅ **零依赖**：只依赖 anthropic SDK
- ✅ **可定制**：想怎么改怎么改
- ✅ **学习价值**：理解 Agent 原理

### 缺点
- ❌ 需要自己实现很多功能（记忆、流式、子 Agent）
- ❌ 需要处理边界情况
- ❌ 多模型需要自己封装

### 适合场景
- 想完全理解原理
- 需求相对简单
- 不想依赖第三方框架

---

## 横向对比

### 代码量对比（实现相同功能）

| 功能 | Pydantic AI | Agno | LangGraph | 自己实现 |
|------|-------------|------|-----------|---------|
| 基础 Agent | 10 行 | 8 行 | 30 行 | 50 行 |
| + 3 个工具 | +15 行 | +12 行 | +25 行 | +30 行 |
| + 记忆 | +5 行 | +2 行 | +10 行 | +50 行 |
| + 子 Agent | +20 行 | +10 行 | +40 行 | +80 行 |
| **总计** | ~50 行 | ~35 行 | ~105 行 | ~210 行 |

### 功能对比

| 功能 | Pydantic AI | Agno | LangGraph | 自己实现 |
|------|-------------|------|-----------|---------|
| Tool 定义 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 类型安全 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| 内置记忆 | ❌ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ |
| 子 Agent | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| 流式输出 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 多模型 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 内置 UI | ❌ | ⭐⭐⭐⭐⭐ | ❌ | ❌ |
| 学习曲线 | 低 | 低 | 高 | 中 |
| 文档质量 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | - |

---

## 我的建议

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  你的需求:                                                   │
│  ├── 主 Agent + 多 Tools                                    │
│  ├── 可创建子 Agent                                          │
│  ├── 记忆系统                                               │
│  ├── 多模型支持                                              │
│  └── 自动化任务                                              │
│                                                             │
│  ════════════════════════════════════════════               │
│                                                             │
│  推荐方案：                                                  │
│                                                             │
│  【首选】Agno                                               │
│    - 内置你需要的几乎所有功能                                │
│    - 代码最简洁                                              │
│    - 自带 UI，方便调试                                       │
│    - Team 机制完美匹配你的"主Agent+子Agent"需求              │
│                                                             │
│  【备选】Pydantic AI                                        │
│    - 如果你更在意类型安全                                    │
│    - 与 FastAPI 集成更自然                                  │
│    - 需要自己实现记忆和子 Agent                              │
│                                                             │
│  【不推荐】LangGraph                                        │
│    - 对你的需求来说太重了                                    │
│    - 学习成本高                                              │
│                                                             │
│  【可考虑】自己实现                                          │
│    - 如果你想深入理解原理                                    │
│    - 后期可以迁移到框架                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 下一步

确定框架后，我可以帮你：
1. 搭建项目基础结构
2. 实现核心 Tools（Notion、股票 API）
3. 配置多模型支持
4. 实现记忆系统

Sources:
- [Pydantic AI 官方文档](https://ai.pydantic.dev/)
- [Agno GitHub](https://github.com/agno-ai/agno)
- [框架对比分析](https://langwatch.ai/blog/best-ai-agent-frameworks-in-2025-comparing-langgraph-dspy-crewai-agno-and-more)
- [Agno vs Pydantic AI 对比](https://hrshdg8.medium.com/agno-vs-pydantic-ai-the-ultimate-showdown-for-building-ai-agents-79b2c975cbec)
