# AI Notes 项目上下文

## 项目概述
这是一个智能笔记系统，具备 AI 分析、多模型聊天、自动关联等功能。

## 技术栈
- **后端**: Python FastAPI, SQLAlchemy, SQLite
- **前端**: React + TypeScript + Vite, TailwindCSS, shadcn/ui
- **AI**: 支持 Claude, DeepSeek, Gemini, Grok 多模型

## 项目结构
```
src/
├── service/          # Python 后端
│   └── app/
│       ├── api/      # API 路由
│       ├── models/   # 数据库模型
│       ├── schemas/  # Pydantic schemas
│       ├── services/ # 业务逻辑
│       └── ai/       # AI 服务实现
└── frontend/         # React 前端
    └── src/
        ├── pages/        # 页面组件
        ├── components/   # 通用组件
        └── services/     # API 服务
```

## 最近完成的功能 (2026-01-24)

### 1. AI 多模型聊天
- 文件: `app/api/chat.py`, `app/services/chat_service.py`
- 支持同时向多个 AI 模型发送请求并行回答
- 可关联笔记作为上下文

### 2. 聊天历史保存
- 新增模型: `app/models/chat.py` (ChatSession, ChatMessage)
- 对话自动保存到数据库
- 支持查看历史、继续对话、导出为笔记

### 3. 笔记与聊天双向链接
- 聊天页面: 关联笔记可点击跳转
- 笔记详情: 显示关联的 AI 对话，点击跳转
- API: `GET /api/v1/chat/by-note/{note_id}`

### 4. 中文笔记相似度
- 使用 n-gram 算法计算中文标题相似度
- 手动笔记关联功能

## 数据库表
- `notes` - 笔记
- `todos` - 待办事项
- `schedules` - 日程
- `chat_sessions` - 聊天会话 (新增)
- `chat_messages` - 聊天消息 (新增)
- `chat_note_association` - 会话笔记关联 (新增)

## API 端点
- `/api/v1/notes` - 笔记 CRUD
- `/api/v1/chat` - AI 聊天
- `/api/v1/chat/sessions` - 聊天会话管理
- `/api/v1/chat/by-note/{id}` - 获取笔记关联的聊天
- `/api/v1/search` - 搜索
- `/api/v1/todos` - 待办事项

## 配置
环境变量在 `.env` 文件中配置:
- `AI_SERVICE` - 默认 AI 服务
- `CLAUDE_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GROK_API_KEY`

## 启动命令
```bash
# 后端
cd src/service && python -m uvicorn app.main:app --reload

# 前端
cd src/frontend && npm run dev
```

## 待处理/已知问题
- 重启后端服务以创建新的聊天相关数据库表
