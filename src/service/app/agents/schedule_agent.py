"""Schedule Agent for managing schedules and reminders."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from .base import BaseAgent
from .event_bus import Event, EventType
from ..database import SessionLocal
from ..models.schedule import Schedule


class ScheduleAgent(BaseAgent):
    """
    Schedule Agent responsible for:
    - Monitoring upcoming schedules
    - Sending reminders
    - Detecting schedule conflicts
    - Suggesting optimal meeting times
    """

    def __init__(
        self,
        interval_seconds: int = 60,  # Check every minute
        reminder_window_minutes: int = 15,  # Send reminders 15 minutes before
    ):
        """
        Initialize the Schedule Agent.

        Args:
            interval_seconds: How often to check schedules
            reminder_window_minutes: How many minutes before to send reminders
        """
        super().__init__(
            name="schedule_agent",
            interval_seconds=interval_seconds,
        )
        self.reminder_window_minutes = reminder_window_minutes
        self._sent_reminders: set = set()  # Track sent reminders to avoid duplicates

    async def setup(self) -> None:
        """Setup the agent - subscribe to relevant events."""
        if self.event_bus:
            self.event_bus.subscribe(EventType.SCHEDULE_CREATED, self._on_schedule_created)
            self.event_bus.subscribe(EventType.SCHEDULE_UPDATED, self._on_schedule_updated)
            self.event_bus.subscribe(EventType.SCHEDULE_DELETED, self._on_schedule_deleted)

        logger.info(f"ScheduleAgent setup complete. Reminder window: {self.reminder_window_minutes} minutes")

    async def cleanup(self) -> None:
        """Cleanup - unsubscribe from events."""
        if self.event_bus:
            self.event_bus.unsubscribe(EventType.SCHEDULE_CREATED, self._on_schedule_created)
            self.event_bus.unsubscribe(EventType.SCHEDULE_UPDATED, self._on_schedule_updated)
            self.event_bus.unsubscribe(EventType.SCHEDULE_DELETED, self._on_schedule_deleted)

        self._sent_reminders.clear()
        logger.info("ScheduleAgent cleanup complete")

    async def run_cycle(self) -> None:
        """
        Main cycle - check for upcoming schedules and send reminders.
        """
        db = SessionLocal()
        try:
            # Get upcoming schedules that need reminders
            upcoming = await self._get_upcoming_schedules(db)

            for schedule in upcoming:
                await self._process_schedule(schedule)

            # Check for conflicts in today's schedules
            await self._check_conflicts(db)

            # Update metadata
            self.set_metadata("last_check", datetime.now().isoformat())
            self.set_metadata("schedules_checked", len(upcoming))

        except Exception as e:
            logger.error(f"Error in ScheduleAgent run cycle: {e}")
            raise
        finally:
            db.close()

    async def _get_upcoming_schedules(self, db: Session) -> List[Schedule]:
        """
        Get schedules that are coming up and need reminders.

        Args:
            db: Database session

        Returns:
            List of upcoming schedules
        """
        now = datetime.now()
        reminder_time = now + timedelta(minutes=self.reminder_window_minutes)

        # Get schedules starting within the reminder window
        schedules = (
            db.query(Schedule)
            .filter(
                Schedule.status == "scheduled",
                Schedule.start_time >= now,
                Schedule.start_time <= reminder_time,
            )
            .all()
        )

        return schedules

    async def _process_schedule(self, schedule: Schedule) -> None:
        """
        Process a schedule and send reminder if needed.

        Args:
            schedule: Schedule to process
        """
        # Check if we already sent a reminder for this schedule
        reminder_key = f"{schedule.id}_{schedule.start_time.date()}"
        if reminder_key in self._sent_reminders:
            return

        # Calculate time until event
        now = datetime.now()
        time_until = schedule.start_time - now
        minutes_until = int(time_until.total_seconds() / 60)

        # Check if it's time to send reminder
        if schedule.reminder_minutes and minutes_until <= schedule.reminder_minutes:
            await self._send_reminder(schedule, minutes_until)
            self._sent_reminders.add(reminder_key)

        # Also send reminder at the default window
        elif minutes_until <= self.reminder_window_minutes:
            await self._send_reminder(schedule, minutes_until)
            self._sent_reminders.add(reminder_key)

    async def _send_reminder(self, schedule: Schedule, minutes_until: int) -> None:
        """
        Send a reminder for a schedule.

        Args:
            schedule: Schedule to remind about
            minutes_until: Minutes until the event starts
        """
        logger.info(f"Sending reminder for schedule: {schedule.title} in {minutes_until} minutes")

        if self.event_bus:
            await self.event_bus.emit(
                EventType.SCHEDULE_REMINDER,
                {
                    "schedule_id": schedule.id,
                    "title": schedule.title,
                    "start_time": schedule.start_time.isoformat(),
                    "minutes_until": minutes_until,
                    "location": schedule.location,
                    "participants": schedule.participants,
                },
                source=self.name,
            )

    async def _check_conflicts(self, db: Session) -> None:
        """
        Check for schedule conflicts today.

        Args:
            db: Database session
        """
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        # Get all schedules for today
        schedules = (
            db.query(Schedule)
            .filter(
                Schedule.status == "scheduled",
                Schedule.start_time >= datetime.combine(today, datetime.min.time()),
                Schedule.start_time < datetime.combine(tomorrow, datetime.min.time()),
            )
            .order_by(Schedule.start_time)
            .all()
        )

        # Check for overlaps
        for i, schedule1 in enumerate(schedules):
            for schedule2 in schedules[i + 1:]:
                if self._schedules_overlap(schedule1, schedule2):
                    await self._report_conflict(schedule1, schedule2)

    def _schedules_overlap(self, s1: Schedule, s2: Schedule) -> bool:
        """Check if two schedules overlap."""
        # Get end times (default to 1 hour if no end time)
        s1_end = s1.end_time or (s1.start_time + timedelta(hours=1))
        s2_end = s2.end_time or (s2.start_time + timedelta(hours=1))

        # Check for overlap
        return s1.start_time < s2_end and s2.start_time < s1_end

    async def _report_conflict(self, s1: Schedule, s2: Schedule) -> None:
        """Report a schedule conflict."""
        conflict_key = f"conflict_{min(s1.id, s2.id)}_{max(s1.id, s2.id)}"

        # Avoid reporting the same conflict repeatedly
        if conflict_key in self._sent_reminders:
            return

        logger.warning(f"Schedule conflict detected: '{s1.title}' and '{s2.title}'")

        if self.event_bus:
            await self.event_bus.emit(
                EventType.SCHEDULE_CONFLICT,
                {
                    "schedule1": {
                        "id": s1.id,
                        "title": s1.title,
                        "start_time": s1.start_time.isoformat(),
                    },
                    "schedule2": {
                        "id": s2.id,
                        "title": s2.title,
                        "start_time": s2.start_time.isoformat(),
                    },
                },
                source=self.name,
            )

        self._sent_reminders.add(conflict_key)

    # Event handlers

    async def _on_schedule_created(self, event: Event) -> None:
        """Handle schedule created event."""
        logger.debug(f"Schedule created: {event.data}")
        # Could trigger immediate conflict check

    async def _on_schedule_updated(self, event: Event) -> None:
        """Handle schedule updated event."""
        logger.debug(f"Schedule updated: {event.data}")
        # Clear sent reminders for this schedule to allow new reminders
        schedule_id = event.data.get("schedule_id")
        if schedule_id:
            self._sent_reminders = {
                key for key in self._sent_reminders
                if not key.startswith(f"{schedule_id}_")
            }

    async def _on_schedule_deleted(self, event: Event) -> None:
        """Handle schedule deleted event."""
        logger.debug(f"Schedule deleted: {event.data}")
        # Clean up sent reminders for this schedule
        schedule_id = event.data.get("schedule_id")
        if schedule_id:
            self._sent_reminders = {
                key for key in self._sent_reminders
                if not key.startswith(f"{schedule_id}_")
            }

    # Public methods for external use

    async def get_upcoming_reminders(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get all upcoming schedules within the specified hours.

        Args:
            hours: Number of hours to look ahead

        Returns:
            List of upcoming schedule info
        """
        db = SessionLocal()
        try:
            now = datetime.now()
            future = now + timedelta(hours=hours)

            schedules = (
                db.query(Schedule)
                .filter(
                    Schedule.status == "scheduled",
                    Schedule.start_time >= now,
                    Schedule.start_time <= future,
                )
                .order_by(Schedule.start_time)
                .all()
            )

            return [
                {
                    "id": s.id,
                    "title": s.title,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "location": s.location,
                    "participants": s.participants,
                }
                for s in schedules
            ]
        finally:
            db.close()

    async def suggest_time_slot(
        self,
        duration_minutes: int = 60,
        preferred_start: Optional[datetime] = None,
        preferred_end: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Suggest available time slots.

        Args:
            duration_minutes: Required duration in minutes
            preferred_start: Earliest acceptable start time
            preferred_end: Latest acceptable end time

        Returns:
            List of available time slots
        """
        db = SessionLocal()
        try:
            now = datetime.now()
            start = preferred_start or now
            end = preferred_end or (now + timedelta(days=7))

            # Get existing schedules in the time range
            schedules = (
                db.query(Schedule)
                .filter(
                    Schedule.status == "scheduled",
                    Schedule.start_time >= start,
                    Schedule.start_time <= end,
                )
                .order_by(Schedule.start_time)
                .all()
            )

            # Find gaps between schedules
            available_slots = []
            current_time = start

            for schedule in schedules:
                s_end = schedule.end_time or (schedule.start_time + timedelta(hours=1))

                # Check if there's a gap before this schedule
                gap = (schedule.start_time - current_time).total_seconds() / 60
                if gap >= duration_minutes:
                    available_slots.append({
                        "start": current_time.isoformat(),
                        "end": schedule.start_time.isoformat(),
                        "duration_minutes": int(gap),
                    })

                current_time = max(current_time, s_end)

            # Check for gap after last schedule
            if current_time < end:
                gap = (end - current_time).total_seconds() / 60
                if gap >= duration_minutes:
                    available_slots.append({
                        "start": current_time.isoformat(),
                        "end": end.isoformat(),
                        "duration_minutes": int(gap),
                    })

            return available_slots[:5]  # Return top 5 slots

        finally:
            db.close()
