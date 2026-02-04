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

        # 创建主 Agent（memory_index 会在首次使用时懒加载）
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
            memory_index=None,  # 懒加载
            system_prompt=get_system_prompt(),
            default_provider=settings.default_model,
            auto_memory_retrieval=True,
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


async def get_agent_with_memory() -> Agent:
    """
    获取主 Agent 实例，并确保 memory_index 已初始化。

    这是一个 async 函数，用于 API endpoints。
    """
    agent = get_agent()

    # 确保 memory_index 已初始化
    if agent.memory_index is None:
        memory_index = await get_memory_index()
        if memory_index:
            agent.memory_index = memory_index
            print("[Agent] Memory index attached for cross-conversation retrieval")

    return agent


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

        @agent.tool()
        async def social_sentiment(symbol: str, hours: int = 24) -> str:
            """查询股票的社交媒体情绪

            获取 Reddit、StockTwits 等平台上的讨论情绪分析。

            Args:
                symbol: 股票代码，如 TSLA, AAPL
                hours: 分析时间范围（小时），默认 24
            """
            try:
                from ..social import get_social_service
                service = get_social_service()

                sentiment = service.get_sentiment(symbol=symbol.upper(), hours=hours)

                if sentiment.total_posts == 0:
                    return f"暂无 {symbol} 的社交媒体数据。请先使用 Collector Agent 采集数据。"

                emoji = "🐂" if sentiment.sentiment_label.value == "bullish" else "🐻" if sentiment.sentiment_label.value == "bearish" else "➖"

                result = [
                    f"## {symbol.upper()} 社交情绪 {emoji}",
                    f"",
                    f"**情绪**: {sentiment.sentiment_label.value.upper()} (分数: {sentiment.sentiment_score:.2f})",
                    f"**置信度**: {sentiment.confidence:.0%}",
                    f"",
                    f"### 统计 (过去 {hours} 小时)",
                    f"- 总讨论: {sentiment.total_posts} 条",
                    f"- 看涨: {sentiment.bullish_count} ({sentiment.bullish_count/max(sentiment.total_posts,1):.0%})",
                    f"- 看跌: {sentiment.bearish_count} ({sentiment.bearish_count/max(sentiment.total_posts,1):.0%})",
                    f"- 中性: {sentiment.neutral_count}",
                    f"- 互动量: {sentiment.total_engagement}",
                ]

                if sentiment.key_themes:
                    result.append(f"")
                    result.append(f"### 热门话题")
                    result.append(f"{', '.join(sentiment.key_themes)}")

                return "\n".join(result)
            except Exception as e:
                return f"获取社交情绪失败: {str(e)}"

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

    # ==================== Task Agent 工具 ====================
    elif config.id == "task":
        import json
        from ..tasks import (
            get_task_service, CreateTaskRequest,
            ActionType, ScheduleType, IntervalUnit, TaskStatus
        )

        @agent.tool()
        async def create_task(
            name: str,
            action_type: str,
            action_config: dict,
            schedule_type: str = "once",
            interval_value: int = None,
            interval_unit: str = None,
            notify_channels: list = None,
        ) -> str:
            """创建一个新的定时任务

            Args:
                name: 任务名称
                action_type: 任务类型 (stock_alert, stock_analysis, portfolio_monitor, news_watch)
                action_config: 任务配置，根据类型不同而不同
                schedule_type: 调度类型 (once, interval, cron)
                interval_value: 间隔值（用于 interval 类型）
                interval_unit: 间隔单位 (minutes, hours, days)
                notify_channels: 通知渠道列表 (telegram, discord, slack)
            """
            try:
                service = get_task_service()

                # Add notify_channels to action_config if provided
                if notify_channels:
                    action_config["notify_channels"] = notify_channels

                request = CreateTaskRequest(
                    name=name,
                    action_type=ActionType(action_type),
                    action_config=action_config,
                    schedule_type=ScheduleType(schedule_type),
                    interval_value=interval_value,
                    interval_unit=IntervalUnit(interval_unit) if interval_unit else None,
                )

                task = service.create_task(request)

                return f"""任务创建成功！

- **ID**: {task.id}
- **名称**: {task.name}
- **类型**: {task.action_type.value}
- **调度**: {task.schedule.type.value}
- **状态**: {task.status.value}
- **下次执行**: {task.next_execution_at.strftime('%Y-%m-%d %H:%M') if task.next_execution_at else '待定'}
"""
            except Exception as e:
                return f"创建任务失败: {str(e)}"

        @agent.tool()
        async def list_tasks(
            status: str = None,
            action_type: str = None,
            limit: int = 20,
        ) -> str:
            """列出所有任务

            Args:
                status: 按状态过滤 (pending, scheduled, running, completed, paused, cancelled, failed)
                action_type: 按类型过滤 (stock_alert, stock_analysis, portfolio_monitor, news_watch)
                limit: 返回数量上限
            """
            try:
                service = get_task_service()

                tasks, total = service.list_tasks(
                    status=TaskStatus(status) if status else None,
                    action_type=ActionType(action_type) if action_type else None,
                    limit=limit,
                )

                if not tasks:
                    return "暂无任务"

                result = ["## 任务列表\n"]
                result.append("| 名称 | 类型 | 状态 | 执行次数 | 下次执行 |")
                result.append("|------|------|------|----------|----------|")

                for t in tasks:
                    next_exec = t.next_execution_at.strftime('%m-%d %H:%M') if t.next_execution_at else "-"
                    result.append(f"| {t.name} | {t.action_type.value} | {t.status.value} | {t.execution_count} | {next_exec} |")

                result.append(f"\n共 {total} 个任务")
                return "\n".join(result)
            except Exception as e:
                return f"列出任务失败: {str(e)}"

        @agent.tool()
        async def get_task(task_id: str) -> str:
            """获取任务详情

            Args:
                task_id: 任务 ID
            """
            try:
                service = get_task_service()
                task = service.get_task(task_id)

                if not task:
                    return f"任务 {task_id} 不存在"

                config_str = json.dumps(task.action_config, ensure_ascii=False, indent=2)

                return f"""## 任务详情: {task.name}

- **ID**: {task.id}
- **描述**: {task.description or '无'}
- **类型**: {task.action_type.value}
- **状态**: {task.status.value}
- **执行次数**: {task.execution_count}
- **上次执行**: {task.last_executed_at.strftime('%Y-%m-%d %H:%M') if task.last_executed_at else '从未'}
- **下次执行**: {task.next_execution_at.strftime('%Y-%m-%d %H:%M') if task.next_execution_at else '无'}
- **创建时间**: {task.created_at.strftime('%Y-%m-%d %H:%M')}

### 配置
```json
{config_str}
```
"""
            except Exception as e:
                return f"获取任务失败: {str(e)}"

        @agent.tool()
        async def cancel_task(task_id: str) -> str:
            """取消任务

            Args:
                task_id: 任务 ID
            """
            try:
                service = get_task_service()
                if await service.cancel(task_id):
                    return f"任务 {task_id} 已取消"
                return f"任务 {task_id} 不存在"
            except Exception as e:
                return f"取消任务失败: {str(e)}"

        @agent.tool()
        async def trigger_task(task_id: str) -> str:
            """手动触发任务执行

            Args:
                task_id: 任务 ID
            """
            try:
                service = get_task_service()
                if await service.trigger(task_id):
                    return f"任务 {task_id} 已触发执行"
                return f"任务 {task_id} 不存在或正在运行中"
            except Exception as e:
                return f"触发任务失败: {str(e)}"

        @agent.tool()
        async def get_task_results(
            task_id: str,
            limit: int = 5,
        ) -> str:
            """获取任务执行结果

            Args:
                task_id: 任务 ID
                limit: 返回数量上限
            """
            try:
                service = get_task_service()
                task = service.get_task(task_id)
                executions, total = service.get_executions(task_id=task_id, limit=limit)

                if not executions:
                    return f"任务 {task_id} 暂无执行记录"

                task_name = task.name if task else task_id
                result = [f"## {task_name} 执行结果 (共 {total} 条)\n"]

                for e in executions:
                    status = "✅ 成功" if e.success else "❌ 失败"
                    duration = f"{e.duration_ms}ms" if e.duration_ms else "-"
                    time_str = e.started_at.strftime('%Y-%m-%d %H:%M:%S')

                    result.append(f"### {status} - {time_str} ({duration})")

                    if e.error:
                        result.append(f"**错误**: {e.error}")

                    if e.result:
                        # Format result based on content
                        data = e.result

                        # Stock alert result
                        if "triggered" in data:
                            triggered = "🔔 已触发" if data.get("triggered") else "⏳ 未触发"
                            result.append(f"- 状态: {triggered}")
                            if "symbol" in data:
                                result.append(f"- 股票: {data['symbol']}")
                            if "current_price" in data:
                                result.append(f"- 当前价格: ${data['current_price']:.2f}")
                            if "change_percent" in data:
                                result.append(f"- 涨跌幅: {data['change_percent']:+.2f}%")

                        # Stock analysis result
                        elif "analyses" in data:
                            if "symbol" in data:
                                result.append(f"- 股票: {data['symbol']}")
                            if "current_price" in data:
                                result.append(f"- 价格: ${data['current_price']:.2f}")

                            analyses = data.get("analyses", {})
                            if "technical" in analyses:
                                tech = analyses["technical"]
                                if "trend" in tech:
                                    result.append(f"- 技术面: {tech['trend']}")
                            if "fundamental" in analyses:
                                fund = analyses["fundamental"]
                                if "rating" in fund:
                                    result.append(f"- 基本面: {fund['rating']}")
                            if "sentiment" in analyses:
                                sent = analyses["sentiment"]
                                if "overall_sentiment" in sent:
                                    result.append(f"- 情绪: {sent['overall_sentiment']}")

                        # Portfolio monitor result
                        elif "total_value" in data:
                            result.append(f"- 组合价值: ${data['total_value']:,.2f}")
                            if "change_pct" in data:
                                result.append(f"- 变化: {data['change_pct']:+.2f}%")
                            if "triggered" in data and data["triggered"]:
                                result.append(f"- 状态: 🔔 已触发警报")

                        # News watch result
                        elif "news_count" in data:
                            result.append(f"- 新闻数量: {data['news_count']}")
                            news = data.get("news", [])
                            if news:
                                result.append("- 最新新闻:")
                                for n in news[:3]:
                                    result.append(f"  - {n.get('title', 'N/A')}")

                        # Generic result
                        else:
                            for key, value in list(data.items())[:8]:
                                if isinstance(value, (str, int, float, bool)):
                                    if isinstance(value, float):
                                        result.append(f"- {key}: {value:.2f}")
                                    else:
                                        result.append(f"- {key}: {value}")

                    result.append("")

                return "\n".join(result)
            except Exception as e:
                return f"获取执行结果失败: {str(e)}"

        @agent.tool()
        async def search_task_history(
            query: str,
            limit: int = 20,
        ) -> str:
            """搜索任务执行历史

            Args:
                query: 搜索关键词
                limit: 返回数量上限
            """
            try:
                service = get_task_service()
                executions = service.search_results(query, limit=limit)

                if not executions:
                    return f"未找到包含 '{query}' 的执行记录"

                result = [f"## 搜索结果: '{query}'\n"]

                for e in executions:
                    task = service.get_task(e.task_id)
                    task_name = task.name if task else e.task_id
                    status = "✅" if e.success else "❌"
                    time_str = e.started_at.strftime('%Y-%m-%d %H:%M')

                    result.append(f"### {status} {task_name} - {time_str}")

                    if e.result:
                        result_str = json.dumps(e.result, ensure_ascii=False)
                        if len(result_str) > 200:
                            result_str = result_str[:200] + "..."
                        result.append(f"```\n{result_str}\n```")

                    result.append("")

                return "\n".join(result)
            except Exception as e:
                return f"搜索失败: {str(e)}"

    # ==================== Collector Agent 工具 ====================
    if config.id == "collector":
        from ..social import get_social_service, SocialPlatform

        @agent.tool()
        async def collect_symbol(
            symbol: str,
            platforms: str = None,
            limit: int = 50,
        ) -> str:
            """采集特定股票的社交媒体数据

            Args:
                symbol: 股票代码，如 TSLA, AAPL
                platforms: 平台列表，逗号分隔（reddit, stocktwits, twitter）
                limit: 每个平台采集数量上限
            """
            try:
                service = get_social_service()

                platform_enums = None
                if platforms:
                    platform_enums = [SocialPlatform(p.strip()) for p in platforms.split(",")]

                results = await service.collect_for_symbol(
                    symbol=symbol.upper(),
                    platforms=platform_enums,
                    limit=limit,
                )

                total = sum(results.values())
                result_lines = [f"## {symbol.upper()} 社交媒体数据采集完成\n"]
                result_lines.append(f"**总计采集**: {total} 条帖子\n")

                for platform, count in results.items():
                    result_lines.append(f"- {platform}: {count} 条")

                # Get sentiment
                sentiment = service.get_sentiment(symbol.upper())
                result_lines.append(f"\n### 情绪分析")
                result_lines.append(f"- **整体情绪**: {sentiment.sentiment_label.value}")
                result_lines.append(f"- **情绪分数**: {sentiment.sentiment_score:.2f}")
                result_lines.append(f"- **看涨**: {sentiment.bullish_count} | **看跌**: {sentiment.bearish_count} | **中性**: {sentiment.neutral_count}")

                if sentiment.key_themes:
                    result_lines.append(f"- **关键话题**: {', '.join(sentiment.key_themes)}")

                return "\n".join(result_lines)
            except Exception as e:
                return f"采集 {symbol} 数据失败: {str(e)}"

        @agent.tool()
        async def collect_trending(
            platforms: str = None,
            limit: int = 20,
        ) -> str:
            """采集社交媒体热门股票

            Args:
                platforms: 平台列表，逗号分隔
                limit: 返回数量上限
            """
            try:
                service = get_social_service()

                platform_enums = None
                if platforms:
                    platform_enums = [SocialPlatform(p.strip()) for p in platforms.split(",")]

                trending = await service.collect_trending(platforms=platform_enums, limit=limit)

                if not trending:
                    return "未获取到热门股票数据"

                result = ["## 🔥 社交媒体热门股票\n"]
                result.append("| 排名 | 股票 | 提及次数 | 情绪 | 平台 |")
                result.append("|------|------|----------|------|------|")

                for t in trending:
                    emoji = "🐂" if t.sentiment_label.value == "bullish" else "🐻" if t.sentiment_label.value == "bearish" else "➖"
                    platforms_str = ", ".join([p.value for p in t.platforms])
                    result.append(f"| {t.rank} | {t.symbol} | {t.mentions_count} | {emoji} {t.sentiment_label.value} | {platforms_str} |")

                return "\n".join(result)
            except Exception as e:
                return f"采集热门股票失败: {str(e)}"

        @agent.tool()
        async def get_social_sentiment(
            symbol: str,
            hours: int = 24,
            platform: str = None,
        ) -> str:
            """获取股票的社交情绪分析

            Args:
                symbol: 股票代码
                hours: 分析时间范围（小时）
                platform: 指定平台
            """
            try:
                service = get_social_service()
                sentiment = service.get_sentiment(
                    symbol=symbol.upper(),
                    hours=hours,
                    platform=platform,
                )

                if sentiment.total_posts == 0:
                    return f"暂无 {symbol} 的社交媒体数据，请先采集数据"

                emoji = "🐂" if sentiment.sentiment_label.value == "bullish" else "🐻" if sentiment.sentiment_label.value == "bearish" else "➖"

                result = [
                    f"## {symbol.upper()} 社交情绪分析 {emoji}",
                    f"",
                    f"**情绪**: {sentiment.sentiment_label.value.upper()}",
                    f"**分数**: {sentiment.sentiment_score:.2f} (-1 到 1)",
                    f"**置信度**: {sentiment.confidence:.0%}",
                    f"",
                    f"### 统计",
                    f"- 总帖子: {sentiment.total_posts}",
                    f"- 看涨: {sentiment.bullish_count} ({sentiment.bullish_count/max(sentiment.total_posts,1):.0%})",
                    f"- 看跌: {sentiment.bearish_count} ({sentiment.bearish_count/max(sentiment.total_posts,1):.0%})",
                    f"- 中性: {sentiment.neutral_count}",
                    f"- 24h 提及: {sentiment.mentions_24h}",
                    f"",
                ]

                if sentiment.key_themes:
                    result.append(f"### 关键话题")
                    result.append(f"{', '.join(sentiment.key_themes)}")

                return "\n".join(result)
            except Exception as e:
                return f"获取情绪分析失败: {str(e)}"

        @agent.tool()
        async def search_social(
            keywords: str,
            platforms: str = None,
            limit: int = 30,
        ) -> str:
            """搜索社交媒体内容

            Args:
                keywords: 搜索关键词，逗号分隔
                platforms: 平台列表，逗号分隔
                limit: 返回数量上限
            """
            try:
                service = get_social_service()
                keyword_list = [k.strip() for k in keywords.split(",")]

                platform_enums = None
                if platforms:
                    platform_enums = [SocialPlatform(p.strip()) for p in platforms.split(",")]

                posts = await service.search(
                    keywords=keyword_list,
                    platforms=platform_enums,
                    limit=limit,
                )

                if not posts:
                    return f"未找到包含 '{keywords}' 的帖子"

                # Save to store
                result = [f"## 搜索结果: '{keywords}'\n"]
                result.append(f"找到 {len(posts)} 条帖子\n")

                for i, post in enumerate(posts[:10], 1):
                    emoji = "🐂" if post.sentiment_label.value == "bullish" else "🐻" if post.sentiment_label.value == "bearish" else "➖"
                    time_str = post.posted_at.strftime("%m-%d %H:%M")
                    result.append(f"### {i}. [{post.platform.value}] {time_str} {emoji}")

                    if post.title:
                        result.append(f"**{post.title[:80]}**")

                    content = post.content[:200] + "..." if len(post.content) > 200 else post.content
                    result.append(content)
                    result.append(f"👍 {post.upvotes} | 💬 {post.comments_count}")
                    result.append("")

                return "\n".join(result)
            except Exception as e:
                return f"搜索失败: {str(e)}"

        @agent.tool()
        async def get_social_posts(
            symbol: str,
            hours: int = 24,
            limit: int = 20,
        ) -> str:
            """获取已存储的社交帖子

            Args:
                symbol: 股票代码
                hours: 时间范围（小时）
                limit: 返回数量上限
            """
            try:
                service = get_social_service()
                posts = service.get_posts(
                    symbol=symbol.upper(),
                    hours=hours,
                    limit=limit,
                )

                if not posts:
                    return f"暂无 {symbol} 的存储帖子"

                result = [f"## {symbol.upper()} 社交帖子 (最近 {hours} 小时)\n"]

                for i, post in enumerate(posts[:limit], 1):
                    emoji = "🐂" if post.sentiment_label.value == "bullish" else "🐻" if post.sentiment_label.value == "bearish" else "➖"
                    time_str = post.posted_at.strftime("%m-%d %H:%M")
                    result.append(f"### {i}. [{post.platform.value}] {time_str} {emoji}")

                    if post.title:
                        result.append(f"**{post.title[:80]}**")

                    content = post.content[:150] + "..." if len(post.content) > 150 else post.content
                    result.append(content)
                    result.append(f"👍 {post.upvotes} | 💬 {post.comments_count} | 作者: {post.author}")

                    if post.url:
                        result.append(f"[链接]({post.url})")
                    result.append("")

                return "\n".join(result)
            except Exception as e:
                return f"获取帖子失败: {str(e)}"

        @agent.tool()
        async def get_available_platforms() -> str:
            """获取可用的社交媒体平台列表"""
            try:
                service = get_social_service()
                available = service.get_available_platforms()
                stats = service.get_stats()

                result = [
                    "## 社交媒体平台状态",
                    "",
                    "### 可用平台",
                ]

                all_platforms = ["reddit", "stocktwits", "twitter"]
                for p in all_platforms:
                    status = "✅" if p in available else "❌ 未配置"
                    result.append(f"- {p}: {status}")

                result.append("")
                result.append("### 数据统计")
                result.append(f"- 已存储帖子: {stats.get('total_posts', 0)}")
                result.append(f"- 涉及股票: {stats.get('unique_symbols', 0)}")

                by_platform = stats.get('posts_by_platform', {})
                if by_platform:
                    result.append("- 按平台分布:")
                    for p, count in by_platform.items():
                        result.append(f"  - {p}: {count}")

                return "\n".join(result)
            except Exception as e:
                return f"获取平台状态失败: {str(e)}"


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
    from datetime import datetime
    current_date = datetime.now().strftime("%Y年%m月%d日")

    return f"""你是一个智能个人助手，可以帮助用户完成各种任务。

**当前日期**: {current_date}

## 重要提醒
- 搜索信息时，使用当前年份 ({datetime.now().year} 年)
- 不要搜索过时的信息（如 2024 年、2025 年的旧数据）
- 财报、新闻等应搜索最新的

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

**常用场景**：
- 股票分析、行情查询、技术分析 → `call_agent(agent_id="stock", ...)`
- 社交媒体数据采集、Reddit/Twitter/StockTwits 数据获取 → `call_agent(agent_id="collector", ...)`
- 定时任务创建和管理 → `call_agent(agent_id="task", ...)`

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
