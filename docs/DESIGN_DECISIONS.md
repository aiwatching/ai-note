# Personal AI Assistant - 设计决策

**版本**: v2.0
**更新日期**: 2026-01-30

---

## 1. 核心设计决策

### 1.1 产品定位

**目标**：个人化多 Agent AI 助手，帮助用户处理日常工作、学习、投资等各方面需求。

**核心价值**：
- 一个入口，统一管理所有 AI 能力
- AI 自动理解意图，无需手动切换
- 拥有长期记忆，真正了解用户
- 可自动化执行重复任务

### 1.2 使用模式

```
┌─────────────────────────────────────────────────────────────┐
│                      用户交互方式                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐      ┌─────────────────────────────┐  │
│  │   主动对话式     │      │       自动化任务式           │  │
│  │                 │      │                             │  │
│  │  用户提问       │      │  ┌─────────────────────┐   │  │
│  │      ↓         │      │  │ 定时任务             │   │  │
│  │  AI 理解意图    │      │  │ - 每日股票简报       │   │  │
│  │      ↓         │      │  │ - 每周学习总结       │   │  │
│  │  路由到 Agent   │      │  └─────────────────────┘   │  │
│  │      ↓         │      │                             │  │
│  │  执行并回复     │      │  ┌─────────────────────┐   │  │
│  │                 │      │  │ 事件触发             │   │  │
│  └─────────────────┘      │  │ - 股票价格预警       │   │  │
│                           │  │ - 新资源提醒         │   │  │
│                           │  └─────────────────────┘   │  │
│                           └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Agent 协作模式

**决策**：AI 自动路由（不需要用户手动选择 Agent）

**实现方式**：
```
用户输入 → Intent Classifier (LLM) → Agent Router → 目标 Agent
                    ↓
           识别意图 + 提取参数
           判断需要哪个/哪些 Agent
```

**路由规则**：
1. 分析用户输入的语义
2. 参考当前上下文（正在聊什么话题）
3. 判断主要 Agent + 可能需要协作的 Agent
4. 支持 Agent 之间的任务传递

---

## 2. 记忆系统设计

### 2.1 记忆层次

```
┌─────────────────────────────────────────────────────────────┐
│                        记忆系统                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: 短期记忆 (Session Memory)                         │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ - 当前会话的对话历史                                    │ │
│  │ - 会话内的上下文变量                                    │ │
│  │ - 存储：内存                                           │ │
│  │ - 生命周期：会话结束后可选择保存或丢弃                   │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Layer 2: 工作记忆 (Working Memory)                         │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ - 历史对话摘要                                         │ │
│  │ - 近期任务和结果                                       │ │
│  │ - Agent 状态                                          │ │
│  │ - 存储：SQLite                                        │ │
│  │ - 生命周期：保留最近 N 天/条                           │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Layer 3: 长期记忆 (Long-term Memory)                       │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ - 用户偏好和习惯                                       │ │
│  │ - 学习过的知识点                                       │ │
│  │ - 重要的决策和原因                                     │ │
│  │ - 收集的资源和笔记                                     │ │
│  │ - 存储：SQLite + Vector DB (可选)                     │ │
│  │ - 生命周期：永久                                       │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 记忆内容

| 类别 | 内容示例 | 来源 |
|------|---------|------|
| **用户偏好** | 喜欢简洁的回答、偏好用中文、股票关注美股科技 | 对话中提取 + 显式设置 |
| **对话历史** | 完整对话记录、关键对话摘要 | 自动保存 |
| **学习进度** | 英语单词掌握情况、学习计划完成度 | Agent 记录 |
| **知识积累** | 收集的资源、整理的笔记、学到的概念 | Notion 同步 + 对话提取 |
| **行为模式** | 常用的查询、工作习惯、使用时间 | 自动分析 |

### 2.3 记忆检索

```python
# 记忆检索策略
class MemoryRetrieval:
    def retrieve(self, query: str, context: Context) -> RelevantMemory:
        """
        检索相关记忆，用于增强 AI 回答
        """
        memories = []

        # 1. 最近的对话历史（时间相关性）
        memories += self.get_recent_history(limit=10)

        # 2. 用户偏好（始终相关）
        memories += self.get_user_preferences()

        # 3. 语义相关的历史内容（向量检索）
        if self.vector_db:
            memories += self.vector_search(query, top_k=5)

        # 4. Agent 特定的状态
        memories += self.get_agent_state(context.current_agent)

        return self.rank_and_filter(memories)
```

---

## 3. 自动化任务系统

### 3.1 任务类型

```
┌─────────────────────────────────────────────────────────────┐
│                      自动化任务                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  定时任务 (Scheduled Tasks)                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 类型        │ 示例                                     │ │
│  ├─────────────┼─────────────────────────────────────────┤ │
│  │ 每日        │ 早报：股票行情 + 今日待办 + 天气         │ │
│  │ 每周        │ 周报：学习总结 + 投资回顾                │ │
│  │ 每月        │ 月度复盘：目标完成度 + 知识图谱更新       │ │
│  │ 自定义      │ 每天 9:30 检查股票开盘情况               │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  事件触发 (Event Triggers)                                  │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 触发条件                │ 动作                         │ │
│  ├─────────────────────────┼─────────────────────────────┤ │
│  │ AAPL 股价 < $150       │ 发送提醒 + 分析原因          │ │
│  │ Notion 新增页面         │ 自动分类 + 打标签            │ │
│  │ 收到新的学习资源        │ 整理入库 + 生成摘要          │ │
│  │ 连续 3 天未学习英语     │ 发送提醒                    │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 技术实现

```python
# 任务调度器
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class TaskScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.event_bus = EventBus()

    # 定时任务
    def schedule_cron(self, task_id: str, cron: str, handler: Callable):
        """
        添加定时任务
        cron: "0 9 * * *"  # 每天 9:00
        """
        self.scheduler.add_job(handler, 'cron', **parse_cron(cron), id=task_id)

    # 事件触发
    def register_trigger(self, trigger: Trigger):
        """
        注册事件触发器
        """
        self.event_bus.subscribe(trigger.event_type, trigger.condition, trigger.handler)

# 触发器示例
class StockPriceTrigger(Trigger):
    event_type = "stock_price_update"

    def condition(self, event: StockEvent) -> bool:
        return event.symbol == "AAPL" and event.price < 150

    async def handler(self, event: StockEvent):
        await self.notify_user(f"AAPL 跌破 $150，当前 ${event.price}")
        await self.analyze_reason(event.symbol)
```

---

## 4. Notion 集成设计

### 4.1 集成范围

**决策**：完全双向同步

```
┌─────────────────────────────────────────────────────────────┐
│                    Notion 集成架构                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐         ┌─────────────────────────────┐   │
│  │   Assistant │ ←────── │      Notion Workspace       │   │
│  │             │ ──────→ │                             │   │
│  └─────────────┘         │  ┌─────────────────────┐   │   │
│        ↑↓                │  │ Notes Database       │   │   │
│   双向同步               │  │ - 笔记               │   │   │
│                          │  │ - 学习资料           │   │   │
│  读取:                   │  └─────────────────────┘   │   │
│  - 搜索笔记内容          │                             │   │
│  - 查询数据库            │  ┌─────────────────────┐   │   │
│  - 获取页面详情          │  │ Resources Database  │   │   │
│                          │  │ - 收藏的链接         │   │   │
│  写入:                   │  │ - 工具/软件          │   │   │
│  - 创建新页面            │  └─────────────────────┘   │   │
│  - 更新页面内容          │                             │   │
│  - 添加数据库条目        │  ┌─────────────────────┐   │   │
│  - 管理标签/属性         │  │ Learning Database   │   │   │
│                          │  │ - 英语学习记录       │   │   │
│  监听:                   │  │ - 成长目标           │   │   │
│  - Webhook (如果可用)    │  └─────────────────────┘   │   │
│  - 定时轮询              │                             │   │
│                          └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 数据库映射

| Notion Database | 用途 | 主要字段 |
|-----------------|------|---------|
| Notes | 笔记存储 | Title, Content, Tags, Category, Created |
| Resources | 资源收集 | URL, Title, Type, Tags, Summary, Status |
| Learning | 学习记录 | Topic, Progress, Last Review, Next Review |
| Tasks | 待办任务 | Title, Status, Due Date, Priority |
| Investments | 投资记录 | Symbol, Action, Price, Date, Notes |

### 4.3 同步策略

```python
class NotionSyncService:
    """Notion 同步服务"""

    async def sync_to_notion(self, data_type: str, data: dict):
        """推送数据到 Notion"""
        database_id = self.get_database_id(data_type)
        await self.notion.pages.create(
            parent={"database_id": database_id},
            properties=self.map_to_notion_properties(data)
        )

    async def sync_from_notion(self, database_id: str, since: datetime = None):
        """从 Notion 拉取数据"""
        filter = {"timestamp": "last_edited_time", "after": since} if since else None
        results = await self.notion.databases.query(database_id, filter=filter)
        return [self.map_from_notion(page) for page in results]

    async def watch_changes(self):
        """监听 Notion 变更（定时轮询）"""
        while True:
            for db_id in self.watched_databases:
                changes = await self.sync_from_notion(db_id, since=self.last_sync)
                for change in changes:
                    await self.event_bus.emit("notion_change", change)
            await asyncio.sleep(60)  # 每分钟检查一次
```

---

## 5. 多模型支持

### 5.1 模型配置

| 模型 | 用途 | 特点 |
|------|------|------|
| **Claude** | 默认主力模型 | 推理强、安全、支持长文本 |
| **DeepSeek** | 代码生成 | 代码能力强、成本低 |
| **Gemini** | 多模态任务 | 支持图片、视频 |
| **Grok** | 实时信息 | 有 X/Twitter 数据 |
| **GPT-4** | 备选 | 生态丰富 |

### 5.2 模型选择策略

```python
class ModelSelector:
    """智能模型选择"""

    def select(self, task_type: str, context: Context) -> str:
        """
        根据任务类型选择最合适的模型
        """
        rules = {
            "code_generation": "deepseek",
            "code_review": "claude",
            "general_chat": "claude",
            "image_analysis": "gemini",
            "realtime_news": "grok",
            "complex_reasoning": "claude",
            "translation": "deepseek",  # 成本考虑
        }

        # 用户可以覆盖默认选择
        if context.user_model_preference:
            return context.user_model_preference

        return rules.get(task_type, "claude")
```

### 5.3 多模型对比

```python
async def multi_model_compare(self, prompt: str, models: List[str]) -> Dict[str, str]:
    """
    同一问题发送给多个模型，返回对比结果
    """
    tasks = {model: self.llm.chat(prompt, model=model) for model in models}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    return dict(zip(tasks.keys(), results))
```

---

## 6. Agent 定义

### 6.1 Agent 列表

| ID | 名称 | 职责 | 核心 Tools |
|----|------|------|-----------|
| `general` | 通用助手 | 闲聊、无法归类的问题 | web_search |
| `note_manager` | 笔记管理 | Notion 读写、笔记整理 | notion_* |
| `dev_assistant` | 开发助手 | 代码生成、技术问答 | code_execute, file_ops |
| `investment` | 投资顾问 | 股票分析、行情查询 | stock_*, news_search |
| `growth_coach` | 成长教练 | 目标管理、学习计划 | notion_*, schedule |
| `resource_collector` | 资源收集 | 链接保存、资源整理 | web_fetch, notion_* |
| `english_tutor` | 英语老师 | 英语学习辅导 | (待整合) |

### 6.2 Agent 能力矩阵

```
                    │ Notion │ Stock │ Code │ Web │ File │ Schedule │
────────────────────┼────────┼───────┼──────┼─────┼──────┼──────────┤
general             │   -    │   -   │  -   │  ✓  │  -   │    -     │
note_manager        │   ✓    │   -   │  -   │  -  │  -   │    -     │
dev_assistant       │   -    │   -   │  ✓   │  ✓  │  ✓   │    -     │
investment          │   ✓    │   ✓   │  -   │  ✓  │  -   │    ✓     │
growth_coach        │   ✓    │   -   │  -   │  -  │  -   │    ✓     │
resource_collector  │   ✓    │   -   │  -   │  ✓  │  -   │    -     │
english_tutor       │   ✓    │   -   │  -   │  -  │  -   │    ✓     │
```

---

## 7. 技术选型确认

### 7.1 后端

| 组件 | 选择 | 理由 |
|------|------|------|
| 框架 | FastAPI | 异步、高性能、自动文档 |
| 数据库 | SQLite | 简单、本地、够用 |
| 向量数据库 | ChromaDB (可选) | 语义搜索、记忆检索 |
| 任务调度 | APScheduler | 轻量、支持 cron |
| 消息队列 | 内存队列 (初期) | MVP 阶段足够 |

### 7.2 前端

| 组件 | 选择 | 理由 |
|------|------|------|
| 框架 | React 18 | 生态成熟 |
| 语言 | TypeScript | 类型安全 |
| 构建 | Vite | 快速 |
| UI | shadcn/ui + Tailwind | 美观、可定制 |
| 状态 | Zustand | 简单 |

### 7.3 外部服务

| 服务 | 提供商 | 用途 |
|------|--------|------|
| Notion | Notion API | 笔记管理 |
| 股票数据 | Alpha Vantage / Yahoo Finance | 美股行情 |
| AI 模型 | Claude/DeepSeek/Gemini/Grok | 智能对话 |

---

## 8. 开发计划

### 8.1 Phase 1: 核心框架 (Week 1-2)

**目标**：搭建多 Agent 框架，能跑通基本对话

- [ ] Agent 基类和 Router
- [ ] Intent Classifier
- [ ] Context Manager（基础版）
- [ ] LLM Service（复用现有代码）
- [ ] 基础 API 和 WebSocket
- [ ] 前端聊天界面

**验收**：能和 General Agent 对话，AI 能自动路由

### 8.2 Phase 2: Notion 集成 (Week 2-3)

**目标**：Note Manager Agent 完整可用

- [ ] Notion Client 封装
- [ ] Notion Tools (search, create, update, query)
- [ ] Note Manager Agent
- [ ] 双向同步机制
- [ ] 前端 Notion 相关 UI

**验收**：能通过对话操作 Notion

### 8.3 Phase 3: 其他 Agent (Week 3-5)

**目标**：所有 Agent 基本可用

- [ ] Dev Assistant Agent + Code Tools
- [ ] Investment Agent + Stock API
- [ ] Growth Coach Agent
- [ ] Resource Collector Agent
- [ ] 各 Agent 的 Prompt 调优

**验收**：所有 Agent 能响应相关请求

### 8.4 Phase 4: 记忆和自动化 (Week 5-6)

**目标**：完善记忆系统和自动化任务

- [ ] 长期记忆存储
- [ ] 记忆检索机制
- [ ] 定时任务调度器
- [ ] 事件触发系统
- [ ] 用户偏好学习

**验收**：AI 能记住用户偏好，能执行自动化任务

### 8.5 Phase 5: 英语整合 + 优化 (Week 6-8)

**目标**：整合英语项目，全面优化

- [ ] English Tutor Agent 整合
- [ ] 多模型对比功能
- [ ] UI/UX 优化
- [ ] 性能优化
- [ ] 测试和文档

---

## 9. 风险和应对

| 风险 | 影响 | 应对 |
|------|------|------|
| Notion API 限制 | 中 | 缓存 + 批量操作 |
| LLM 成本 | 高 | 智能模型选择 + 缓存 |
| 股票 API 限制 | 中 | 多数据源 + 缓存 |
| Intent 识别不准 | 中 | 用户可手动指定 + 反馈学习 |
| 记忆系统复杂度 | 高 | 分阶段实现，先简单后复杂 |

---

**文档结束**

下一步：开始编码实现
