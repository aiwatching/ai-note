# 会话记忆摘要 (2026-01-24)

## 已完成的功能

### 1. AI 多模型聊天功能
- 支持 Claude、DeepSeek、Gemini、Grok 四个 AI 提供商
- 可同时选择多个模型并行回答
- 可关联笔记作为上下文

### 2. 聊天历史保存与管理
- 新增数据库模型：`ChatSession`、`ChatMessage`（`app/models/chat.py`）
- 对话自动保存到数据库
- 支持查看历史、继续对话、编辑标题、归档、删除
- 支持导出对话为笔记

### 3. 笔记与聊天的双向链接
- 聊天页面：关联笔记显示为可点击链接，跳转到笔记详情
- 笔记详情页：显示"关联的 AI 对话"区域，点击可跳转到对应聊天
- API：`GET /api/v1/chat/by-note/{note_id}`

## 关键文件变更

### 后端
- `src/service/app/models/chat.py` - 新增，聊天数据模型
- `src/service/app/schemas/chat_schema.py` - 更新，添加会话相关 schema
- `src/service/app/services/chat_service.py` - 更新，添加会话管理方法
- `src/service/app/api/chat.py` - 更新，添加会话管理 API
- `src/service/app/ai/gemini_service.py` - 新增，Gemini 服务
- `src/service/app/ai/grok_service.py` - 新增，Grok 服务

### 前端
- `src/frontend/src/services/chatService.ts` - 更新，添加会话 API
- `src/frontend/src/pages/Chat/index.tsx` - 更新，完整聊天 UI
- `src/frontend/src/components/NoteDetail/index.tsx` - 更新，显示关联对话

## 数据库新增表
- `chat_sessions` - 聊天会话
- `chat_messages` - 聊天消息
- `chat_note_association` - 会话与笔记的关联表

## 需要注意
- 重启后端服务以创建新的数据库表
- 在 `.env` 中配置 AI 提供商的 API Key：
  - `CLAUDE_API_KEY`
  - `DEEPSEEK_API_KEY`
  - `GEMINI_API_KEY`
  - `GROK_API_KEY`

## 之前会话完成的功能
- 中文标题相似度算法（n-gram）
- 手动笔记关联功能
- 笔记关系建议 UI
