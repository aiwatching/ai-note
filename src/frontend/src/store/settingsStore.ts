import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  // 深度分析 Prompt 配置
  deepAnalysisPrompt: string;
  categories: string[];
  domains: string[];

  // AI 模型设置
  aiModel: string;
  temperature: number;
  maxTokens: number;

  // Actions
  setDeepAnalysisPrompt: (prompt: string) => void;
  setCategories: (categories: string[]) => void;
  setDomains: (domains: string[]) => void;
  setAiModel: (model: string) => void;
  setTemperature: (temp: number) => void;
  setMaxTokens: (tokens: number) => void;
  resetToDefaults: () => void;
}

// 默认分类列表
export const DEFAULT_CATEGORIES = [
  '学习笔记',
  '工作记录',
  '客户问题',
  '需求记录',
  'Bug记录',
  '会议记录',
  '想法灵感',
  '个人杂记',
];

// 默认领域列表
export const DEFAULT_DOMAINS = [
  '技术',
  '产品',
  '市场',
  '管理',
  '设计',
  '运营',
  '财务',
  '人事',
  '客服',
  '其他',
];

// 默认深度分析 Prompt
export const DEFAULT_DEEP_ANALYSIS_PROMPT = `你是一个专业的笔记分析助手。请对以下笔记内容进行深度分析，提取所有关键信息。

当前日期时间：{current_date}

笔记内容：
---
{content}
---

请以 JSON 格式返回完整的分析结果：

{
  "basic_info": {
    "title": "简洁标题（10字以内）",
    "category": "分类（从可选列表中选择）",
    "subcategory": "子分类（可选，更具体的分类）",
    "summary": "一句话摘要（30字以内）"
  },

  "entities": {
    "persons": [
      {
        "name": "标准姓名",
        "aliases": ["小张", "张工"],
        "role": "角色描述（如：项目经理、客户联系人）"
      }
    ],
    "companies": [
      {
        "name": "公司/客户名称",
        "aliases": ["简称", "别名"],
        "type": "类型（客户/供应商/合作伙伴/内部部门）"
      }
    ],
    "projects": [
      {
        "name": "项目名称",
        "status": "状态（进行中/已完成/规划中/暂停）"
      }
    ],
    "locations": ["地点1", "地点2"],
    "technical_terms": ["专业术语1", "技术名词2", "产品名称3"]
  },

  "topic_analysis": {
    "core_topic": "核心主题（一句话概括笔记核心内容）",
    "keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
    "domain": "所属领域（从可选列表中选择）"
  },

  "time_info": {
    "event_times": [
      {
        "description": "事件描述",
        "time": "YYYY-MM-DD HH:mm",
        "original_text": "原文中的时间表述（如：明天下午3点）"
      }
    ],
    "deadlines": [
      {
        "description": "截止事项描述",
        "time": "YYYY-MM-DD",
        "original_text": "原文表述"
      }
    ],
    "follow_up_dates": [
      {
        "description": "需要跟进的事项",
        "time": "YYYY-MM-DD",
        "original_text": "原文表述"
      }
    ]
  },

  "relation_signals": {
    "is_follow_up": false,
    "is_summary": false,
    "is_standalone": true,
    "reference_keywords": ["上次提到的关键词", "之前讨论的主题"],
    "continuation_topic": "如果是延续某主题，填写该主题关键词"
  },

  "content_features": {
    "intent": "笔记意图",
    "content_type": "内容类型",
    "has_todos": false,
    "has_questions": false,
    "has_decisions": false,
    "urgency": "紧迫度（urgent/important/normal/casual）"
  },

  "priority_assessment": {
    "priority": "优先级（high/medium/low）",
    "urgency_score": 0.5,
    "importance_score": 0.5,
    "reason": "优先级评估理由"
  },

  "action_suggestions": [
    {
      "type": "todo/schedule/reminder/link_project",
      "title": "建议操作标题",
      "due_date": "YYYY-MM-DD",
      "reason": "建议理由"
    }
  ],

  "key_points": [
    "关键要点1（一句话总结）",
    "关键要点2",
    "关键要点3"
  ]
}

可选分类列表：{categories}
可选领域列表：{domains}

重要说明：
1. 所有相对时间必须转换为绝对日期
2. 人物姓名要识别所有可能的别名和称呼
3. 跟进笔记判断：如果笔记中有"上次"、"之前"、"继续"、"接着"等词
4. 只返回 JSON，不要有任何其他文字
5. 如果无法确定某字段，使用 null 或空数组 []
6. 使用中文回复所有内容`;

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      deepAnalysisPrompt: DEFAULT_DEEP_ANALYSIS_PROMPT,
      categories: DEFAULT_CATEGORIES,
      domains: DEFAULT_DOMAINS,
      aiModel: 'claude',
      temperature: 0.7,
      maxTokens: 4096,

      setDeepAnalysisPrompt: (prompt) => {
        set({ deepAnalysisPrompt: prompt });
      },

      setCategories: (categories) => {
        set({ categories });
      },

      setDomains: (domains) => {
        set({ domains });
      },

      setAiModel: (model) => {
        set({ aiModel: model });
      },

      setTemperature: (temp) => {
        set({ temperature: temp });
      },

      setMaxTokens: (tokens) => {
        set({ maxTokens: tokens });
      },

      resetToDefaults: () => {
        set({
          deepAnalysisPrompt: DEFAULT_DEEP_ANALYSIS_PROMPT,
          categories: DEFAULT_CATEGORIES,
          domains: DEFAULT_DOMAINS,
          aiModel: 'claude',
          temperature: 0.7,
          maxTokens: 4096,
        });
      },
    }),
    {
      name: 'ai-note-settings',
    }
  )
);
