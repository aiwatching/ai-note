"""
Task Storage Implementation (SQLite)
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import (
    Task, TaskExecution, TaskStatus, TaskSchedule,
    ActionType, ScheduleType, IntervalUnit
)


class TaskStore:
    """SQLite storage for tasks"""

    def __init__(self, db_path: str = "./data/tasks.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Tasks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    action_type TEXT NOT NULL,
                    action_config TEXT,
                    schedule TEXT,
                    status TEXT DEFAULT 'pending',
                    execution_count INTEGER DEFAULT 0,
                    last_executed_at TEXT,
                    next_execution_at TEXT,
                    tags TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            # Task executions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_executions (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_ms INTEGER,
                    success INTEGER DEFAULT 0,
                    result TEXT,
                    error TEXT,
                    indexed INTEGER DEFAULT 0,
                    memory_chunk_ids TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)

            # Indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status
                ON tasks(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_next_execution
                ON tasks(next_execution_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_task_id
                ON task_executions(task_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_started_at
                ON task_executions(started_at)
            """)

            conn.commit()

    # ==================== Task CRUD ====================

    def create_task(self, task: Task) -> Task:
        """Create a new task"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO tasks (
                    id, name, description, action_type, action_config,
                    schedule, status, execution_count, last_executed_at,
                    next_execution_at, tags, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id,
                task.name,
                task.description,
                task.action_type.value,
                json.dumps(task.action_config),
                task.schedule.model_dump_json(),
                task.status.value,
                task.execution_count,
                task.last_executed_at.isoformat() if task.last_executed_at else None,
                task.next_execution_at.isoformat() if task.next_execution_at else None,
                json.dumps(task.tags),
                task.created_at.isoformat(),
                task.updated_at.isoformat(),
            ))
            conn.commit()
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_task(row)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        action_type: Optional[ActionType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """List tasks with optional filters"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM tasks WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status.value)

            if action_type:
                query += " AND action_type = ?"
                params.append(action_type.value)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()
            tasks = [self._row_to_task(row) for row in rows]

            # Filter by tags if specified
            if tags:
                tasks = [t for t in tasks if any(tag in t.tags for tag in tags)]

            return tasks

    def update_task(self, task: Task) -> Task:
        """Update an existing task"""
        task.updated_at = datetime.now()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE tasks SET
                    name = ?,
                    description = ?,
                    action_type = ?,
                    action_config = ?,
                    schedule = ?,
                    status = ?,
                    execution_count = ?,
                    last_executed_at = ?,
                    next_execution_at = ?,
                    tags = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                task.name,
                task.description,
                task.action_type.value,
                json.dumps(task.action_config),
                task.schedule.model_dump_json(),
                task.status.value,
                task.execution_count,
                task.last_executed_at.isoformat() if task.last_executed_at else None,
                task.next_execution_at.isoformat() if task.next_execution_at else None,
                json.dumps(task.tags),
                task.updated_at.isoformat(),
                task.id,
            ))
            conn.commit()

        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task and its executions"""
        with sqlite3.connect(self.db_path) as conn:
            # Delete executions first
            conn.execute("DELETE FROM task_executions WHERE task_id = ?", (task_id,))
            # Delete task
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    def count_tasks(
        self,
        status: Optional[TaskStatus] = None,
        action_type: Optional[ActionType] = None,
    ) -> int:
        """Count tasks with optional filters"""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT COUNT(*) FROM tasks WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status.value)

            if action_type:
                query += " AND action_type = ?"
                params.append(action_type.value)

            result = conn.execute(query, params).fetchone()
            return result[0] if result else 0

    # ==================== Execution CRUD ====================

    def create_execution(self, execution: TaskExecution) -> TaskExecution:
        """Create a new execution record"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO task_executions (
                    id, task_id, started_at, completed_at, duration_ms,
                    success, result, error, indexed, memory_chunk_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution.id,
                execution.task_id,
                execution.started_at.isoformat(),
                execution.completed_at.isoformat() if execution.completed_at else None,
                execution.duration_ms,
                1 if execution.success else 0,
                json.dumps(execution.result),
                execution.error,
                1 if execution.indexed else 0,
                json.dumps(execution.memory_chunk_ids),
            ))
            conn.commit()
        return execution

    def update_execution(self, execution: TaskExecution) -> TaskExecution:
        """Update an execution record"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE task_executions SET
                    completed_at = ?,
                    duration_ms = ?,
                    success = ?,
                    result = ?,
                    error = ?,
                    indexed = ?,
                    memory_chunk_ids = ?
                WHERE id = ?
            """, (
                execution.completed_at.isoformat() if execution.completed_at else None,
                execution.duration_ms,
                1 if execution.success else 0,
                json.dumps(execution.result),
                execution.error,
                1 if execution.indexed else 0,
                json.dumps(execution.memory_chunk_ids),
                execution.id,
            ))
            conn.commit()
        return execution

    def get_execution(self, execution_id: str) -> Optional[TaskExecution]:
        """Get an execution by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM task_executions WHERE id = ?",
                (execution_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_execution(row)

    def list_executions(
        self,
        task_id: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[TaskExecution]:
        """List executions with optional filters"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM task_executions WHERE 1=1"
            params = []

            if task_id:
                query += " AND task_id = ?"
                params.append(task_id)

            if success is not None:
                query += " AND success = ?"
                params.append(1 if success else 0)

            query += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_execution(row) for row in rows]

    def count_executions(self, task_id: Optional[str] = None) -> int:
        """Count executions"""
        with sqlite3.connect(self.db_path) as conn:
            if task_id:
                result = conn.execute(
                    "SELECT COUNT(*) FROM task_executions WHERE task_id = ?",
                    (task_id,)
                ).fetchone()
            else:
                result = conn.execute("SELECT COUNT(*) FROM task_executions").fetchone()
            return result[0] if result else 0

    # ==================== Scheduling Queries ====================

    def get_due_tasks(self, before: datetime = None) -> List[Task]:
        """Get tasks that are due for execution"""
        if before is None:
            before = datetime.now()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute("""
                SELECT * FROM tasks
                WHERE status IN ('scheduled', 'pending')
                AND next_execution_at IS NOT NULL
                AND next_execution_at <= ?
                ORDER BY next_execution_at ASC
            """, (before.isoformat(),)).fetchall()

            return [self._row_to_task(row) for row in rows]

    def get_scheduled_tasks(self) -> List[Task]:
        """Get all scheduled tasks"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute("""
                SELECT * FROM tasks
                WHERE status = 'scheduled'
                ORDER BY next_execution_at ASC
            """).fetchall()

            return [self._row_to_task(row) for row in rows]

    # ==================== Search ====================

    def search_execution_results(
        self,
        query: str,
        task_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[TaskExecution]:
        """Search execution results by keyword"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sql = """
                SELECT * FROM task_executions
                WHERE result LIKE ?
            """
            params = [f"%{query}%"]

            if task_id:
                sql += " AND task_id = ?"
                params.append(task_id)

            sql += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_execution(row) for row in rows]

    # ==================== Helpers ====================

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert database row to Task object"""
        schedule_data = json.loads(row["schedule"]) if row["schedule"] else {}

        return Task(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            action_type=ActionType(row["action_type"]),
            action_config=json.loads(row["action_config"]) if row["action_config"] else {},
            schedule=TaskSchedule(**schedule_data),
            status=TaskStatus(row["status"]),
            execution_count=row["execution_count"] or 0,
            last_executed_at=datetime.fromisoformat(row["last_executed_at"]) if row["last_executed_at"] else None,
            next_execution_at=datetime.fromisoformat(row["next_execution_at"]) if row["next_execution_at"] else None,
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
        )

    def _row_to_execution(self, row: sqlite3.Row) -> TaskExecution:
        """Convert database row to TaskExecution object"""
        return TaskExecution(
            id=row["id"],
            task_id=row["task_id"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else datetime.now(),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            duration_ms=row["duration_ms"],
            success=bool(row["success"]),
            result=json.loads(row["result"]) if row["result"] else {},
            error=row["error"],
            indexed=bool(row["indexed"]),
            memory_chunk_ids=json.loads(row["memory_chunk_ids"]) if row["memory_chunk_ids"] else [],
        )
