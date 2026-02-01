"""
依赖注入
"""
from typing import Optional
from functools import lru_cache

from ..config import settings
from ..llm import LLMService
from ..llm.service import create_llm_service
from ..memory import Memory, SQLiteMemory
from ..memory.embeddings import EmbeddingConfig
from ..memory.index import MemoryIndex, MemoryIndexConfig
from ..agent import Agent, Skill, create_agent, AgentConfig, load_agent_configs
from ..tools import ToolRegistry, default_registry


# 全局实例
_llm_service: Optional[LLMService] = None
_memory: Optional[Memory] = None
_agent: Optional[Agent] = None
_memory_index: Optional[MemoryIndex] = None


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


async def get_memory_index() -> Optional[MemoryIndex]:
    """获取 Memory Index 实例（带 embedding 和 hybrid search）"""
    global _memory_index
    if _memory_index is None:
        # 创建 embedding 配置
        embedding_config = EmbeddingConfig(
            provider=settings.embedding_provider,
            model=settings.embedding_model,
            fallback=settings.embedding_fallback,
            cache_enabled=settings.embedding_cache_enabled,
            cache_max_entries=settings.embedding_cache_max_entries,
            local_model=settings.embedding_local_model,
            openai_api_key=settings.openai_api_key,
        )

        # 创建 memory index 配置
        index_config = MemoryIndexConfig(
            db_path=settings.memory_index_path,
            embedding_config=embedding_config,
            max_results=settings.search_max_results,
            min_score=settings.search_min_score,
            hybrid_enabled=settings.search_hybrid_enabled,
            vector_weight=settings.search_vector_weight,
            text_weight=settings.search_text_weight,
        )

        _memory_index = MemoryIndex(index_config)
        try:
            await _memory_index.initialize()
            print("[MemoryIndex] Initialized successfully")
        except Exception as e:
            print(f"[MemoryIndex] Failed to initialize: {e}")
            _memory_index = None

    return _memory_index


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

        # Log agent initialization
        _agent.logger.init("Personal Assistant", "主Agent初始化")

        # 注册基础工具
        _register_base_tools(_agent)

        # 从配置文件加载并注册子 Agent
        _register_sub_agents_from_config(_agent, llm)

        # Log ready state with details
        registered_tools = _agent.tools.list_tools()
        registered_agents = list(_agent._sub_agents.keys())
        _agent.logger.ready(
            tools_count=len(registered_tools),
            sub_agents_count=len(registered_agents)
        )
        print(f"[Agent] Tools registered: {registered_tools}")
        print(f"[Agent] Sub-agents registered: {registered_agents}")

    return _agent


def _register_sub_agents_from_config(main_agent: Agent, llm: LLMService):
    """从配置文件加载并注册子 Agent"""

    # 加载所有 Agent 配置
    configs = load_agent_configs()

    for config in configs:
        # Skip main agent - don't register it as a sub-agent of itself
        if config.id == "main":
            continue
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

        # Log agent registration
        main_agent.logger.agent_register(config.id, config.name)
        print(f"[Agent] Registered: {config.name} ({config.id})")


def _register_agent_tools(agent: Agent, config: AgentConfig):
    """
    为 Agent 注册工具

    注意：工具的实际实现在这里，配置文件只定义工具的接口
    后续可以改为动态加载工具实现
    """

    # ==================== Stock Agent 工具 ====================
    if config.id == "stock":
        from ..stock import StockService
        stock_service = StockService()

        @agent.tool()
        async def stock_quote(symbol: str) -> str:
            """查询股票实时价格

            Args:
                symbol: 股票代码，如 AAPL, GOOGL, MSFT, TSLA
            """
            try:
                quote = await stock_service.get_quote(symbol.upper())
                change_sign = "+" if quote.change_percent >= 0 else ""
                return f"{quote.symbol}: ${quote.price:.2f} ({change_sign}{quote.change_percent:.2f}%) | 开盘: ${quote.open:.2f} | 最高: ${quote.high:.2f} | 最低: ${quote.low:.2f} | 成交量: {quote.volume:,}"
            except Exception as e:
                return f"获取 {symbol} 股票数据失败: {str(e)}"

        @agent.tool()
        async def stock_news(symbol: str, limit: int = 5) -> str:
            """查询股票相关新闻

            Args:
                symbol: 股票代码
                limit: 返回新闻数量，默认5条
            """
            try:
                news_items = await stock_service.get_news(symbol.upper(), limit)
                if not news_items:
                    return f"未找到 {symbol} 的相关新闻"

                result = [f"📰 {symbol.upper()} 最新新闻:\n"]
                for i, news in enumerate(news_items, 1):
                    published = news.published.strftime("%m-%d %H:%M") if news.published else "未知时间"
                    result.append(f"{i}. [{published}] {news.title}")
                    if news.summary:
                        result.append(f"   {news.summary[:100]}...")
                return "\n".join(result)
            except Exception as e:
                return f"获取 {symbol} 新闻失败: {str(e)}"

        @agent.tool()
        async def stock_analyze(symbol: str) -> str:
            """综合分析股票（技术面+基本面+情绪）

            Args:
                symbol: 股票代码
            """
            try:
                analysis = await stock_service.analyze_stock(symbol.upper())

                result = [
                    f"## {analysis.symbol} 综合分析 - {analysis.company_name}",
                    f"",
                    f"**当前价格**: ${analysis.current_price:.2f} ({analysis.change_percent:+.2f}%)",
                    f"**综合评分**: {analysis.overall_score:.1f}/100",
                    f"**投资信号**: {analysis.overall_signal.upper()}",
                    f"",
                    f"### 技术面: {analysis.technical_signal}",
                ]

                if analysis.technical_summary.get("current"):
                    tech = analysis.technical_summary["current"]
                    if tech.get("rsi"):
                        result.append(f"- RSI: {tech['rsi']:.1f}")
                    if tech.get("sma_20"):
                        result.append(f"- SMA20: ${tech['sma_20']:.2f}")

                result.append(f"")
                result.append(f"### 基本面: {analysis.fundamental_rating}")

                if analysis.fundamental_summary.get("valuation"):
                    val = analysis.fundamental_summary["valuation"]
                    if val.get("pe_ratio"):
                        result.append(f"- P/E: {val['pe_ratio']:.1f}")

                result.append(f"")
                result.append(f"### 市场情绪: {analysis.sentiment_level}")

                if analysis.key_insights:
                    result.append(f"")
                    result.append(f"### 关键洞察")
                    for insight in analysis.key_insights:
                        result.append(f"- {insight}")

                return "\n".join(result)
            except Exception as e:
                return f"分析 {symbol} 失败: {str(e)}"

        @agent.tool()
        async def stock_technical(symbol: str) -> str:
            """技术分析（指标、趋势、信号）

            Args:
                symbol: 股票代码
            """
            try:
                tech = await stock_service.analyze_technical(symbol.upper())
                if "error" in tech:
                    return f"技术分析失败: {tech['error']}"

                current = tech.get("current", {})
                signals = tech.get("signals", {})

                result = [
                    f"## {symbol.upper()} 技术分析",
                    f"",
                    f"**趋势**: {tech.get('trend', 'neutral')}",
                    f"**当前价格**: ${current.get('price', 0):.2f}",
                    f"",
                    f"### 技术指标",
                    f"- SMA20: ${current.get('sma_20', 0):.2f}" if current.get('sma_20') else "",
                    f"- SMA50: ${current.get('sma_50', 0):.2f}" if current.get('sma_50') else "",
                    f"- RSI: {current.get('rsi', 0):.1f}" if current.get('rsi') else "",
                    f"- MACD: {current.get('macd', 0):.4f}" if current.get('macd') else "",
                ]

                return "\n".join([r for r in result if r])
            except Exception as e:
                return f"技术分析 {symbol} 失败: {str(e)}"

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

    # ==================== Memory Tools ====================
    @agent.tool()
    async def memory_search(
        query: str,
        max_results: int = 5,
        min_score: float = 0.3,
        source_filter: str = None
    ) -> str:
        """搜索记忆（对话历史、笔记、文档）

        使用混合搜索（语义 + 关键词）查找相关信息。

        Args:
            query: 搜索关键词，描述你要查找的内容
            max_results: 返回结果数量上限（默认 5）
            min_score: 最低相关度阈值 0-1（默认 0.3）
            source_filter: 按来源过滤（conversation, note, document）
        """
        import json
        from ..tools.memory_tools import memory_search as _memory_search

        memory_idx = await get_memory_index()
        result = await _memory_search(
            query=query,
            max_results=max_results,
            min_score=min_score,
            source_filter=source_filter,
            memory_index=memory_idx,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @agent.tool()
    async def memory_add(
        text: str,
        source: str = "note",
        source_id: str = None,
    ) -> str:
        """添加内容到记忆

        将重要信息保存到记忆系统，以便将来检索。

        Args:
            text: 要记住的文本内容
            source: 来源类型（note, document, fact）
            source_id: 可选的来源标识符
        """
        import json
        from ..tools.memory_tools import memory_add as _memory_add

        memory_idx = await get_memory_index()
        result = await _memory_add(
            text=text,
            source=source,
            source_id=source_id,
            memory_index=memory_idx,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    @agent.tool()
    async def memory_stats() -> str:
        """获取记忆系统统计信息

        返回记忆索引的统计数据，包括已索引的内容数量等。
        """
        import json
        from ..tools.memory_tools import memory_stats as _memory_stats

        memory_idx = await get_memory_index()
        result = await _memory_stats(memory_index=memory_idx)
        return json.dumps(result, ensure_ascii=False, indent=2)


def get_system_prompt() -> str:
    """获取主 Agent 系统提示"""
    return """你是一个智能个人助手，可以帮助用户完成各种任务。

## 你的能力

### 直接能力（通过工具）
- 获取当前时间
- 数学计算
- 网页搜索
- **记忆系统**：
  - `memory_search`: 搜索过往对话、笔记和文档
  - `memory_add`: 保存重要信息到记忆
  - `memory_stats`: 查看记忆系统状态

### 专业能力（通过子 Agent）
你可以调用专业的子 Agent 来处理特定领域的任务。
使用 call_agent 工具来调用它们。

## 记忆系统使用指南

记忆系统使用混合搜索（语义相似度 + 关键词匹配），可以帮助你：
- 查找相关的历史对话
- 检索用户之前提到的信息
- 保存重要的事实和偏好

**何时使用记忆搜索**：
- 用户询问"我之前说过..."、"上次我们讨论的..."
- 需要回顾特定话题的历史记录
- 用户提到某个名称或概念，可能在之前提过

**何时保存到记忆**：
- 用户明确表示要记住某事
- 重要的用户偏好或个人信息
- 值得长期保存的关键信息

## 工作原则

1. **简单任务**：直接使用工具完成
2. **专业任务**：调用对应的子 Agent
3. **复杂任务**：可以组合多个 Agent 和工具
4. **信息检索**：先搜索记忆，再回答相关问题

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
