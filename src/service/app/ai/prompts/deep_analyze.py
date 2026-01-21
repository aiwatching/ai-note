"""Deep note analysis prompt template with comprehensive extraction."""

DEEP_ANALYZE_NOTE_PROMPT = '''【重要：你必须只返回 JSON，不要有任何其他文字、解释或对话】

你是一个专业的笔记分析助手。请对以下笔记内容进行深度分析，提取所有关键信息。

当前日期时间：{current_date}

笔记内容：
---
{content}
---

直接返回以下 JSON 格式的分析结果（不要包含任何其他文字）：

{{
  "basic_info": {{
    "title": "简洁标题（10字以内）",
    "category": "分类（从可选列表中选择）",
    "subcategory": "子分类（可选，更具体的分类）",
    "summary": "一句话摘要（30字以内）"
  }},

  "entities": {{
    "persons": [
      {{
        "name": "标准姓名",
        "aliases": ["小张", "张工"],
        "role": "角色描述（如：项目经理、客户联系人）"
      }}
    ],
    "companies": [
      {{
        "name": "公司/客户名称",
        "aliases": ["简称", "别名"],
        "type": "类型（客户/供应商/合作伙伴/内部部门）"
      }}
    ],
    "projects": [
      {{
        "name": "项目名称",
        "status": "状态（进行中/已完成/规划中/暂停）"
      }}
    ],
    "locations": ["地点1", "地点2"],
    "technical_terms": ["专业术语1", "技术名词2", "产品名称3"]
  }},

  "topic_analysis": {{
    "core_topic": "核心主题（一句话概括笔记核心内容）",
    "keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
    "domain": "所属领域（从可选列表中选择）"
  }},

  "time_info": {{
    "event_times": [
      {{
        "description": "事件描述",
        "time": "YYYY-MM-DD HH:mm",
        "original_text": "原文中的时间表述（如：明天下午3点）"
      }}
    ],
    "deadlines": [
      {{
        "description": "截止事项描述",
        "time": "YYYY-MM-DD",
        "original_text": "原文表述"
      }}
    ],
    "follow_up_dates": [
      {{
        "description": "需要跟进的事项",
        "time": "YYYY-MM-DD",
        "original_text": "原文表述"
      }}
    ]
  }},

  "relation_signals": {{
    "is_follow_up": false,
    "is_summary": false,
    "is_standalone": true,
    "reference_keywords": ["上次提到的关键词", "之前讨论的主题"],
    "continuation_topic": "如果是延续某主题，填写该主题关键词"
  }},

  "content_features": {{
    "intent": "笔记意图（问题反馈/工作计划/学习记录/会议纪要/头脑风暴/项目进展/客户沟通/技术方案/其他）",
    "content_type": "内容类型（问题描述/解决方案/讨论记录/知识点/想法/决策/计划/总结）",
    "has_todos": false,
    "has_questions": false,
    "has_decisions": false,
    "urgency": "紧迫度（urgent/important/normal/casual）"
  }},

  "priority_assessment": {{
    "priority": "优先级（high/medium/low）",
    "urgency_score": 0.5,
    "importance_score": 0.5,
    "reason": "优先级评估理由"
  }},

  "action_suggestions": [
    {{
      "type": "todo",
      "title": "建议创建的待办事项标题",
      "due_date": "YYYY-MM-DD",
      "priority": "high/medium/low",
      "reason": "建议理由"
    }},
    {{
      "type": "schedule",
      "title": "建议创建的日程标题",
      "start_time": "YYYY-MM-DD HH:mm",
      "end_time": "YYYY-MM-DD HH:mm",
      "participants": ["参与人1", "参与人2"],
      "reason": "建议理由"
    }},
    {{
      "type": "reminder",
      "title": "提醒内容",
      "remind_at": "YYYY-MM-DD HH:mm",
      "reason": "建议理由"
    }},
    {{
      "type": "link_project",
      "project_name": "关联的项目名称",
      "reason": "建议理由"
    }}
  ],

  "key_points": [
    "关键要点1（一句话总结）",
    "关键要点2",
    "关键要点3",
    "关键要点4",
    "关键要点5"
  ]
}}

可选分类列表：{categories}
可选领域列表：{domains}

重要说明：
1. 所有相对时间必须转换为绝对日期（基于当前日期：{current_date}）
   - "明天" -> 计算具体日期
   - "下周三" -> 计算具体日期
   - "两周后" -> 计算具体日期
2. 人物姓名要识别所有可能的别名和称呼
3. 跟进笔记判断：如果笔记中有"上次"、"之前"、"继续"、"接着"等词，说明是跟进笔记
4. 只返回 JSON，不要有任何其他文字
5. 如果无法确定某字段，使用 null 或空数组 []
6. 使用中文回复所有内容'''


# Default configuration values
DEFAULT_CATEGORIES = [
    "学习笔记", "工作记录", "客户问题", "需求记录",
    "Bug记录", "会议记录", "想法灵感", "个人杂记"
]

DEFAULT_DOMAINS = [
    "技术", "产品", "市场", "管理", "设计", "运营", "财务", "人事", "客服", "其他"
]
