# 智能笔记系统 - 技术架构文档

**版本**: v1.0  
**创建日期**: 2026-01-19  
**文档状态**: 待评审

---

## 1. 架构概述

### 1.1 整体架构
采用前后端分离架构，前端和后端独立开发、部署，通过 RESTful API 进行通信。

```
┌─────────────────────────────────────────────────────────┐
│                     客户端层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Web 前端    │  │  桌面客户端   │  │  移动端(未来)│  │
│  │  (React)     │  │  (Electron)   │  │             │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↓ HTTP/REST API
┌─────────────────────────────────────────────────────────┐
│                     服务层                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │            Python FastAPI 后端服务                │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │   │
│  │  │ 笔记管理  │ │ AI 服务  │ │ Todo/Schedule   │ │   │
│  │  │  模块     │ │  模块    │ │     模块         │ │   │
│  │  └──────────┘ └──────────┘ └──────────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                     数据层                                │
│  ┌─────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ SQLite  │  │ Markdown     │  │ Elasticsearch    │   │
│  │ (元数据) │  │ (笔记内容)   │  │ (全文检索-可选)  │   │
│  └─────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   外部服务层                              │
│  ┌──────────────┐  ┌──────────────────────────────┐    │
│  │ Claude API   │  │  其他 AI 服务 (未来扩展)      │    │
│  └──────────────┘  └──────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### 1.2 设计原则
- **前后端分离**: 清晰的接口定义，便于多端扩展
- **模块化设计**: 各模块职责单一，低耦合高内聚
- **可扩展性**: AI 服务、数据库可插拔替换
- **本地优先**: MVP 版本本地运行，数据本地存储
- **渐进增强**: MVP 保持简单，为未来功能预留接口

---

## 2. 技术选型

### 2.1 前端技术栈

#### 核心框架
- **React 18** - UI 框架
    - 理由：生态成熟、组件丰富、性能优秀、社区活跃

#### UI 组件库
- **Ant Design** 或 **shadcn/ui**
    - Ant Design: 企业级组件库，开箱即用
    - shadcn/ui: 现代化设计，可定制性强
    - 推荐：**shadcn/ui** (更轻量、更灵活)

#### Markdown 编辑器
- **react-markdown-editor-lite** + **marked**
    - 支持实时预览
    - 支持 Markdown 语法
    - 轻量级

或者

- **CodeMirror 6** + **@uiw/react-codemirror**
    - 更强大的编辑功能
    - 语法高亮
    - 可扩展性强

#### 状态管理
- **Zustand** 或 **Redux Toolkit**
    - 推荐：**Zustand** (更简单、更轻量)

#### 路由
- **React Router v6**

#### HTTP 客户端
- **Axios**

#### 其他工具
- **date-fns** - 日期处理
- **react-query** - 服务端状态管理（可选）
- **tailwindcss** - CSS 框架

### 2.2 后端技术栈

#### 核心框架
- **Python 3.11+**
- **FastAPI** - Web 框架
    - 理由：性能优秀、自动生成 API 文档、类型提示、异步支持

#### 数据库
**MVP 版本**
- **SQLite** - 元数据存储（用户、配置、笔记索引、Todo、Schedule）
- **文件系统** - Markdown 文件存储（笔记原始内容和整理后内容）

**未来版本**
- **PostgreSQL** 或 **MongoDB** - 生产环境数据库
- 数据模型设计时考虑迁移性

#### 全文检索（可选）
- **Elasticsearch** - 本地部署
    - 理由：强大的全文检索、支持中文分词、灵活的查询 DSL
    - 备选：**Meilisearch** (更轻量、部署简单)

#### AI 服务
**MVP 版本**
- **Claude API** (Anthropic)
    - 模型：claude-sonnet-4-20250514

**接口设计**
- 抽象 AI Service 接口，支持未来扩展
- 预留对接：OpenAI、本地 LLM (Ollama)、其他 API

#### 其他依赖
- **SQLAlchemy** - ORM 框架
- **Pydantic** - 数据验证
- **python-dotenv** - 环境变量管理
- **anthropic** - Claude SDK
- **elasticsearch** - ES 客户端 (可选)
- **python-markdown** - Markdown 处理
- **jieba** - 中文分词 (用于搜索)
- **schedule** - 定时任务 (如自动备份)

### 2.3 开发工具

#### 前端
- **Vite** - 构建工具
- **TypeScript** - 类型安全
- **ESLint** + **Prettier** - 代码规范

#### 后端
- **Poetry** 或 **pip + requirements.txt** - 依赖管理
- **Black** - 代码格式化
- **Pylint** / **Flake8** - 代码检查
- **pytest** - 测试框架

#### 版本控制
- **Git**

---

## 3. 目录结构

```
ai-notes/
├── README.md
├── docs/                          # 文档目录
│   ├── PRD.md                     # 产品需求文档
│   ├── ARCHITECTURE.md            # 本架构文档
│   └── API.md                     # API 文档
├── src/
│   ├── frontend/                  # 前端项目
│   │   ├── public/
│   │   ├── src/
│   │   │   ├── components/        # 公共组件
│   │   │   │   ├── NoteEditor/    # 笔记编辑器
│   │   │   │   ├── SearchBar/     # 搜索栏
│   │   │   │   ├── TodoList/      # 待办列表
│   │   │   │   └── Calendar/      # 日历组件
│   │   │   ├── pages/             # 页面
│   │   │   │   ├── Home/          # 首页 - 快速记录
│   │   │   │   ├── Notes/         # 笔记列表
│   │   │   │   ├── Search/        # 搜索页面
│   │   │   │   ├── Todo/          # 待办页面
│   │   │   │   ├── Schedule/      # 日程页面
│   │   │   │   └── Settings/      # 设置页面
│   │   │   ├── services/          # API 服务
│   │   │   │   ├── api.ts         # API 基础配置
│   │   │   │   ├── noteService.ts
│   │   │   │   ├── todoService.ts
│   │   │   │   └── searchService.ts
│   │   │   ├── store/             # 状态管理
│   │   │   │   ├── noteStore.ts
│   │   │   │   ├── todoStore.ts
│   │   │   │   └── userStore.ts
│   │   │   ├── types/             # TypeScript 类型定义
│   │   │   ├── utils/             # 工具函数
│   │   │   ├── App.tsx
│   │   │   └── main.tsx
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── vite.config.ts
│   │
│   └── service/                   # 后端项目
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py            # FastAPI 应用入口
│       │   ├── config.py          # 配置管理
│       │   ├── database.py        # 数据库连接
│       │   │
│       │   ├── models/            # 数据模型
│       │   │   ├── __init__.py
│       │   │   ├── user.py
│       │   │   ├── note.py
│       │   │   ├── todo.py
│       │   │   └── schedule.py
│       │   │
│       │   ├── schemas/           # Pydantic 模式（请求/响应）
│       │   │   ├── __init__.py
│       │   │   ├── note_schema.py
│       │   │   ├── todo_schema.py
│       │   │   └── search_schema.py
│       │   │
│       │   ├── api/               # API 路由
│       │   │   ├── __init__.py
│       │   │   ├── notes.py       # 笔记相关 API
│       │   │   ├── search.py      # 搜索相关 API
│       │   │   ├── todos.py       # Todo 相关 API
│       │   │   ├── schedules.py   # 日程相关 API
│       │   │   └── settings.py    # 设置相关 API
│       │   │
│       │   ├── services/          # 业务逻辑层
│       │   │   ├── __init__.py
│       │   │   ├── note_service.py
│       │   │   ├── search_service.py
│       │   │   ├── todo_service.py
│       │   │   └── schedule_service.py
│       │   │
│       │   ├── ai/                # AI 服务模块
│       │   │   ├── __init__.py
│       │   │   ├── base.py        # AI 服务基类（抽象接口）
│       │   │   ├── claude_service.py  # Claude 实现
│       │   │   ├── factory.py     # AI 服务工厂
│       │   │   └── prompts/       # AI Prompt 模板
│       │   │       ├── classify.py
│       │   │       ├── extract.py
│       │   │       └── search.py
│       │   │
│       │   ├── storage/           # 存储层
│       │   │   ├── __init__.py
│       │   │   ├── markdown_storage.py  # Markdown 文件管理
│       │   │   ├── db_storage.py        # 数据库操作
│       │   │   └── search_index.py      # 搜索索引 (ES)
│       │   │
│       │   └── utils/             # 工具函数
│       │       ├── __init__.py
│       │       ├── markdown_utils.py
│       │       ├── date_utils.py
│       │       └── logger.py
│       │
│       ├── tests/                 # 测试
│       │   ├── test_api/
│       │   ├── test_services/
│       │   └── test_ai/
│       │
│       ├── requirements.txt       # Python 依赖
│       ├── .env.example           # 环境变量模板
│       └── pyproject.toml         # Poetry 配置（可选）
│
├── data/                          # 数据目录（gitignore）
│   ├── notes/                     # Markdown 笔记文件
│   │   ├── raw/                   # 原始笔记
│   │   └── organized/             # 整理后笔记
│   ├── database/                  # SQLite 数据库
│   │   └── notes.db
│   ├── backups/                   # 备份目录
│   └── logs/                      # 日志文件
│
├── scripts/                       # 工具脚本
│   ├── init_db.py                 # 初始化数据库
│   ├── backup.py                  # 备份脚本
│   └── migrate.py                 # 数据迁移脚本
│
├── .gitignore
└── docker-compose.yml             # Docker 配置（可选）
```

---

## 4. 数据模型设计

### 4.1 数据库表结构（SQLite MVP 版本）

#### 用户表 (users)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 配置表 (settings)
```sql
CREATE TABLE settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    key VARCHAR(100) NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, key)
);
```

#### 笔记索引表 (notes)
```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    
    -- 基本信息
    title VARCHAR(200),
    raw_file_path VARCHAR(500) NOT NULL,      -- 原始 Markdown 文件路径
    organized_file_path VARCHAR(500),         -- 整理后 Markdown 文件路径
    
    -- AI 分析结果
    category VARCHAR(50),                     -- 分类：学习笔记、工作记录等
    subcategory VARCHAR(50),                  -- 子分类
    tags JSON,                                -- 标签数组 ["Python", "装饰器"]
    summary TEXT,                             -- 摘要
    
    -- 特殊标记
    is_todo BOOLEAN DEFAULT 0,                -- 是否包含待办
    is_schedule BOOLEAN DEFAULT 0,            -- 是否包含日程
    priority VARCHAR(20),                     -- 优先级：high/medium/low
    status VARCHAR(20) DEFAULT 'active',      -- 状态：active/archived/deleted
    
    -- 关联信息
    related_persons JSON,                     -- 相关人物 ["张三", "李四"]
    related_dates JSON,                       -- 相关日期
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 索引
CREATE INDEX idx_notes_user_id ON notes(user_id);
CREATE INDEX idx_notes_category ON notes(category);
CREATE INDEX idx_notes_created_at ON notes(created_at);
CREATE INDEX idx_notes_status ON notes(status);
```

#### 待办表 (todos)
```sql
CREATE TABLE todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    note_id INTEGER,                          -- 关联的笔记 ID
    
    -- 待办信息
    title VARCHAR(200) NOT NULL,
    description TEXT,
    due_date DATE,
    priority VARCHAR(20) DEFAULT 'medium',    -- high/medium/low
    status VARCHAR(20) DEFAULT 'pending',     -- pending/in_progress/completed/cancelled
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (note_id) REFERENCES notes(id)
);

-- 索引
CREATE INDEX idx_todos_user_id ON todos(user_id);
CREATE INDEX idx_todos_status ON todos(status);
CREATE INDEX idx_todos_due_date ON todos(due_date);
```

#### 日程表 (schedules)
```sql
CREATE TABLE schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    note_id INTEGER,                          -- 关联的笔记 ID
    
    -- 日程信息
    title VARCHAR(200) NOT NULL,
    description TEXT,
    location VARCHAR(200),
    participants JSON,                        -- 参与人 ["张三", "李四"]
    
    -- 时间信息
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    is_all_day BOOLEAN DEFAULT 0,
    recurrence VARCHAR(50),                   -- 重复规则：daily/weekly/monthly
    
    -- 提醒
    reminder_minutes INTEGER,                 -- 提前多少分钟提醒
    
    -- 状态
    status VARCHAR(20) DEFAULT 'scheduled',   -- scheduled/completed/cancelled
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (note_id) REFERENCES notes(id)
);

-- 索引
CREATE INDEX idx_schedules_user_id ON schedules(user_id);
CREATE INDEX idx_schedules_start_time ON schedules(start_time);
CREATE INDEX idx_schedules_status ON schedules(status);
```

#### 笔记关联表 (note_relations)
```sql
CREATE TABLE note_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,
    related_note_id INTEGER NOT NULL,
    relation_type VARCHAR(50),                -- 关联类型：similar/follow_up/reference
    strength FLOAT DEFAULT 0.5,               -- 关联强度 0-1
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (note_id) REFERENCES notes(id),
    FOREIGN KEY (related_note_id) REFERENCES notes(id),
    UNIQUE(note_id, related_note_id)
);
```

### 4.2 Markdown 文件存储结构

#### 文件命名规范
```
{timestamp}_{id}.md

示例：
20260119_143022_001.md    # 原始笔记
20260119_143022_001_org.md # 整理后笔记
```

#### 原始笔记文件格式
```markdown
---
id: 1
created_at: 2026-01-19 14:30:22
user_id: 1
---

# 原始内容

今天客户 A 反馈登录功能有问题，需要排查。明天下午 3 点要和技术团队开会讨论。
```

#### 整理后笔记文件格式
```markdown
---
id: 1
created_at: 2026-01-19 14:30:22
organized_at: 2026-01-19 14:30:25
user_id: 1
category: 工作记录
subcategory: 客户问题
tags: [客户A, 登录问题, 技术会议]
priority: high
---

# 客户 A 登录问题反馈

## 问题描述
客户 A 反馈登录功能存在问题。

## 后续行动
- [ ] 排查登录功能问题
- [ ] 明天下午 3 点技术团队会议讨论

## 相关信息
- 客户：客户 A
- 优先级：高
- 状态：待处理
```

### 4.3 未来扩展到 PostgreSQL/MongoDB 的考虑

#### PostgreSQL 迁移
- JSON 字段原生支持
- 全文检索能力（ts_vector）
- 更好的并发性能
- 数据模型基本不变，只需调整数据类型

#### MongoDB 迁移
- 文档型数据库，适合半结构化数据
- 灵活的 Schema
- 示例文档结构：

```json
{
  "_id": "ObjectId",
  "user_id": 1,
  "title": "客户 A 登录问题",
  "raw_content": "...",
  "organized_content": "...",
  "ai_analysis": {
    "category": "工作记录",
    "subcategory": "客户问题",
    "tags": ["客户A", "登录问题"],
    "summary": "...",
    "entities": {
      "persons": ["客户A"],
      "dates": ["2026-01-20 15:00"],
      "topics": ["登录", "技术会议"]
    }
  },
  "metadata": {
    "is_todo": false,
    "is_schedule": true,
    "priority": "high",
    "status": "active"
  },
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

---

## 5. 核心模块设计

### 5.1 AI 服务模块

#### 抽象接口设计
```python
# app/ai/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class AIServiceBase(ABC):
    """AI 服务抽象基类"""
    
    @abstractmethod
    async def analyze_note(self, content: str, context: Optional[Dict] = None) -> Dict:
        """
        分析笔记内容
        
        Args:
            content: 笔记原始内容
            context: 额外上下文信息（如用户偏好、历史分类等）
        
        Returns:
            {
                'category': str,
                'subcategory': str,
                'tags': List[str],
                'title': str,
                'summary': str,
                'is_todo': bool,
                'is_schedule': bool,
                'priority': str,
                'entities': {
                    'persons': List[str],
                    'dates': List[str],
                    'locations': List[str]
                },
                'suggested_actions': List[Dict]
            }
        """
        pass
    
    @abstractmethod
    async def semantic_search(self, query: str, context: Optional[Dict] = None) -> Dict:
        """
        语义搜索
        
        Args:
            query: 用户查询语句
            context: 搜索上下文
        
        Returns:
            {
                'intent': str,  # 查询意图
                'filters': Dict,  # 筛选条件
                'keywords': List[str],
                'time_range': Optional[Dict]
            }
        """
        pass
    
    @abstractmethod
    async def extract_tasks(self, content: str) -> List[Dict]:
        """提取待办任务"""
        pass
    
    @abstractmethod
    async def extract_schedule(self, content: str) -> Optional[Dict]:
        """提取日程信息"""
        pass
    
    @abstractmethod
    async def suggest_relations(self, note_id: int, content: str) -> List[int]:
        """建议相关笔记"""
        pass
```

#### Claude 实现
```python
# app/ai/claude_service.py
import anthropic
from typing import Dict, List, Optional
import json
from .base import AIServiceBase

class ClaudeService(AIServiceBase):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
    
    async def analyze_note(self, content: str, context: Optional[Dict] = None) -> Dict:
        """实现笔记分析"""
        # 使用 Claude API 分析笔记
        # 详细实现见下文 Prompt 设计
        pass
    
    async def semantic_search(self, query: str, context: Optional[Dict] = None) -> Dict:
        """实现语义搜索"""
        pass
    
    # ... 其他方法实现
```

#### 工厂模式
```python
# app/ai/factory.py
from typing import Dict
from .base import AIServiceBase
from .claude_service import ClaudeService

class AIServiceFactory:
    """AI 服务工厂"""
    
    _services: Dict[str, type] = {
        'claude': ClaudeService,
        # 未来扩展
        # 'openai': OpenAIService,
        # 'local': LocalLLMService,
    }
    
    @classmethod
    def create(cls, service_type: str, **kwargs) -> AIServiceBase:
        """
        创建 AI 服务实例
        
        Args:
            service_type: 服务类型 ('claude', 'openai', 'local')
            **kwargs: 服务配置参数（如 api_key）
        
        Returns:
            AI 服务实例
        """
        service_class = cls._services.get(service_type)
        if not service_class:
            raise ValueError(f"不支持的 AI 服务类型: {service_type}")
        
        return service_class(**kwargs)
    
    @classmethod
    def register(cls, name: str, service_class: type):
        """注册新的 AI 服务"""
        cls._services[name] = service_class
```

### 5.2 存储模块

#### Markdown 文件管理
```python
# app/storage/markdown_storage.py
from pathlib import Path
from typing import Optional
import frontmatter

class MarkdownStorage:
    """Markdown 文件存储管理"""
    
    def __init__(self, base_path: str = "data/notes"):
        self.raw_path = Path(base_path) / "raw"
        self.organized_path = Path(base_path) / "organized"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保目录存在"""
        self.raw_path.mkdir(parents=True, exist_ok=True)
        self.organized_path.mkdir(parents=True, exist_ok=True)
    
    def save_raw(self, note_id: int, content: str, metadata: dict) -> str:
        """保存原始笔记"""
        filename = self._generate_filename(note_id)
        filepath = self.raw_path / filename
        
        # 使用 frontmatter 库处理元数据
        post = frontmatter.Post(content, **metadata)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))
        
        return str(filepath)
    
    def save_organized(self, note_id: int, content: str, metadata: dict) -> str:
        """保存整理后笔记"""
        filename = self._generate_filename(note_id, suffix="_org")
        filepath = self.organized_path / filename
        
        post = frontmatter.Post(content, **metadata)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))
        
        return str(filepath)
    
    def read(self, filepath: str) -> tuple[str, dict]:
        """读取笔记文件"""
        with open(filepath, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
        return post.content, post.metadata
    
    def _generate_filename(self, note_id: int, suffix: str = "") -> str:
        """生成文件名"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{note_id:06d}{suffix}.md"
```

#### 搜索索引（Elasticsearch - 可选）
```python
# app/storage/search_index.py
from elasticsearch import Elasticsearch
from typing import List, Dict, Optional

class SearchIndex:
    """Elasticsearch 搜索索引"""
    
    def __init__(self, host: str = "localhost", port: int = 9200):
        self.es = Elasticsearch([f"http://{host}:{port}"])
        self.index_name = "notes"
        self._ensure_index()
    
    def _ensure_index(self):
        """确保索引存在"""
        if not self.es.indices.exists(index=self.index_name):
            # 创建索引，配置中文分词
            self.es.indices.create(
                index=self.index_name,
                body={
                    "settings": {
                        "analysis": {
                            "analyzer": {
                                "ik_smart_analyzer": {
                                    "type": "custom",
                                    "tokenizer": "ik_smart"
                                }
                            }
                        }
                    },
                    "mappings": {
                        "properties": {
                            "content": {"type": "text", "analyzer": "ik_smart_analyzer"},
                            "title": {"type": "text", "analyzer": "ik_smart_analyzer"},
                            "category": {"type": "keyword"},
                            "tags": {"type": "keyword"},
                            "created_at": {"type": "date"}
                        }
                    }
                }
            )
    
    def index_note(self, note_id: int, data: Dict):
        """索引笔记"""
        self.es.index(index=self.index_name, id=note_id, body=data)
    
    def search(self, query: str, filters: Optional[Dict] = None) -> List[Dict]:
        """全文搜索"""
        must = [{"multi_match": {"query": query, "fields": ["content", "title"]}}]
        
        if filters:
            for key, value in filters.items():
                must.append({"term": {key: value}})
        
        body = {
            "query": {
                "bool": {"must": must}
            }
        }
        
        result = self.es.search(index=self.index_name, body=body)
        return [hit["_source"] for hit in result["hits"]["hits"]]
```

### 5.3 笔记服务层

```python
# app/services/note_service.py
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from ..models.note import Note
from ..storage.markdown_storage import MarkdownStorage
from ..storage.search_index import SearchIndex
from ..ai.factory import AIServiceFactory

class NoteService:
    """笔记服务"""
    
    def __init__(self, db: Session, ai_service_type: str = 'claude'):
        self.db = db
        self.markdown_storage = MarkdownStorage()
        self.search_index = SearchIndex()  # 可选
        self.ai_service = AIServiceFactory.create(ai_service_type, api_key="...")
    
    async def create_note(self, user_id: int, content: str) -> Dict:
        """创建笔记"""
        # 1. 保存原始内容到数据库
        note = Note(user_id=user_id, status='processing')
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        
        # 2. 保存原始 Markdown 文件
        raw_metadata = {
            'id': note.id,
            'user_id': user_id,
            'created_at': note.created_at.isoformat()
        }
        raw_path = self.markdown_storage.save_raw(note.id, content, raw_metadata)
        
        # 3. AI 分析内容
        analysis = await self.ai_service.analyze_note(content)
        
        # 4. 生成整理后的内容
        organized_content = self._generate_organized_content(content, analysis)
        organized_metadata = {**raw_metadata, **analysis, 'organized_at': 'now'}
        organized_path = self.markdown_storage.save_organized(
            note.id, organized_content, organized_metadata
        )
        
        # 5. 更新数据库
        note.raw_file_path = raw_path
        note.organized_file_path = organized_path
        note.title = analysis['title']
        note.category = analysis['category']
        note.subcategory = analysis['subcategory']
        note.tags = analysis['tags']
        note.summary = analysis['summary']
        note.is_todo = analysis['is_todo']
        note.is_schedule = analysis['is_schedule']
        note.priority = analysis['priority']
        note.status = 'active'
        self.db.commit()
        
        # 6. 索引到 ES（如果启用）
        if self.search_index:
            self.search_index.index_note(note.id, {
                'content': organized_content,
                'title': note.title,
                'category': note.category,
                'tags': note.tags,
                'created_at': note.created_at
            })
        
        return self._note_to_dict(note)
    
    def _generate_organized_content(self, raw_content: str, analysis: Dict) -> str:
        """生成整理后的 Markdown 内容"""
        # 根据 AI 分析结果，重新组织内容
        # 添加标题、分段、待办列表等
        pass
    
    # 其他方法...
```

---

## 6. API 接口设计

### 6.1 RESTful API 规范

**Base URL**: `http://localhost:8000/api/v1`

#### 6.1.1 笔记相关 API

**创建笔记**
```
POST /notes
Content-Type: application/json

Request:
{
  "content": "笔记内容（Markdown 格式）"
}

Response:
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "title": "AI 生成的标题",
    "category": "工作记录",
    "subcategory": "客户问题",
    "tags": ["客户A", "登录"],
    "summary": "摘要",
    "is_todo": false,
    "is_schedule": true,
    "priority": "high",
    "created_at": "2026-01-19T14:30:22Z",
    "raw_file_path": "data/notes/raw/...",
    "organized_file_path": "data/notes/organized/..."
  }
}
```

**获取笔记列表**
```
GET /notes?page=1&page_size=20&category=工作记录&status=active&sort_by=created_at&order=desc

Response:
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "items": [...]
  }
}
```

**获取笔记详情**
```
GET /notes/{note_id}

Response:
{
  "code": 200,
  "data": {
    "id": 1,
    "title": "...",
    "raw_content": "原始内容",
    "organized_content": "整理后内容",
    "ai_analysis": {...},
    "related_notes": [...],
    "related_todos": [...],
    "related_schedules": [...]
  }
}
```

**更新笔记**
```
PUT /notes/{note_id}
Content-Type: application/json

Request:
{
  "content": "更新后的内容",
  "reanalyze": true  // 是否重新 AI 分析
}
```

**删除笔记**
```
DELETE /notes/{note_id}
```

#### 6.1.2 搜索相关 API

**对话式搜索**
```
POST /search
Content-Type: application/json

Request:
{
  "query": "有哪些需求问题还没确定？",
  "context": {
    "previous_query": "...",  // 可选，多轮对话
    "filters": {...}
  }
}

Response:
{
  "code": 200,
  "data": {
    "intent": "查询待确认需求",
    "results": [
      {
        "note_id": 1,
        "title": "...",
        "summary": "...",
        "relevance_score": 0.95,
        "highlight": "...高亮的相关内容..."
      }
    ],
    "suggestions": [
      {
        "action": "create_todo",
        "description": "是否创建待办任务？",
        "data": {...}
      }
    ]
  }
}
```

#### 6.1.3 Todo 相关 API

**创建 Todo**
```
POST /todos
Content-Type: application/json

Request:
{
  "title": "任务标题",
  "description": "描述",
  "due_date": "2026-01-25",
  "priority": "high",
  "note_id": 1  // 可选，关联笔记
}
```

**从笔记创建 Todo**
```
POST /todos/from-note
Content-Type: application/json

Request:
{
  "note_id": 1,
  "auto_extract": true  // 是否让 AI 自动提取
}

Response:
{
  "code": 200,
  "data": {
    "todos": [
      {"title": "...", "due_date": "..."},
      {"title": "...", "due_date": "..."}
    ]
  }
}
```

**获取 Todo 列表**
```
GET /todos?status=pending&priority=high&due_date_from=2026-01-19&due_date_to=2026-01-25
```

**更新 Todo 状态**
```
PATCH /todos/{todo_id}/status
Content-Type: application/json

Request:
{
  "status": "completed"
}
```

#### 6.1.4 日程相关 API

**创建 Schedule**
```
POST /schedules
Content-Type: application/json

Request:
{
  "title": "会议主题",
  "description": "...",
  "start_time": "2026-01-20T15:00:00Z",
  "end_time": "2026-01-20T16:00:00Z",
  "participants": ["张三", "李四"],
  "location": "会议室 A",
  "note_id": 1
}
```

**从笔记创建 Schedule**
```
POST /schedules/from-note
Content-Type: application/json

Request:
{
  "note_id": 1
}
```

**获取 Schedule 列表**
```
GET /schedules?start_date=2026-01-19&end_date=2026-01-25&view=week
```

#### 6.1.5 设置相关 API

**获取设置**
```
GET /settings
```

**更新设置**
```
PUT /settings
Content-Type: application/json

Request:
{
  "ai_service": "claude",
  "api_key": "sk-...",
  "theme": "dark",
  "auto_backup": true
}
```

### 6.2 WebSocket API（可选 - 用于实时更新）

```
ws://localhost:8000/ws

// AI 分析进度推送
{
  "type": "analysis_progress",
  "note_id": 1,
  "progress": 50,
  "message": "正在提取关键信息..."
}

// 分析完成通知
{
  "type": "analysis_completed",
  "note_id": 1,
  "result": {...}
}
```

---

## 7. AI Prompt 设计

### 7.1 笔记分析 Prompt

```python
# app/ai/prompts/classify.py

ANALYZE_NOTE_PROMPT = """
你是一个智能笔记助手，负责分析用户的笔记内容并提取结构化信息。

请分析以下笔记内容：

{content}

请以 JSON 格式返回以下信息：

{{
  "title": "为笔记生成一个简洁的标题（10 字以内）",
  "category": "分类，从以下选项中选择：学习笔记、工作记录、客户问题、需求记录、Bug记录、会议记录、想法灵感、个人杂记",
  "subcategory": "更具体的子分类（可选）",
  "tags": ["提取的关键词标签", "最多5个"],
  "summary": "一句话摘要（30 字以内）",
  "is_todo": true/false,  // 是否包含待办任务
  "is_schedule": true/false,  // 是否包含日程安排
  "priority": "high/medium/low",  // 优先级
  "entities": {{
    "persons": ["提及的人物"],
    "dates": ["提及的日期，格式 YYYY-MM-DD"],
    "locations": ["提及的地点"],
    "companies": ["提及的公司/客户"]
  }},
  "suggested_actions": [
    {{
      "type": "create_todo",
      "title": "建议创建的待办标题",
      "due_date": "YYYY-MM-DD",
      "priority": "high/medium/low"
    }},
    {{
      "type": "create_schedule",
      "title": "建议创建的日程标题",
      "start_time": "YYYY-MM-DD HH:MM",
      "participants": ["人员列表"]
    }}
  ]
}}

注意：
1. 只返回 JSON，不要包含其他说明文字
2. 如果某个字段无法确定，使用 null
3. tags 要具体且有意义，避免太泛泛
4. 优先级判断要合理，根据内容的紧急程度和重要性
"""
```

### 7.2 语义搜索 Prompt

```python
# app/ai/prompts/search.py

SEMANTIC_SEARCH_PROMPT = """
你是一个智能搜索助手，负责理解用户的查询意图并转换为搜索条件。

用户查询：{query}

上下文信息（可选）：
{context}

请分析用户的查询意图，并以 JSON 格式返回搜索参数：

{{
  "intent": "描述用户的查询意图",
  "filters": {{
    "category": "如果查询涉及特定分类，填写分类名",
    "tags": ["如果查询涉及特定标签"],
    "status": "active/archived",
    "is_todo": true/false/null,
    "is_schedule": true/false/null,
    "priority": "high/medium/low/null",
    "persons": ["如果查询涉及特定人物"],
    "companies": ["如果查询涉及特定公司/客户"]
  }},
  "time_range": {{
    "start": "YYYY-MM-DD",  // 如果查询涉及时间范围
    "end": "YYYY-MM-DD"
  }},
  "keywords": ["提取的搜索关键词"],
  "sort_by": "created_at/priority/updated_at",
  "order": "desc/asc"
}}

查询示例分析：

示例 1：
用户查询："有哪些需求问题还没确定？"
返回：
{{
  "intent": "查询待确认的需求问题",
  "filters": {{
    "category": "需求记录",
    "status": "active",
    "priority": null
  }},
  "keywords": ["需求", "问题", "待确认"],
  "sort_by": "created_at",
  "order": "desc"
}}

示例 2：
用户查询："上周和客户 A 相关的问题"
返回：
{{
  "intent": "查询上周客户 A 的相关问题",
  "filters": {{
    "companies": ["客户A"],
    "category": "客户问题"
  }},
  "time_range": {{
    "start": "上周一的日期",
    "end": "上周日的日期"
  }},
  "keywords": ["客户A", "问题"],
  "sort_by": "created_at",
  "order": "desc"
}}

注意：
1. 只返回 JSON，不包含其他内容
2. 时间范围要根据当前日期（{current_date}）计算
3. filters 中的值如果无法确定，使用 null
4. 关键词要提取最有意义的词，避免停用词
"""
```

---

## 8. 部署方案

### 8.1 本地开发环境

#### 环境要求
- Python 3.11+
- Node.js 18+
- （可选）Elasticsearch 8.x / Meilisearch

#### 启动步骤

**后端启动**
```bash
cd src/service

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 Claude API Key

# 初始化数据库
python scripts/init_db.py

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端启动**
```bash
cd src/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问：http://localhost:5173

### 8.2 Docker 部署（可选）

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./src/service
    ports:
      - "8000:8000"
    environment:
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - DATABASE_URL=sqlite:///data/notes.db
    volumes:
      - ./data:/app/data
    depends_on:
      - elasticsearch  # 如果使用 ES

  frontend:
    build: ./src/frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend

  elasticsearch:  # 可选
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

volumes:
  es_data:
```

启动：
```bash
docker-compose up -d
```

### 8.3 生产环境部署（未来）

- 使用 Nginx 反向代理
- PostgreSQL 替代 SQLite
- Redis 缓存
- 使用 Gunicorn + Uvicorn 运行 FastAPI
- 前端打包后静态部署

---

## 9. 性能优化策略

### 9.1 前端优化
- 虚拟列表渲染大量笔记
- Markdown 渲染防抖
- 图片懒加载
- 使用 Web Worker 处理大文件

### 9.2 后端优化
- AI 分析结果缓存（Redis）
- 数据库查询优化（索引、分页）
- 异步处理 AI 分析（后台任务队列 Celery）
- API 响应压缩

### 9.3 搜索优化
- Elasticsearch 分页和缓存
- 搜索结果预加载
- 热门查询缓存

---

## 10. 安全性考虑

### 10.1 数据安全
- API Key 加密存储
- 敏感笔记内容本地加密
- 备份文件加密

### 10.2 API 安全
- JWT 认证（未来多用户）
- API 限流
- CORS 配置
- 输入验证和清理

### 10.3 隐私保护
- 明确告知用户 AI 分析会将内容发送到 Claude API
- 提供本地模型选项（未来）
- 支持完全离线模式（不使用 AI）

---

## 11. 测试策略

### 11.1 单元测试
- 后端：pytest 测试各模块
- 前端：Vitest 测试组件和逻辑

### 11.2 集成测试
- API 端到端测试
- AI 服务 Mock 测试

### 11.3 性能测试
- 大量笔记的加载性能
- AI 分析响应时间
- 搜索性能测试

---

## 12. 开发计划

### Phase 1: 基础框架（1-2 周）
- [ ] 项目初始化，搭建前后端框架
- [ ] 数据库设计和初始化
- [ ] AI 服务抽象接口设计

### Phase 2: 核心功能（2-3 周）
- [ ] 笔记创建和保存
- [ ] AI 分析集成
- [ ] 笔记列表和详情展示
- [ ] 基础搜索功能

### Phase 3: 高级功能（2-3 周）
- [ ] 对话式搜索
- [ ] Todo 管理
- [ ] Schedule 管理
- [ ] 笔记关联

### Phase 4: 优化和完善（1-2 周）
- [ ] UI/UX 优化
- [ ] 性能优化
- [ ] 测试和 Bug 修复
- [ ] 文档完善

---

## 13. 风险和应对

### 技术风险
| 风险 | 影响 | 应对措施 |
|-----|------|---------|
| Claude API 成本过高 | 高 | 缓存策略、批量处理、提供本地模型选项 |
| AI 分析准确率不足 | 中 | 允许手动修正、用户反馈训练 |
| Elasticsearch 部署复杂 | 中 | 改用 Meilisearch 或基于 SQLite FTS |
| 大量笔记性能问题 | 中 | 分页、虚拟滚动、索引优化 |

### 用户体验风险
| 风险 | 影响 | 应对措施 |
|-----|------|---------|
| 对话式搜索理解偏差 | 中 | 提供示例查询、允许手动筛选 |
| AI 分类错误 | 低 | 显示原始内容、允许重新分类 |

---

## 附录

### A. 技术栈版本
- Python: 3.11+
- FastAPI: 0.109+
- SQLAlchemy: 2.0+
- React: 18.2+
- TypeScript: 5.0+
- Vite: 5.0+

### B. 参考文档
- FastAPI: https://fastapi.tiangolo.com/
- React: https://react.dev/
- Claude API: https://docs.anthropic.com/
- Elasticsearch: https://www.elastic.co/guide/

---

**文档结束**

审阅人：______________________  
批准人：______________________  
日期：______________________