# Personal AI Assistant - 简化设计

## 一句话描述

**一个 AI 助手 + 多种工具能力 + 可创建子 Agent**

---

## 系统架构

```
用户 ──→ 主 Agent ──→ 工具/子Agent ──→ 结果
              │
              ├── 直接回答（简单问题）
              ├── 调用工具（需要外部数据/操作）
              └── 创建子 Agent（复杂多步骤任务）
```

---

## 主 Agent 的能力

### 1. 直接对话
- 闲聊、问答、翻译、写作
- 不需要外部工具的任务

### 2. 调用工具 (Tools)

| 工具 | 功能 | 用于 |
|------|------|------|
| `notion_search` | 搜索 Notion | 查找笔记 |
| `notion_create` | 创建页面 | 新建笔记 |
| `notion_update` | 更新页面 | 修改笔记 |
| `notion_query_db` | 查询数据库 | 获取结构化数据 |
| `stock_quote` | 查询股价 | 获取实时行情 |
| `stock_history` | 历史数据 | K线、走势 |
| `stock_news` | 相关新闻 | 舆情分析 |
| `web_search` | 搜索网页 | 获取最新信息 |
| `web_fetch` | 抓取网页 | 保存资源 |
| `code_execute` | 执行代码 | 数据处理、计算 |
| `schedule_task` | 定时任务 | 自动化 |

### 3. 创建子 Agent
当任务复杂时，主 Agent 可以创建临时子 Agent：

```
用户: "帮我分析一下苹果最近一个月的走势，写一份报告保存到 Notion"

主 Agent 思考:
  这是一个复杂任务，需要：
  1. 获取股票数据
  2. 分析走势
  3. 生成报告
  4. 保存到 Notion

主 Agent 决定:
  创建一个"股票分析"子 Agent 来处理

子 Agent 执行:
  → stock_history("AAPL", "1month")
  → 分析数据，生成报告
  → notion_create(报告内容)
  → 返回结果
```

---

## 工具详细设计

### Notion 工具集

```python
# 搜索笔记
notion_search(query: str) -> List[Page]
  "搜索我关于 Python 的笔记"

# 创建页面
notion_create(
    database: str,     # 数据库名称
    title: str,        # 标题
    content: str,      # 内容
    properties: dict   # 属性（标签、分类等）
) -> Page
  "创建一个新笔记，标题是xxx"

# 更新页面
notion_update(page_id: str, content: str) -> Page
  "在这个笔记里加一段内容"

# 查询数据库
notion_query_db(
    database: str,
    filter: dict,
    sort: dict
) -> List[Page]
  "显示我这周创建的所有笔记"
```

### 股票工具集

```python
# 实时行情
stock_quote(symbol: str) -> Quote
  "苹果现在股价多少"
  返回: {"symbol": "AAPL", "price": 185.5, "change": "+1.2%"}

# 历史数据
stock_history(
    symbol: str,
    period: str  # "1day", "1week", "1month", "1year"
) -> List[OHLCV]
  "苹果最近一个月的走势"

# 新闻
stock_news(symbol: str, limit: int = 10) -> List[News]
  "苹果最近有什么新闻"
```

### Web 工具集

```python
# 搜索
web_search(query: str, limit: int = 10) -> List[Result]
  "搜索 Python 异步编程最佳实践"

# 抓取
web_fetch(url: str) -> Content
  "帮我保存这个链接的内容"
```

### 自动化工具

```python
# 创建定时任务
schedule_task(
    name: str,
    cron: str,           # "0 9 * * *" = 每天9点
    action: str,         # 要执行的操作描述
    notify: bool = True  # 是否通知用户
) -> Task
  "每天早上9点给我发一份股票简报"

# 创建触发器
create_trigger(
    name: str,
    condition: str,      # 触发条件描述
    action: str          # 触发后的操作
) -> Trigger
  "如果苹果跌破180，提醒我"
```

---

## 模型使用策略

### 选择原则

```
┌─────────────────────────────────────────────────────┐
│                   任务类型                           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  简单对话/翻译/摘要          复杂推理/工具调用        │
│        │                           │               │
│        ↓                           ↓               │
│  ┌───────────┐              ┌───────────┐          │
│  │ DeepSeek  │              │  Claude   │          │
│  │   便宜    │              │   强大    │          │
│  └───────────┘              └───────────┘          │
│                                                     │
│  成本: $0.27/M               成本: $3/M             │
│  速度: 快                    速度: 中               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 自动模型选择

```python
def select_model(task):
    # 需要工具调用 → Claude（工具调用更稳定）
    if task.needs_tools:
        return "claude-sonnet"

    # 代码相关 → DeepSeek（代码能力强且便宜）
    if task.is_code_related:
        return "deepseek"

    # 简单对话 → DeepSeek（便宜）
    if task.is_simple_chat:
        return "deepseek"

    # 复杂推理 → Claude
    return "claude-sonnet"
```

### 费用估算

**日常使用场景**（每天）：
- 10 次简单对话 (DeepSeek): ~2000 tokens × 10 = 20k tokens
- 5 次工具调用 (Claude): ~3000 tokens × 5 = 15k tokens
- 2 次复杂任务 (Claude): ~5000 tokens × 2 = 10k tokens

**月费用**：
- DeepSeek: 20k × 30 × $0.001 ≈ $0.6
- Claude: 25k × 30 × $0.01 ≈ $7.5
- **总计: 约 $8-10/月**

---

## 记忆系统

### 简单版本（MVP）

```python
# 只保存到 SQLite
memories = {
    "conversations": [...],      # 对话历史
    "user_preferences": {...},   # 用户偏好
    "frequently_used": [...],    # 常用操作
}
```

### 什么时候记忆

1. **对话历史**: 每次对话自动保存
2. **用户偏好**: 用户明确说出时记录
   - "我一般只关注科技股"
   - "回复尽量简短"
3. **使用习惯**: 自动学习
   - 常查的股票
   - 常用的 Notion 数据库

### 什么时候使用记忆

```python
def build_context(user_input):
    context = []

    # 1. 最近的对话
    context += get_recent_conversations(limit=5)

    # 2. 用户偏好
    context += get_user_preferences()

    # 3. 相关的历史（如果查股票，加入之前查过的记录）
    if is_stock_related(user_input):
        context += get_stock_history()

    return context
```

---

## 简单的目录结构

```
ai-assistant/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置
│   │
│   ├── agent/
│   │   ├── main_agent.py    # 主 Agent
│   │   └── sub_agent.py     # 子 Agent 基类
│   │
│   ├── tools/               # 工具实现
│   │   ├── notion.py        # Notion 工具
│   │   ├── stock.py         # 股票工具
│   │   ├── web.py           # Web 工具
│   │   └── scheduler.py     # 定时任务
│   │
│   ├── llm/                 # LLM 调用
│   │   ├── service.py       # 统一接口
│   │   ├── claude.py
│   │   └── deepseek.py
│   │
│   ├── memory/              # 记忆系统
│   │   ├── store.py         # 存储
│   │   └── retrieval.py     # 检索
│   │
│   └── api/                 # API 路由
│       └── chat.py
│
├── frontend/                # React 前端
│
└── data/
    └── assistant.db         # SQLite 数据库
```

---

## 开发顺序

### Week 1: 能对话
- [ ] 主 Agent + LLM 调用
- [ ] 基础 API
- [ ] 简单前端

### Week 2: 能用工具
- [ ] Notion 工具
- [ ] Stock 工具
- [ ] Tool calling 机制

### Week 3: 能记忆
- [ ] 对话历史保存
- [ ] 用户偏好存储
- [ ] 上下文构建

### Week 4: 能自动化
- [ ] 定时任务
- [ ] 事件触发
- [ ] 通知机制

### Week 5+: 优化
- [ ] 子 Agent 机制
- [ ] 模型选择优化
- [ ] UI 完善

---

## 这个设计的好处

1. **简单**: 一个主 Agent，不需要复杂的路由
2. **灵活**: 工具可以随时增加
3. **省钱**: 智能选择模型
4. **可扩展**: 需要时可以创建子 Agent

---

## 示例对话

```
用户: 苹果现在多少钱？
AI: [调用 stock_quote("AAPL")]
    苹果(AAPL)当前股价 $185.50，今日涨幅 +1.2%

用户: 帮我记一下，185 是一个关键支撑位
AI: [调用 notion_create(...)]
    已保存到你的投资笔记中。要不要我设置一个提醒，当苹果跌破 185 时通知你？

用户: 好的
AI: [调用 create_trigger(...)]
    已设置。当 AAPL < $185 时，我会通过 [通知方式] 提醒你。

用户: 每天早上给我发一份我关注的股票简报
AI: [调用 schedule_task(...)]
    已设置每日简报。每天早上 9:00 我会给你发送你关注的股票（AAPL, ...）的行情汇总。
```
