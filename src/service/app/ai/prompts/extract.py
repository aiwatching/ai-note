"""Extraction prompt templates for todos and schedules."""

EXTRACT_TODOS_PROMPT = """You are an intelligent assistant that extracts actionable todo items from note content.

Please analyze the following note content and extract all todo/task items:

{content}

Return the extracted todos in JSON format:

{{
  "todos": [
    {{
      "title": "Task title (clear and actionable)",
      "description": "Additional details if any",
      "due_date": "YYYY-MM-DD or null if not specified",
      "priority": "high/medium/low based on urgency and importance"
    }}
  ]
}}

Guidelines:
1. Extract explicit tasks (marked with keywords like "need to", "should", "todo", "待办", "需要", "要")
2. Extract implicit tasks (action items mentioned in meeting notes, follow-ups, etc.)
3. Set priority based on:
   - "high": urgent, deadline soon, explicitly marked as important
   - "medium": regular tasks without specific urgency
   - "low": optional or "nice to have" items
4. Parse relative dates (tomorrow, next week, etc.) to actual dates based on current date
5. If no todos found, return empty array
6. Return only JSON, no other text
"""

EXTRACT_SCHEDULE_PROMPT = """You are an intelligent assistant that extracts meeting/schedule information from note content.

Please analyze the following note content and extract schedule information:

{content}

Current date: {current_date}

Return the extracted schedule in JSON format:

{{
  "schedule": {{
    "title": "Meeting/event title",
    "description": "Description or agenda",
    "start_time": "YYYY-MM-DD HH:MM",
    "end_time": "YYYY-MM-DD HH:MM or null",
    "location": "Meeting location or null",
    "participants": ["List of participants"],
    "is_all_day": false
  }}
}}

Or if no schedule found:
{{
  "schedule": null
}}

Guidelines:
1. Look for time expressions (tomorrow, next Monday, 3pm, 15:00, etc.)
2. Look for meeting indicators (meeting, call, discussion, 会议, 讨论, 开会)
3. Extract participants from people mentioned
4. Parse relative times to absolute datetime
5. If time is ambiguous, make reasonable assumptions
6. Return only JSON, no other text
"""
