# AI Assistant 项目上下文

## 项目概述
个人 AI 助手系统，自研多 Agent 框架，支持多模型、工具调用、子 Agent 协作。

## 技术栈
- **后端**: Python FastAPI, SQLite
- **前端**: React + TypeScript + Vite, TailwindCSS
- **AI**: 支持 Claude, DeepSeek, OpenAI, Grok 多模型

## Current Project Structure (v2.0)
```
src/backend/app/
├── agent/                    # Agent Core
│   ├── core.py              # Agent, Skill, AgentCard classes
│   ├── loader.py            # YAML frontmatter loader (OpenClaw-style)
│   └── configs/             # Agent config files
│       ├── main.md          # Main orchestrator agent
│       ├── stock.md         # Stock analysis agent
│       ├── note.md          # Note management agent
│       ├── dev.md           # Development assistant agent
│       └── notify.md        # Notification agent
├── channels/                # Notification Channels (OpenClaw-inspired)
│   ├── base.py              # BaseChannel, ChannelRegistry
│   ├── telegram.py          # Telegram Bot API
│   ├── discord.py           # Discord webhook/bot
│   ├── webhook.py           # Generic webhook, Slack
│   └── notification.py      # NotificationService
├── llm/                     # Multi-model LLM support
│   ├── base.py              # BaseLLMProvider
│   ├── claude.py            # Claude implementation
│   ├── deepseek.py          # DeepSeek implementation
│   ├── openai.py            # OpenAI implementation
│   ├── grok.py              # Grok implementation
│   └── service.py           # LLMService unified interface
├── tools/                   # Tool system
│   ├── base.py              # Tool class
│   └── registry.py          # Tool registry
├── memory/                  # Memory system
│   ├── models.py            # Message, Conversation
│   └── store.py             # SQLiteMemory
├── api/                     # API routes
│   ├── chat.py
│   ├── conversations.py
│   └── notifications.py     # Notification endpoints
├── core/deps.py             # Dependency injection
├── config.py                # Configuration
└── main.py                  # FastAPI entry point
```

## Agent/Skill 设计经验 (学习自 OpenClaw)

### 1. Skill 配置格式
使用 **YAML frontmatter + Markdown**，结构清晰易维护：

```yaml
---
name: stock
description: 股票分析专家
provider: deepseek
requires:
  env: ["ALPHA_VANTAGE_KEY"]    # 必需的环境变量
  bins: ["some-cli"]            # 必需的二进制
  os: ["darwin", "linux"]       # 支持的操作系统
install:
  - kind: pip
    package: yfinance
---

## System Prompt
你是专业的股票分析师...

## Skills
### 行情查询
查询股票实时价格

## Tools
- stock_quote
- stock_news
```

### 2. 三层加载优先级
```
优先级（高到低）：
1. workspace: <project>/skills/    # 项目级（最高）
2. managed:   ~/.ai-assistant/skills/   # 用户安装
3. bundled:   dist/skills/         # 内置
```
同名 Skill，workspace 覆盖 managed，managed 覆盖 bundled。

### 3. Skill 资格检查
加载前检查 Skill 是否可用：
```python
def should_include_skill(entry, config, context):
    # 检查 OS
    if requires.os and platform not in requires.os:
        return False
    # 检查二进制
    if requires.bins and not all_bins_exist(requires.bins):
        return False
    # 检查环境变量
    if requires.env and not all_envs_exist(requires.env):
        return False
    # 检查允许/禁止列表
    if config.skills.deny and name in config.skills.deny:
        return False
    return True
```

### 4. 工具分组策略
```python
TOOL_GROUPS = {
    "group:fs": ["read", "write", "edit"],
    "group:web": ["web_search", "web_fetch"],
    "group:runtime": ["exec", "process"],
    "group:stock": ["stock_quote", "stock_news"],
}

TOOL_PROFILES = {
    "minimal": {"allow": ["get_current_time"]},
    "coding": {"allow": ["group:fs", "group:runtime"]},
    "stock": {"allow": ["group:stock", "group:web"]},
    "full": {},  # 允许全部
}
```

### 5. 模型选择策略
按任务类型自动选择模型，降低费用：
```python
# 费用排序（从便宜到贵）
MODEL_COST_RANKING = {
    "deepseek": 1,    # 最便宜，代码能力强
    "grok": 2,        # grok-2-mini 便宜
    "openai": 3,      # gpt-4o-mini 中等
    "claude": 4,      # 最贵但最强
}

# 任务类型 -> 模型
TASK_PROVIDER_MAP = {
    "simple": cheapest,
    "chat": cheapest,
    "code": "deepseek",
    "complex": "claude",
}
```

### 6. 模型故障转移
```python
FAILOVER_CHAIN = ["deepseek", "grok", "openai", "claude"]
PROFILE_COOLDOWN = 60  # 失败后冷却秒数

async def chat_with_failover(message, providers):
    for provider in providers:
        if is_in_cooldown(provider):
            continue
        try:
            return await llm.chat(message, provider=provider)
        except (AuthError, RateLimitError):
            mark_failed(provider)
    raise AllProvidersFailedError()
```

### 7. Workspace 上下文注入
首轮对话注入这些文件作为 Agent 记忆：
```
~/.ai-assistant/
├── AGENTS.md      # Agent 全局指令
├── USER.md        # 用户偏好画像
└── MEMORY.md      # 长期记忆
```

### 8. 设计原则
1. **Skill 是知识库** — Markdown 文档描述能力和使用方法
2. **requires 是门卫** — 运行前检查依赖可用性
3. **三层优先级** — 允许项目级覆盖全局配置
4. **工具策略** — 细粒度控制 Agent 能力
5. **模型故障转移** — 自动处理 API 失败
6. **费用优先** — 简单任务用便宜模型

## 启动命令
```bash
# 后端
cd src/backend && uvicorn app.main:app --reload --port 8000

# 前端
cd src/frontend && npm run dev
```

## Configuration (.env)
```env
# LLM Providers
CLAUDE_API_KEY=sk-xxx
DEEPSEEK_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx
GROK_API_KEY=xai-xxx
DEFAULT_MODEL=deepseek

# Notification Channels
TELEGRAM_BOT_TOKEN=123456:ABC-xxx
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

## Notification System (OpenClaw-inspired)

### Channel Architecture
```
┌─────────────────────────────────────────────┐
│           NotificationService               │
├─────────────────────────────────────────────┤
│  configure_from_env()                       │
│  notify(Notification) → NotificationResult  │
│  send_reminder() / send_alert()             │
└───────────────┬─────────────────────────────┘
                │
        ┌───────┴───────┐
        │ ChannelRegistry │
        └───────┬───────┘
                │
    ┌───────┬───┴───┬───────┐
    ▼       ▼       ▼       ▼
Telegram  Discord  Slack  Webhook
```

### Usage
```python
from app.channels import notification_service, Notification

# Auto-configure from env
notification_service.configure_from_env()

# Send notification
result = await notification_service.notify(Notification(
    title="Reminder",
    message="Meeting in 10 minutes!",
    priority="high",
    channels=["telegram"]
))
```

### API Endpoints
```
GET  /api/notifications/channels   - List configured channels
POST /api/notifications/send       - Send notification
POST /api/notifications/reminder   - Send reminder
POST /api/notifications/alert      - Send alert
POST /api/notifications/test       - Test channel
GET  /api/notifications/telegram/info    - Get bot info
GET  /api/notifications/telegram/updates - Get updates (find chat ID)
```

### Setup Telegram Bot
1. Message @BotFather on Telegram, send `/newbot`
2. Copy the bot token to `TELEGRAM_BOT_TOKEN`
3. Message @userinfobot to get your chat ID
4. Set `TELEGRAM_CHAT_ID`
5. Start your bot by sending `/start` to it

## Pending Features
- [x] Skill requires checks (bins/env/os) ✓
- [ ] Three-tier Skill loading mechanism
- [ ] Tool groups and profiles
- [ ] Model failover with cooldown
- [ ] Workspace context injection
- [ ] Notion API integration
- [ ] Stock API integration
- [ ] Scheduled notifications/reminders
