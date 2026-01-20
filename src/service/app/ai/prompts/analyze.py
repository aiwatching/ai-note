"""Note analysis prompt template."""

ANALYZE_NOTE_PROMPT = """You are an intelligent note assistant responsible for analyzing user notes and extracting structured information.

Please analyze the following note content:

{content}

Return the analysis result in JSON format:

{{
  "title": "Generate a concise title for the note (max 10 characters)",
  "category": "Category, choose from: 学习笔记, 工作记录, 客户问题, 需求记录, Bug记录, 会议记录, 想法灵感, 个人杂记",
  "subcategory": "More specific subcategory (optional)",
  "tags": ["Extracted keyword tags", "Maximum 5"],
  "summary": "One-sentence summary (max 30 characters)",
  "is_todo": true/false,
  "is_schedule": true/false,
  "priority": "high/medium/low",
  "entities": {{
    "persons": ["Mentioned people"],
    "dates": ["Mentioned dates in YYYY-MM-DD format"],
    "locations": ["Mentioned locations"],
    "companies": ["Mentioned companies/clients"]
  }},
  "suggested_actions": [
    {{
      "type": "create_todo",
      "title": "Suggested todo title",
      "due_date": "YYYY-MM-DD",
      "priority": "high/medium/low"
    }},
    {{
      "type": "create_schedule",
      "title": "Suggested schedule title",
      "start_time": "YYYY-MM-DD HH:MM",
      "participants": ["List of people"]
    }}
  ]
}}

Notes:
1. Return only JSON, no other explanatory text
2. If a field cannot be determined, use null
3. Tags should be specific and meaningful, avoid being too general
4. Priority judgment should be reasonable, based on urgency and importance
5. Respond in the same language as the input content (Chinese for Chinese input, English for English input)
"""
