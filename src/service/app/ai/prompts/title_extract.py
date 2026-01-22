"""Simple title extraction prompt for note analysis."""

EXTRACT_TITLE_PROMPT = '''【重要：你必须只返回 JSON，不要有任何其他文字】

请从以下笔记内容中提取核心主题，用一个简洁的标题概括。

笔记内容：
---
{content}
---

直接返回以下 JSON 格式（不要包含任何其他文字）：

{{
  "title": "简洁的标题（5-15个字，概括笔记核心内容）",
  "category": "分类（从列表中选择：{categories}）",
  "summary": "一句话摘要（20字以内）"
}}

规则：
1. title 应该是笔记的核心主题，便于后续识别相关笔记
2. 如果笔记内容是关于某个具体事项（如会议、任务、想法），标题应反映该事项
3. 如果多条笔记是关于同一主题的，它们的 title 应该相同或非常相似
4. 只返回 JSON，不要有任何解释'''
