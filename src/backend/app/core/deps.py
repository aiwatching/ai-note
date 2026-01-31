"""
依赖注入
"""
from typing import Optional
from functools import lru_cache

from ..config import settings
from ..llm import LLMService
from ..llm.service import create_llm_service
from ..memory import Memory, SQLiteMemory
from ..agent import Agent, Skill, create_agent, AgentConfig, load_agent_configs
from ..tools import ToolRegistry, default_registry


# 全局实例
_llm_service: Optional[LLMService] = None
_memory: Optional[Memory] = None
_agent: Optional[Agent] = None


def get_llm_service() -> LLMService:
    """获取 LLM 服务实例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = create_llm_service(
            claude_api_key=settings.claude_api_key,
            deepseek_api_key=settings.deepseek_api_key,
            openai_api_key=settings.openai_api_key,
            grok_api_key=settings.grok_api_key,
            default=settings.default_model
        )
    return _llm_service


def get_memory() -> Memory:
    """获取 Memory 实例"""
    global _memory
    if _memory is None:
        _memory = SQLiteMemory("./data/memory.db")
    return _memory


def get_agent() -> Agent:
    """获取主 Agent 实例"""
    global _agent
    if _agent is None:
        llm = get_llm_service()

        # 创建主 Agent
        _agent = Agent(
            llm=llm,
            agent_id="main",
            name="Personal Assistant",
            description="个人智能助手，可以帮助你完成各种任务",
            skills=[
                Skill(name="通用对话", description="回答问题、闲聊"),
                Skill(name="任务分发", description="将复杂任务分发给专业 Agent"),
            ],
            tools=default_registry,
            memory=get_memory(),
            system_prompt=get_system_prompt(),
            default_provider=settings.default_model
        )

        # 注册基础工具
        _register_base_tools(_agent)

        # 从配置文件加载并注册子 Agent
        _register_sub_agents_from_config(_agent, llm)

    return _agent


def _register_sub_agents_from_config(main_agent: Agent, llm: LLMService):
    """从配置文件加载并注册子 Agent"""

    # 加载所有 Agent 配置
    configs = load_agent_configs()

    for config in configs:
        # 创建 Agent
        agent = create_agent(
            llm=llm,
            agent_id=config.id,
            name=config.name,
            description=config.description,
            skills=[{"name": s["name"], "description": s["description"]} for s in config.skills],
            system_prompt=config.system_prompt,
            default_provider=config.provider
        )

        # 注册 Agent 专属工具
        _register_agent_tools(agent, config)

        # 注册到主 Agent
        main_agent.register_agent(agent)
        print(f"[Agent] Registered: {config.name} ({config.id})")


def _register_agent_tools(agent: Agent, config: AgentConfig):
    """
    为 Agent 注册工具

    注意：工具的实际实现在这里，配置文件只定义工具的接口
    后续可以改为动态加载工具实现
    """

    # ==================== Stock Agent 工具 ====================
    if config.id == "stock":
        @agent.tool()
        async def stock_quote(symbol: str) -> str:
            """查询股票实时价格

            Args:
                symbol: 股票代码，如 AAPL, GOOGL, MSFT
            """
            # TODO: 实现真实 API 调用
            mock_data = {
                "AAPL": {"price": 185.50, "change": "+1.2%", "name": "Apple Inc."},
                "GOOGL": {"price": 141.80, "change": "-0.5%", "name": "Alphabet Inc."},
                "MSFT": {"price": 378.90, "change": "+0.8%", "name": "Microsoft Corp."},
                "TSLA": {"price": 248.50, "change": "+2.3%", "name": "Tesla Inc."},
            }
            if symbol.upper() in mock_data:
                data = mock_data[symbol.upper()]
                return f"{data['name']} ({symbol.upper()}): ${data['price']} ({data['change']})"
            return f"未找到股票 {symbol} 的数据"

        @agent.tool()
        async def stock_news(symbol: str) -> str:
            """查询股票相关新闻

            Args:
                symbol: 股票代码
            """
            # TODO: 实现真实新闻 API
            return f"[{symbol}] 最新新闻: 1. 公司发布Q4财报... 2. 分析师上调目标价..."

    # ==================== Note Agent 工具 ====================
    elif config.id == "note":
        @agent.tool()
        async def notion_search(query: str) -> str:
            """搜索 Notion 笔记

            Args:
                query: 搜索关键词
            """
            # TODO: 实现 Notion API
            return f"搜索 '{query}' 的结果: [Notion 集成待实现]"

        @agent.tool()
        async def notion_create(title: str, content: str) -> str:
            """创建 Notion 笔记

            Args:
                title: 笔记标题
                content: 笔记内容
            """
            # TODO: 实现 Notion API
            return f"已创建笔记: {title} [Notion 集成待实现]"

    # ==================== Dev Agent 工具 ====================
    # Dev Agent 暂无专属工具，使用通用对话能力


def _register_base_tools(agent: Agent):
    """注册基础工具（主 Agent 可直接使用）"""

    @agent.tool()
    async def get_current_time() -> str:
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @agent.tool()
    async def calculate(expression: str) -> str:
        """计算数学表达式

        Args:
            expression: 数学表达式，如 "2 + 3 * 4"
        """
        try:
            allowed_chars = set('0123456789+-*/.() ')
            if not all(c in allowed_chars for c in expression):
                return "Error: 表达式包含不允许的字符"
            result = eval(expression)
            return str(result)
        except Exception as e:
            return f"Error: {str(e)}"

    @agent.tool()
    async def web_search(query: str) -> str:
        """搜索网页信息

        Args:
            query: 搜索关键词
        """
        # TODO: 实现实际的网页搜索
        return f"搜索 '{query}' 的结果: [待实现]"


def get_system_prompt() -> str:
    """获取主 Agent 系统提示"""
    return """你是一个智能个人助手，可以帮助用户完成各种任务。

## 你的能力

### 直接能力（通过工具）
- 获取当前时间
- 数学计算
- 网页搜索

### 专业能力（通过子 Agent）
你可以调用专业的子 Agent 来处理特定领域的任务。
使用 call_agent 工具来调用它们。

## 工作原则

1. **简单任务**：直接使用工具完成
2. **专业任务**：调用对应的子 Agent
3. **复杂任务**：可以组合多个 Agent 和工具

## 回复风格
- 简洁明了
- 使用中文
- 必要时使用 Markdown 格式
"""


def reset_instances():
    """重置所有实例（用于测试）"""
    global _llm_service, _memory, _agent
    _llm_service = None
    _memory = None
    _agent = None
