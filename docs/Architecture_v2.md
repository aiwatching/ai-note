# Personal AI Assistant - 架构设计文档

**版本**: v2.0
**创建日期**: 2026-01-30
**文档状态**: 设计中

---

## 1. 架构概述

### 1.1 整体架构图

```
┌────────────────────────────────────────────────────────────────────────┐
│                           客户端层 (Client Layer)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   Web App    │  │  macOS App   │  │   iOS App    │  │  Chrome    │ │
│  │   (React)    │  │  (Electron)  │  │   (Future)   │  │  Extension │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ HTTP/WebSocket
┌────────────────────────────────────────────────────────────────────────┐
│                          API Gateway Layer                              │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                    FastAPI Application                            │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │ │
│  │  │ Auth API   │  │ Agent API  │  │ Config API │  │ WebSocket  │ │ │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       Agent Orchestration Layer                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                     Agent Router / Dispatcher                     │ │
│  │         (意图识别 → Agent 选择 → 任务分发 → 结果聚合)              │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                    │                                    │
│  ┌─────────────────────────────────┴─────────────────────────────────┐ │
│  │                        Context Manager                            │ │
│  │              (会话上下文 / Agent 记忆 / 跨 Agent 共享)             │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          Agent Layer                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ English  │ │  Note    │ │   Dev    │ │Investment│ │  Growth  │    │
│  │  Tutor   │ │ Manager  │ │Assistant │ │ Advisor  │ │  Coach   │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
│  ┌──────────┐ ┌──────────┐                                           │
│  │ Resource │ │ General  │    每个 Agent 包含:                        │
│  │Collector │ │  Chat    │    - Prompt Templates                     │
│  └──────────┘ └──────────┘    - Tools (能力)                         │
│                               - State (状态)                          │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         Service Layer                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │  LLM Service │  │ Tool Service │  │Memory Service│                 │
│  │  (多模型管理) │  │  (工具执行)   │  │  (记忆存储)  │                 │
│  └──────────────┘  └──────────────┘  └──────────────┘                 │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       External Integration Layer                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │  Claude  │ │ DeepSeek │ │  Gemini  │ │   Grok   │ │  OpenAI  │    │
│  │   API    │ │   API    │ │   API    │ │   API    │ │   API    │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                 │
│  │  Notion  │ │  Stock   │ │  GitHub  │ │ Web/RSS  │                 │
│  │   API    │ │   API    │ │   API    │ │ Fetcher  │                 │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘                 │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          Data Layer                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────────┐  │
│  │     SQLite       │  │   Vector Store   │  │    File System      │  │
│  │  (主数据存储)     │  │  (语义检索-可选)  │  │   (缓存/临时文件)   │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.2 设计原则

1. **Agent 独立性**：每个 Agent 独立开发、测试、部署，通过标准接口通信
2. **可插拔 LLM**：LLM 作为服务，Agent 不直接依赖特定模型
3. **工具化能力**：Agent 的特殊能力通过 Tool 实现，可组合、可扩展
4. **统一上下文**：Context Manager 统一管理会话状态和 Agent 记忆
5. **外部集成抽象**：所有外部服务通过适配器模式接入
6. **本地优先**：核心数据本地存储，外部服务可选

---

## 2. 核心组件设计

### 2.1 Agent Router / Dispatcher

**职责**：接收用户请求，识别意图，路由到合适的 Agent。

```python
# app/core/router.py

from typing import List, Dict, Optional
from pydantic import BaseModel

class UserIntent(BaseModel):
    """用户意图"""
    primary_agent: str           # 主要处理的 Agent
    secondary_agents: List[str]  # 可能需要协作的 Agent
    confidence: float            # 置信度
    extracted_params: Dict       # 提取的参数

class AgentRouter:
    """Agent 路由器"""

    def __init__(self, llm_service, agents: Dict[str, 'BaseAgent']):
        self.llm = llm_service
        self.agents = agents
        self.intent_classifier = IntentClassifier(llm_service)

    async def route(self, user_input: str, context: 'Context') -> UserIntent:
        """
        分析用户输入，确定应该由哪个 Agent 处理

        路由策略：
        1. 显式指定：用户通过命令或 UI 选择了 Agent
        2. 意图识别：LLM 分析用户输入的意图
        3. 上下文推断：根据当前会话上下文推断
        """
        # 检查是否有显式指定
        if context.selected_agent:
            return UserIntent(
                primary_agent=context.selected_agent,
                secondary_agents=[],
                confidence=1.0,
                extracted_params={}
            )

        # LLM 意图识别
        intent = await self.intent_classifier.classify(user_input, context)
        return intent

    async def dispatch(self, user_input: str, intent: UserIntent, context: 'Context'):
        """
        分发请求到对应的 Agent
        """
        primary_agent = self.agents[intent.primary_agent]

        # 执行主 Agent
        result = await primary_agent.execute(
            user_input=user_input,
            params=intent.extracted_params,
            context=context
        )

        # 如果需要协作 Agent
        for secondary_name in intent.secondary_agents:
            secondary_agent = self.agents[secondary_name]
            result = await secondary_agent.execute(
                user_input=result.output,
                params=result.handoff_params,
                context=context
            )

        return result
```

### 2.2 Intent Classifier

**职责**：使用 LLM 分析用户意图，决定路由目标。

```python
# app/core/intent.py

INTENT_CLASSIFICATION_PROMPT = """
你是一个意图分类器，负责分析用户输入并确定应该由哪个 Agent 处理。

可用的 Agent 列表：
{agent_descriptions}

用户输入：{user_input}

当前上下文：
- 上一个活跃的 Agent: {last_agent}
- 最近的话题: {recent_topics}

请分析用户的意图，返回 JSON：
{{
  "primary_agent": "最适合处理该请求的 Agent ID",
  "secondary_agents": ["可能需要协作的其他 Agent ID"],
  "confidence": 0.0-1.0,
  "reasoning": "简短解释为什么选择这个 Agent",
  "extracted_params": {{
    "任务相关的参数": "提取的值"
  }}
}}

Agent 描述：
- general_chat: 通用聊天、闲聊、无法归类的问题
- note_manager: 笔记相关：创建、查找、整理、同步 Notion
- dev_assistant: 编程开发：代码生成、调试、技术问答
- investment_advisor: 投资股票：行情查询、分析、建议
- growth_coach: 学习成长：目标管理、习惯追踪、学习计划
- resource_collector: 资源收集：保存链接、整理收藏、稍后阅读
- english_tutor: 英语学习：词汇、语法、练习、翻译

只返回 JSON，不要其他内容。
"""

class IntentClassifier:
    def __init__(self, llm_service):
        self.llm = llm_service

    async def classify(self, user_input: str, context: 'Context') -> UserIntent:
        prompt = INTENT_CLASSIFICATION_PROMPT.format(
            agent_descriptions=self._get_agent_descriptions(),
            user_input=user_input,
            last_agent=context.last_active_agent,
            recent_topics=context.recent_topics
        )

        response = await self.llm.chat(prompt, model="fast")  # 使用快速模型
        intent_data = json.loads(response)

        return UserIntent(**intent_data)
```

### 2.3 Base Agent

**职责**：Agent 基类，定义标准接口和通用行为。

```python
# app/agents/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class AgentConfig(BaseModel):
    """Agent 配置"""
    id: str
    name: str
    description: str
    default_model: str = "claude"
    tools: List[str] = []
    system_prompt: str = ""

class AgentResult(BaseModel):
    """Agent 执行结果"""
    success: bool
    output: str
    data: Optional[Dict[str, Any]] = None
    handoff_to: Optional[str] = None      # 需要交接给其他 Agent
    handoff_params: Optional[Dict] = None
    suggested_actions: List[Dict] = []

class BaseAgent(ABC):
    """Agent 基类"""

    def __init__(self, config: AgentConfig, llm_service, tool_service):
        self.config = config
        self.llm = llm_service
        self.tools = tool_service
        self._register_tools()

    @abstractmethod
    def _register_tools(self):
        """注册 Agent 可用的 Tools"""
        pass

    @abstractmethod
    async def execute(
        self,
        user_input: str,
        params: Dict[str, Any],
        context: 'Context'
    ) -> AgentResult:
        """执行 Agent 任务"""
        pass

    async def chat(
        self,
        user_input: str,
        context: 'Context',
        use_tools: bool = True
    ) -> str:
        """
        通用聊天方法，支持 Tool Calling
        """
        messages = self._build_messages(user_input, context)

        if use_tools and self.config.tools:
            # 带 Tools 的对话
            response = await self.llm.chat_with_tools(
                messages=messages,
                tools=self._get_tool_schemas(),
                model=self.config.default_model
            )

            # 处理 Tool 调用
            while response.tool_calls:
                tool_results = await self._execute_tools(response.tool_calls)
                messages.append(response)
                messages.append(tool_results)
                response = await self.llm.chat_with_tools(
                    messages=messages,
                    tools=self._get_tool_schemas(),
                    model=self.config.default_model
                )

            return response.content
        else:
            return await self.llm.chat(messages, model=self.config.default_model)

    def _build_messages(self, user_input: str, context: 'Context') -> List[Dict]:
        """构建消息列表"""
        messages = [
            {"role": "system", "content": self.config.system_prompt}
        ]

        # 添加历史消息
        for msg in context.get_history(limit=10):
            messages.append(msg)

        # 添加当前输入
        messages.append({"role": "user", "content": user_input})

        return messages
```

### 2.4 Tool System

**职责**：定义和管理 Agent 可用的工具能力。

```python
# app/core/tools.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel

class ToolSchema(BaseModel):
    """Tool 的 JSON Schema 定义（用于 LLM Function Calling）"""
    name: str
    description: str
    parameters: Dict[str, Any]

class BaseTool(ABC):
    """Tool 基类"""

    name: str
    description: str

    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """返回 Tool 的 Schema"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行 Tool"""
        pass

# ========== Notion Tools ==========

class NotionSearchTool(BaseTool):
    """Notion 搜索工具"""

    name = "notion_search"
    description = "搜索 Notion 中的页面和数据库"

    def __init__(self, notion_client):
        self.notion = notion_client

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "filter": {
                        "type": "object",
                        "description": "可选的过滤条件"
                    }
                },
                "required": ["query"]
            }
        )

    async def execute(self, query: str, filter: Dict = None) -> Dict[str, Any]:
        results = await self.notion.search(query=query, filter=filter)
        return {"results": results}

class NotionCreatePageTool(BaseTool):
    """Notion 创建页面工具"""

    name = "notion_create_page"
    description = "在 Notion 中创建新页面"

    # ... 实现

# ========== Stock Tools ==========

class StockQueryTool(BaseTool):
    """股票查询工具"""

    name = "stock_query"
    description = "查询股票实时行情"

    def __init__(self, stock_api_client):
        self.api = stock_api_client

    async def execute(self, symbol: str) -> Dict[str, Any]:
        data = await self.api.get_quote(symbol)
        return {
            "symbol": symbol,
            "price": data["price"],
            "change": data["change"],
            "change_percent": data["change_percent"],
            "volume": data["volume"]
        }

# ========== Dev Tools ==========

class CodeExecuteTool(BaseTool):
    """代码执行工具（沙箱）"""

    name = "code_execute"
    description = "在沙箱中执行代码"

    async def execute(self, code: str, language: str = "python") -> Dict[str, Any]:
        # 安全执行代码
        # 使用 Docker / RestrictedPython / 其他沙箱方案
        pass

# ========== Tool Registry ==========

class ToolRegistry:
    """Tool 注册中心"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        return self._tools.get(name)

    def get_schemas(self, tool_names: List[str]) -> List[ToolSchema]:
        return [self._tools[name].get_schema() for name in tool_names if name in self._tools]
```

### 2.5 Context Manager

**职责**：管理会话上下文、Agent 状态、跨 Agent 数据共享。

```python
# app/core/context.py

from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel

class Message(BaseModel):
    role: str
    content: str
    agent: Optional[str] = None
    timestamp: datetime = datetime.now()
    metadata: Dict[str, Any] = {}

class Context:
    """会话上下文"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[Message] = []
        self.agent_states: Dict[str, Dict] = {}  # 各 Agent 的状态
        self.shared_data: Dict[str, Any] = {}    # 跨 Agent 共享数据
        self.selected_agent: Optional[str] = None
        self.last_active_agent: Optional[str] = None
        self.recent_topics: List[str] = []

    def add_message(self, role: str, content: str, agent: str = None, **metadata):
        self.messages.append(Message(
            role=role,
            content=content,
            agent=agent,
            metadata=metadata
        ))
        if agent:
            self.last_active_agent = agent

    def get_history(self, limit: int = 20, agent: str = None) -> List[Dict]:
        """获取历史消息"""
        messages = self.messages
        if agent:
            messages = [m for m in messages if m.agent == agent]
        return [{"role": m.role, "content": m.content} for m in messages[-limit:]]

    def set_agent_state(self, agent_id: str, key: str, value: Any):
        """设置 Agent 状态"""
        if agent_id not in self.agent_states:
            self.agent_states[agent_id] = {}
        self.agent_states[agent_id][key] = value

    def get_agent_state(self, agent_id: str, key: str, default=None) -> Any:
        """获取 Agent 状态"""
        return self.agent_states.get(agent_id, {}).get(key, default)

    def share_data(self, key: str, value: Any):
        """跨 Agent 共享数据"""
        self.shared_data[key] = value

    def get_shared_data(self, key: str, default=None) -> Any:
        return self.shared_data.get(key, default)


class ContextManager:
    """上下文管理器"""

    def __init__(self, db_session):
        self.db = db_session
        self._contexts: Dict[str, Context] = {}

    def get_or_create(self, session_id: str) -> Context:
        if session_id not in self._contexts:
            # 尝试从数据库加载
            saved_context = self._load_from_db(session_id)
            if saved_context:
                self._contexts[session_id] = saved_context
            else:
                self._contexts[session_id] = Context(session_id)
        return self._contexts[session_id]

    def save(self, context: Context):
        """持久化上下文到数据库"""
        # 保存到 SQLite
        pass

    def _load_from_db(self, session_id: str) -> Optional[Context]:
        # 从 SQLite 加载
        pass
```

### 2.6 LLM Service

**职责**：统一的 LLM 调用接口，支持多模型切换。

```python
# app/services/llm_service.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum

class ModelType(Enum):
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    GROK = "grok"
    OPENAI = "openai"
    LOCAL = "local"  # Ollama

class LLMResponse(BaseModel):
    content: str
    model: str
    tool_calls: Optional[List[Dict]] = None
    usage: Dict[str, int] = {}

class BaseLLMProvider(ABC):
    """LLM Provider 基类"""

    @abstractmethod
    async def chat(self, messages: List[Dict], **kwargs) -> LLMResponse:
        pass

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict],
        **kwargs
    ) -> LLMResponse:
        pass

class ClaudeProvider(BaseLLMProvider):
    # 继承自现有实现
    pass

class DeepSeekProvider(BaseLLMProvider):
    # 继承自现有实现
    pass

# ... 其他 Provider

class LLMService:
    """统一 LLM 服务"""

    def __init__(self, config: Dict[str, Any]):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.default_model = config.get("default_model", "claude")
        self._init_providers(config)

    def _init_providers(self, config: Dict):
        """初始化各 Provider"""
        if config.get("claude_api_key"):
            self.providers["claude"] = ClaudeProvider(config["claude_api_key"])
        if config.get("deepseek_api_key"):
            self.providers["deepseek"] = DeepSeekProvider(config["deepseek_api_key"])
        # ... 其他

    async def chat(
        self,
        messages: List[Dict],
        model: str = None,
        **kwargs
    ) -> LLMResponse:
        """发送聊天请求"""
        model = model or self.default_model
        provider = self.providers.get(model)
        if not provider:
            raise ValueError(f"Model {model} not configured")
        return await provider.chat(messages, **kwargs)

    async def chat_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict],
        model: str = None,
        **kwargs
    ) -> LLMResponse:
        """带 Tool Calling 的聊天"""
        model = model or self.default_model
        provider = self.providers.get(model)
        return await provider.chat_with_tools(messages, tools, **kwargs)

    async def multi_model_chat(
        self,
        messages: List[Dict],
        models: List[str]
    ) -> Dict[str, LLMResponse]:
        """同时向多个模型发送请求（已有功能）"""
        import asyncio
        tasks = {
            model: self.chat(messages, model=model)
            for model in models if model in self.providers
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        return dict(zip(tasks.keys(), results))
```

---

## 3. 具体 Agent 设计

### 3.1 Note Manager Agent

```python
# app/agents/note_manager.py

class NoteManagerAgent(BaseAgent):
    """笔记管理 Agent"""

    def __init__(self, config, llm_service, tool_service, notion_client):
        super().__init__(config, llm_service, tool_service)
        self.notion = notion_client

    def _register_tools(self):
        self.available_tools = [
            "notion_search",
            "notion_create_page",
            "notion_update_page",
            "notion_query_database",
            "notion_add_to_database"
        ]

    async def execute(self, user_input: str, params: Dict, context: Context) -> AgentResult:
        """
        处理笔记相关请求

        支持的操作：
        - 创建笔记
        - 搜索笔记
        - 整理笔记
        - 同步 Notion
        """

        # 使用 LLM + Tools 处理
        response = await self.chat(user_input, context, use_tools=True)

        return AgentResult(
            success=True,
            output=response,
            suggested_actions=self._extract_suggestions(response)
        )

SYSTEM_PROMPT_NOTE_MANAGER = """
你是一个智能笔记管理助手，专门帮助用户管理 Notion 中的笔记。

你的能力：
1. 搜索笔记：在 Notion 中搜索相关内容
2. 创建笔记：在指定数据库创建新页面
3. 整理笔记：帮助用户分类、打标签、生成摘要
4. 查询数据库：查询特定数据库的内容

使用工具时：
- notion_search: 搜索关键词
- notion_create_page: 创建新页面
- notion_query_database: 查询数据库

回复风格：
- 简洁明了
- 操作成功后告知用户结果
- 如果需要更多信息，主动询问
"""
```

### 3.2 Dev Assistant Agent

```python
# app/agents/dev_assistant.py

class DevAssistantAgent(BaseAgent):
    """开发辅助 Agent"""

    def _register_tools(self):
        self.available_tools = [
            "code_execute",      # 代码执行（沙箱）
            "file_read",         # 读取文件
            "file_write",        # 写入文件
            "shell_execute",     # Shell 命令（受限）
            "web_search",        # 搜索技术文档
            "github_api"         # GitHub API
        ]

    async def execute(self, user_input: str, params: Dict, context: Context) -> AgentResult:
        # 判断请求类型
        if self._is_code_review(user_input):
            return await self._handle_code_review(user_input, context)
        elif self._is_code_generation(user_input):
            return await self._handle_code_generation(user_input, context)
        else:
            return await self._handle_general_dev_question(user_input, context)

SYSTEM_PROMPT_DEV_ASSISTANT = """
你是一个专业的编程助手，帮助用户：
1. 生成代码
2. 解释代码
3. 调试问题
4. 代码审查
5. 技术方案设计

你可以使用工具执行代码、读写文件、搜索文档。

安全规则：
- 不执行可能造成系统损害的命令
- 不访问敏感目录
- 文件操作需要用户确认

回复风格：
- 代码用 markdown 代码块
- 解释清晰简洁
- 给出最佳实践建议
"""
```

### 3.3 Investment Advisor Agent

```python
# app/agents/investment_advisor.py

class InvestmentAdvisorAgent(BaseAgent):
    """投资顾问 Agent"""

    def _register_tools(self):
        self.available_tools = [
            "stock_query",        # 查询股票行情
            "stock_history",      # 查询历史数据
            "stock_news",         # 查询相关新闻
            "stock_financials",   # 查询财务数据
            "web_search"          # 搜索财经信息
        ]

SYSTEM_PROMPT_INVESTMENT = """
你是一个投资分析助手，帮助用户：
1. 查询股票行情
2. 分析基本面（财报、估值）
3. 分析技术面（K线、指标）
4. 监控新闻舆情
5. 投资建议（仅供参考）

重要声明：
- 你提供的所有信息仅供参考
- 不构成投资建议
- 投资有风险，用户需自行判断

数据来源：
- 实时行情来自 API
- 财务数据来自公开财报
- 新闻来自公开渠道

回复时：
- 数据要准确标注来源和时间
- 分析要客观中立
- 明确提示风险
"""
```

---

## 4. 目录结构

```
ai-assistant/
├── docs/
│   ├── PRD_PersonalAssistant.md
│   ├── Architecture_v2.md
│   └── API_v2.md
│
├── src/
│   ├── backend/                      # Python 后端
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py              # FastAPI 入口
│   │   │   ├── config.py            # 配置管理
│   │   │   │
│   │   │   ├── core/                # 核心组件
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py        # Agent 路由
│   │   │   │   ├── intent.py        # 意图分类
│   │   │   │   ├── context.py       # 上下文管理
│   │   │   │   ├── tools.py         # Tool 系统
│   │   │   │   └── orchestrator.py  # Agent 编排
│   │   │   │
│   │   │   ├── agents/              # Agent 实现
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py          # Agent 基类
│   │   │   │   ├── general_chat.py  # 通用聊天
│   │   │   │   ├── note_manager.py  # 笔记管理
│   │   │   │   ├── dev_assistant.py # 开发助手
│   │   │   │   ├── investment.py    # 投资顾问
│   │   │   │   ├── growth_coach.py  # 成长教练
│   │   │   │   └── resource_collector.py
│   │   │   │
│   │   │   ├── tools/               # Tool 实现
│   │   │   │   ├── __init__.py
│   │   │   │   ├── notion/          # Notion 相关
│   │   │   │   │   ├── search.py
│   │   │   │   │   ├── create.py
│   │   │   │   │   └── query.py
│   │   │   │   ├── stock/           # 股票相关
│   │   │   │   │   ├── query.py
│   │   │   │   │   └── analysis.py
│   │   │   │   ├── dev/             # 开发相关
│   │   │   │   │   ├── code_exec.py
│   │   │   │   │   └── file_ops.py
│   │   │   │   └── web/             # 网络相关
│   │   │   │       ├── search.py
│   │   │   │       └── fetch.py
│   │   │   │
│   │   │   ├── services/            # 业务服务
│   │   │   │   ├── __init__.py
│   │   │   │   ├── llm_service.py   # LLM 统一服务
│   │   │   │   ├── memory_service.py # 记忆服务
│   │   │   │   └── session_service.py
│   │   │   │
│   │   │   ├── integrations/        # 外部集成
│   │   │   │   ├── __init__.py
│   │   │   │   ├── notion_client.py
│   │   │   │   ├── stock_api.py
│   │   │   │   └── github_api.py
│   │   │   │
│   │   │   ├── llm/                 # LLM Providers
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── claude.py
│   │   │   │   ├── deepseek.py
│   │   │   │   ├── gemini.py
│   │   │   │   ├── grok.py
│   │   │   │   └── openai.py
│   │   │   │
│   │   │   ├── api/                 # API 路由
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chat.py          # 主聊天接口
│   │   │   │   ├── agents.py        # Agent 管理
│   │   │   │   ├── sessions.py      # 会话管理
│   │   │   │   └── settings.py      # 设置
│   │   │   │
│   │   │   ├── models/              # 数据模型
│   │   │   │   ├── __init__.py
│   │   │   │   ├── session.py
│   │   │   │   ├── message.py
│   │   │   │   └── user_config.py
│   │   │   │
│   │   │   └── prompts/             # Prompt 模板
│   │   │       ├── intent.py
│   │   │       ├── note_manager.py
│   │   │       └── ...
│   │   │
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── .env.example
│   │
│   └── frontend/                    # React 前端
│       ├── src/
│       │   ├── components/
│       │   │   ├── Chat/            # 聊天组件
│       │   │   ├── AgentSelector/   # Agent 选择器
│       │   │   ├── ModelSelector/   # 模型选择器
│       │   │   └── ...
│       │   ├── pages/
│       │   │   ├── Home/            # 主页（聊天界面）
│       │   │   ├── Settings/        # 设置页
│       │   │   └── History/         # 历史记录
│       │   ├── services/
│       │   ├── store/
│       │   └── types/
│       ├── package.json
│       └── vite.config.ts
│
├── data/
│   └── database/
│       └── assistant.db
│
├── scripts/
└── docker-compose.yml
```

---

## 5. API 设计

### 5.1 主聊天接口

```
POST /api/v2/chat
Content-Type: application/json

Request:
{
  "message": "帮我查一下茅台今天的股价",
  "session_id": "uuid",           // 可选，不传则创建新会话
  "agent": "investment_advisor",   // 可选，不传则自动路由
  "model": "claude",              // 可选，使用 Agent 默认模型
  "stream": true                  // 是否流式响应
}

Response (非流式):
{
  "code": 200,
  "data": {
    "session_id": "uuid",
    "message_id": "uuid",
    "agent": "investment_advisor",
    "model": "claude",
    "content": "茅台(600519)当前股价...",
    "tool_calls": [
      {
        "tool": "stock_query",
        "input": {"symbol": "600519"},
        "output": {...}
      }
    ],
    "suggested_actions": [
      {"type": "view_chart", "label": "查看K线图", "params": {...}}
    ]
  }
}

Response (流式):
data: {"type": "start", "agent": "investment_advisor"}
data: {"type": "tool_call", "tool": "stock_query", "status": "running"}
data: {"type": "tool_result", "tool": "stock_query", "data": {...}}
data: {"type": "content", "delta": "茅台"}
data: {"type": "content", "delta": "(600519)"}
data: {"type": "content", "delta": "当前股价..."}
data: {"type": "done", "message_id": "uuid"}
```

### 5.2 Agent 管理接口

```
# 获取可用 Agent 列表
GET /api/v2/agents

Response:
{
  "agents": [
    {
      "id": "note_manager",
      "name": "笔记管理",
      "description": "管理 Notion 笔记",
      "icon": "📝",
      "status": "active"
    },
    ...
  ]
}

# 获取 Agent 详情
GET /api/v2/agents/{agent_id}

# 配置 Agent
PUT /api/v2/agents/{agent_id}/config
```

### 5.3 会话管理接口

```
# 获取会话列表
GET /api/v2/sessions?limit=20&offset=0

# 获取会话详情（包含消息历史）
GET /api/v2/sessions/{session_id}

# 删除会话
DELETE /api/v2/sessions/{session_id}
```

---

## 6. 数据模型

### 6.1 数据库表

```sql
-- 会话表
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_agent TEXT,
    status TEXT DEFAULT 'active'
);

-- 消息表
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- user / assistant / system / tool
    content TEXT,
    agent TEXT,
    model TEXT,
    tool_calls JSON,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Agent 状态表
CREATE TABLE agent_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    state_key TEXT NOT NULL,
    state_value JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, agent_id, state_key)
);

-- 用户配置表
CREATE TABLE user_config (
    key TEXT PRIMARY KEY,
    value JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 7. 与现有代码的关系

### 7.1 可复用的模块

| 现有模块 | 用途 | 改动 |
|---------|------|------|
| `app/ai/` | LLM Provider 实现 | 移动到 `app/llm/`，重构为统一接口 |
| `app/services/chat_service.py` | 聊天逻辑 | 重构为 Agent 模式 |
| `app/models/chat.py` | 数据模型 | 简化，移除旧的笔记关联 |

### 7.2 需要废弃的模块

| 模块 | 原因 |
|------|------|
| `app/models/note.py` | 笔记改用 Notion |
| `app/services/note_service.py` | 同上 |
| `app/storage/markdown_storage.py` | 同上 |

### 7.3 迁移策略

1. **Phase 1**: 搭建新架构骨架，与旧代码并存
2. **Phase 2**: 逐步迁移功能到新架构
3. **Phase 3**: 移除旧代码

---

## 8. 待定设计决策

### 8.1 需要讨论

1. **英语学习项目整合方式**
   - 选项 A: 作为独立微服务，通过 HTTP 调用
   - 选项 B: 代码合并到本项目
   - 选项 C: 共享数据库，前端统一

2. **向量数据库是否需要**
   - 用于语义搜索、长期记忆
   - 选项: Chroma / Qdrant / Milvus / 不需要

3. **是否支持多用户**
   - 当前设计为单用户
   - 多用户需要：认证系统、数据隔离、权限管理

---

## 附录

### A. 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React 18, TypeScript, Vite, TailwindCSS, shadcn/ui |
| 后端 | Python 3.11+, FastAPI, SQLAlchemy, Pydantic |
| 数据库 | SQLite (主), ChromaDB (向量, 可选) |
| LLM | Claude, DeepSeek, Gemini, Grok, OpenAI |
| 外部服务 | Notion API, 股票 API, GitHub API |

### B. 参考资料

- [LangChain Agents](https://python.langchain.com/docs/modules/agents/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Notion API](https://developers.notion.com/)
- [AutoGPT Architecture](https://github.com/Significant-Gravitas/Auto-GPT)

---

**文档结束**
