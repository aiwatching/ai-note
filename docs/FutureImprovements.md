# 未来功能改进计划

## 后台 Agent 系统

计划实现一个多 Agent 后台系统，由主调度 Agent 统一管理，各个子 Agent 负责独立任务。

### 架构设计

```
┌─────────────────────────────────────────┐
│           主调度 Agent                   │
│    (Master Scheduler Agent)             │
├─────────────────────────────────────────┤
│  负责任务分发、状态监控、Agent 生命周期   │
└──────────────┬──────────────────────────┘
               │
       ┌───────┼───────┐
       │       │       │
       ▼       ▼       ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Schedule │ │ Content  │ │  其他    │
│  Agent   │ │  Agent   │ │  Agent   │
└──────────┘ └──────────┘ └──────────┘
```

### 1. Schedule Agent (日程管理 Agent)

**职责:**
- 日程调度管理
- 提醒通知发送
- 冲突检测
- 智能时间建议

**功能详情:**
- [ ] 监控所有日程事件
- [ ] 根据设定的提醒时间发送通知
- [ ] 检测日程冲突并提醒用户
- [ ] 根据用户习惯智能建议最佳时间
- [ ] 定期同步外部日历（可选）

### 2. Content Organization Agent (内容整理 Agent)

**职责:**
- 相关笔记关联
- 内容聚合
- 知识图谱构建
- 自动标签优化

**功能详情:**
- [ ] 分析笔记内容相似度
- [ ] 将相关笔记自动关联
- [ ] 构建知识图谱，展示笔记间关系
- [ ] 优化和统一标签体系
- [ ] 定期生成内容摘要报告

### 3. 待补充 Agent

预留位置，后续根据需求添加：

- [ ] **提醒 Agent**: 智能提醒，根据笔记内容识别需要提醒的事项
- [ ] **报告生成 Agent**: 定期生成周报/月报/项目报告
- [ ] **数据备份 Agent**: 自动备份和数据同步
- [ ] **学习 Agent**: 根据学习笔记生成复习计划和知识卡片

---

## 技术实现方案

### Agent 框架选型
- Python asyncio 实现异步任务
- Celery/APScheduler 定时任务调度
- Redis 作为消息队列（可选）

### Agent 通信机制
- 内部事件总线
- 消息队列
- 共享状态存储

### 部署方案
- 单独进程运行
- Docker 容器化部署
- 可选的分布式部署

---

## 已实现功能

### Agent 框架 (v1.0)

已完成基础 Agent 框架的搭建：

```
src/service/app/agents/
├── __init__.py        # 模块导出
├── base.py            # BaseAgent 抽象基类
├── event_bus.py       # 事件总线，支持发布-订阅模式
├── scheduler.py       # MasterScheduler 主调度器
├── schedule_agent.py  # 日程管理 Agent
└── content_agent.py   # 内容整理 Agent
```

#### 核心功能

1. **BaseAgent 基类**
   - 异步任务循环
   - 生命周期管理 (start/stop/pause/resume)
   - 状态监控和错误处理
   - 元数据存储

2. **EventBus 事件总线**
   - 发布-订阅模式
   - 异步事件处理
   - 事件历史记录
   - 支持多种事件类型

3. **MasterScheduler 主调度器**
   - Agent 注册和管理
   - 健康监控和自动重启
   - 系统级事件广播

4. **Schedule Agent**
   - 日程提醒发送
   - 冲突检测
   - 时间槽建议

5. **Content Agent**
   - 笔记相似度分析
   - 相关笔记推荐
   - 标签优化建议
   - 每日摘要生成

#### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/agents/status` | GET | 获取 Agent 系统状态 |
| `/api/v1/agents/start` | POST | 启动 Agent 系统 |
| `/api/v1/agents/stop` | POST | 停止 Agent 系统 |
| `/api/v1/agents/agents/{name}/start` | POST | 启动指定 Agent |
| `/api/v1/agents/agents/{name}/stop` | POST | 停止指定 Agent |
| `/api/v1/agents/events/history` | GET | 获取事件历史 |
| `/api/v1/agents/schedule/upcoming` | GET | 获取即将到来的日程 |
| `/api/v1/agents/content/related/{id}` | GET | 获取相关笔记 |
| `/api/v1/agents/content/tags` | GET | 获取标签统计 |

#### 配置项

在 `.env` 文件中添加：

```env
AUTO_START_AGENTS=false          # 是否自动启动 Agent
AGENT_SCHEDULE_INTERVAL=60       # Schedule Agent 检查间隔(秒)
AGENT_CONTENT_INTERVAL=300       # Content Agent 分析间隔(秒)
```

---

## 更新记录

| 日期 | 更新内容 |
|------|----------|
| 2026-01-20 | 初始化文档，添加 Agent 系统规划 |
| 2026-01-20 | 完成 Agent 框架基础实现 |
