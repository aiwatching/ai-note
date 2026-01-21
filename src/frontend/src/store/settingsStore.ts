import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  // 默认分析 prompt
  defaultAnalysisPrompt: string;

  // Actions
  setDefaultAnalysisPrompt: (prompt: string) => void;
  resetToDefaults: () => void;
}

const DEFAULT_ANALYSIS_PROMPT = `请分析以下内容，并提取：
1. 生成一个简洁的标题
2. 生成内容摘要（100字以内）
3. 识别分类（工作笔记、学习笔记、生活记录、想法灵感、会议记录、项目文档、其他）
4. 提取关键标签（3-5个）
5. 如果内容中包含待办事项，请提取出来
6. 如果内容中包含日程安排，请提取出来`;

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      defaultAnalysisPrompt: DEFAULT_ANALYSIS_PROMPT,

      setDefaultAnalysisPrompt: (prompt) => {
        set({ defaultAnalysisPrompt: prompt });
      },

      resetToDefaults: () => {
        set({ defaultAnalysisPrompt: DEFAULT_ANALYSIS_PROMPT });
      },
    }),
    {
      name: 'ai-note-settings',
    }
  )
);

export { DEFAULT_ANALYSIS_PROMPT };
