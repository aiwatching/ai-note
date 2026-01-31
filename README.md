# Personal AI Assistant

个人 AI 助手 - 自研多 Agent 框架

## 架构

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│    用户 ──→ 主 Agent ──→ Tools ──→ 结果            │
│                                                     │
│  核心组件:                                          │
│  ├── Agent: 对话管理 + 工具调用                     │
│  ├── LLM Service: 多模型支持 (Claude, DeepSeek)    │
│  ├── Tools: 可扩展的工具系统                        │
│  └── Memory: SQLite 持久化存储                      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 后端

```bash
cd src/backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 API Key

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 2. 前端

```bash
cd src/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:5173

## 配置

在 `src/backend/.env` 中配置：

```env
# LLM API Keys (至少配置一个)
CLAUDE_API_KEY=your_key
DEEPSEEK_API_KEY=your_key

# 默认模型
DEFAULT_MODEL=claude
```

## 项目结构

```
src/
├── backend/                 # Python 后端
│   └── app/
│       ├── agent/          # Agent 核心
│       ├── llm/            # LLM 服务
│       ├── tools/          # 工具系统
│       ├── memory/         # 记忆系统
│       ├── api/            # API 路由
│       └── main.py         # 入口
│
└── frontend/               # React 前端
    └── src/
        ├── components/
        ├── services/
        ├── store/
        └── App.tsx
```

## 添加自定义工具

```python
from app.core.deps import get_agent

agent = get_agent()

@agent.tool()
async def my_tool(param: str) -> str:
    """工具描述

    Args:
        param: 参数描述
    """
    return f"结果: {param}"
```

## API

- `POST /api/chat` - 发送消息
- `POST /api/chat/stream` - 流式发送
- `GET /api/chat/models` - 获取可用模型
- `GET /api/conversations` - 获取对话列表
- `GET /api/conversations/{id}` - 获取对话详情
- `DELETE /api/conversations/{id}` - 删除对话

## 开发计划

- [x] 基础 Agent 框架
- [x] 多模型支持 (Claude, DeepSeek)
- [x] 工具系统
- [x] 记忆系统
- [ ] Notion 集成
- [ ] 股票 API 集成
- [ ] 定时任务
- [ ] 更多 LLM 支持 (Gemini, Grok)
