"""Schedule business logic service."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from ..models.schedule import Schedule
from ..schemas.schedule_schema import ScheduleCreate, ScheduleUpdate


class ScheduleService:
    """Service for schedule-related operations."""

    def __init__(self, db: Session):
        """
        Initialize schedule service.

        Args:
            db: Database session
        """
        self.db = db

    def create_schedule(self, user_id: int, data: ScheduleCreate) -> Schedule:
        """
        Create a new schedule.

        Args:
            user_id: User ID
            data: Schedule creation data

        Returns:
            Created schedule
        """
        schedule = Schedule(
            user_id=user_id,
            note_id=data.note_id,
            title=data.title,
            description=data.description,
            location=data.location,
            start_time=data.start_time,
            end_time=data.end_time,
            is_all_day=data.is_all_day,
            recurrence=data.recurrence,
            reminder_minutes=data.reminder_minutes,
        )
        if data.participants:
            schedule.participants = data.participants

        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def get_schedule(self, user_id: int, schedule_id: int) -> Optional[Schedule]:
        """
        Get a schedule by ID.

        Args:
            user_id: User ID
            schedule_id: Schedule ID

        Returns:
            Schedule if found, None otherwise
        """
        return (
            self.db.query(Schedule)
            .filter(Schedule.id == schedule_id, Schedule.user_id == user_id)
            .first()
        )

    def list_schedules(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Schedule], int]:
        """
        List schedules with filters.

        Args:
            user_id: User ID
            start_date: Filter by start date
            end_date: Filter by end date
            status: Filter by status
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (schedules list, total count)
        """
        query = self.db.query(Schedule).filter(Schedule.user_id == user_id)

        if start_date:
            query = query.filter(Schedule.start_time >= start_date)
        if end_date:
            query = query.filter(Schedule.start_time <= end_date)
        if status:
            query = query.filter(Schedule.status == status)

        total = query.count()
        schedules = (
            query.order_by(Schedule.start_time.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return schedules, total

    def get_upcoming_schedules(
        self, user_id: int, limit: int = 10
    ) -> List[Schedule]:
        """
        Get upcoming schedules.

        Args:
            user_id: User ID
            limit: Maximum records to return

        Returns:
            List of upcoming schedules
        """
        now = datetime.utcnow()
        return (
            self.db.query(Schedule)
            .filter(
                Schedule.user_id == user_id,
                Schedule.start_time >= now,
                Schedule.status == "scheduled",
            )
            .order_by(Schedule.start_time.asc())
            .limit(limit)
            .all()
        )

    def update_schedule(
        self, user_id: int, schedule_id: int, data: ScheduleUpdate
    ) -> Optional[Schedule]:
        """
        Update a schedule.

        Args:
            user_id: User ID
            schedule_id: Schedule ID
            data: Schedule update data

        Returns:
            Updated schedule if found, None otherwise
        """
        schedule = self.get_schedule(user_id, schedule_id)
        if not schedule:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "participants":
                schedule.participants = value
            else:
                setattr(schedule, field, value)

        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def update_status(
        self, user_id: int, schedule_id: int, status: str
    ) -> Optional[Schedule]:
        """
        Update schedule status.

        Args:
            user_id: User ID
            schedule_id: Schedule ID
            status: New status

        Returns:
            Updated schedule if found, None otherwise
        """
        schedule = self.get_schedule(user_id, schedule_id)
        if not schedule:
            return None

        schedule.status = status
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def delete_schedule(self, user_id: int, schedule_id: int) -> bool:
        """
        Delete a schedule.

        Args:
            user_id: User ID
            schedule_id: Schedule ID

        Returns:
            True if deleted, False if not found
        """
        schedule = self.get_schedule(user_id, schedule_id)
        if not schedule:
            return False

        self.db.delete(schedule)
        self.db.commit()
        return True

    def create_schedules_from_note(
        self, user_id: int, note_id: int, schedule_data_list: List[dict]
    ) -> List[Schedule]:
        """
        Create schedules from analyzed note data.

        Args:
            user_id: User ID
            note_id: Source note ID
            schedule_data_list: List of schedule data from AI analysis

        Returns:
            List of created schedules
        """
        schedules = []
        for data in schedule_data_list:
            schedule = Schedule(
                user_id=user_id,
                note_id=note_id,
                title=data.get("title", "Untitled Schedule"),
                description=data.get("description"),
                location=data.get("location"),
                start_time=data.get("start_time"),
                end_time=data.get("end_time"),
                is_all_day=data.get("is_all_day", False),
            )
            if data.get("participants"):
                schedule.participants = data["participants"]

            self.db.add(schedule)
            schedules.append(schedule)

        self.db.commit()
        for schedule in schedules:
            self.db.refresh(schedule)

        return schedules
