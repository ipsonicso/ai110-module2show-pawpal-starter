"""
PawPal+ data models — Version 2 (simplified, flat design).

Key differences from models.py (v1):
  - No Household, DailyPlan, or ScheduledItem classes
  - Scheduler is stateless (pure methods, no instance state)
  - Task carries its own scheduled_start/end datetimes directly
  - Owner has convenience methods for creating common task types
  - OwnerPreferences and TimeWindow replace the Household-level constraints
"""

from __future__ import annotations

import copy
import uuid
from datetime import UTC, date, datetime, time, timedelta
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


# ---------------------------------------------------------------------------
# Frequency enum
# ---------------------------------------------------------------------------

class Frequency(Enum):
    ONE_TIME = "one_time"
    DAILY    = "daily"
    WEEKLY   = "weekly"
    MONTHLY  = "monthly"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


PRIORITY_RANK: dict[Priority, int] = {
    Priority.HIGH: 0,
    Priority.MEDIUM: 1,
    Priority.LOW: 2,
}


def _validate_timezone_name(timezone_name: str):  # -> ZoneInfo | timezone
    # ZoneInfo('UTC') requires the tzdata package on some platforms.
    if timezone_name.upper() == "UTC":
        return UTC
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Invalid timezone: {timezone_name!r}") from exc


def _coerce_priority(priority: Priority | str) -> Priority:
    if isinstance(priority, Priority):
        return priority
    try:
        return Priority(priority.strip().lower())
    except ValueError as exc:
        raise ValueError(
            "priority must be one of: low, medium, high"
        ) from exc


def _ensure_aware_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


# ---------------------------------------------------------------------------
# TimeWindow
# ---------------------------------------------------------------------------

class TimeWindow:
    def __init__(self, start: datetime, end: datetime) -> None:
        self.start: datetime = _ensure_aware_utc(start, "start")
        self.end: datetime = _ensure_aware_utc(end, "end")
        if self.start >= self.end:
            raise ValueError("TimeWindow start must be before end")

    def __repr__(self) -> str:
        return f"TimeWindow({self.start} -> {self.end})"


# ---------------------------------------------------------------------------
# Weekly availability defaults
# ---------------------------------------------------------------------------

def _default_weekly_availability() -> dict[int, list[tuple[time, time]]]:
    """Return a fresh copy of the default availability dict (0=Monday, 6=Sunday).

    Weekdays: 6–9 AM (before work). Weekends: 8 AM–9 PM (open day).
    """
    weekday = [(time(6, 0), time(9, 0))]
    weekend = [(time(8, 0), time(21, 0))]
    return {0: list(weekday), 1: list(weekday), 2: list(weekday),
            3: list(weekday), 4: list(weekday), 5: list(weekend), 6: list(weekend)}


# ---------------------------------------------------------------------------
# OwnerPreferences
# ---------------------------------------------------------------------------

class OwnerPreferences:
    def __init__(
        self,
        max_minutes_per_day: int = 480,
        weekly_availability: Optional[dict[int, list[tuple[time, time]]]] = None,
    ) -> None:
        self.max_minutes_per_day: int = max_minutes_per_day
        # Keys 0–6 (Monday–Sunday); each value is a list of (start, end) time pairs.
        self.weekly_availability: dict[int, list[tuple[time, time]]] = (
            weekly_availability if weekly_availability is not None
            else _default_weekly_availability()
        )

    def get_windows_for_date(self, target_date: date) -> list[TimeWindow]:
        """Return TimeWindows for target_date based on the owner's weekly schedule."""
        windows_for_day = self.weekly_availability.get(target_date.weekday(), [])
        result = []
        for start_t, end_t in windows_for_day:
            base = datetime(target_date.year, target_date.month, target_date.day, tzinfo=UTC)
            result.append(TimeWindow(
                base.replace(hour=start_t.hour, minute=start_t.minute),
                base.replace(hour=end_t.hour,   minute=end_t.minute),
            ))
        return result

    def __repr__(self) -> str:
        return f"OwnerPreferences(max_minutes_per_day={self.max_minutes_per_day})"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

class Task:
    def __init__(
        self,
        title: str,
        description: str,
        duration_minutes: int,
        priority: Priority | str,
        frequency: Frequency,
        scheduled_start: Optional[datetime] = None,
        scheduled_end: Optional[datetime] = None,
    ) -> None:
        if duration_minutes <= 0:
            raise ValueError("duration_minutes must be > 0")

        self.id: str = str(uuid.uuid4())
        self.title: str = title
        self.description: str = description
        self.duration_minutes: int = duration_minutes
        self.priority: Priority = _coerce_priority(priority)
        self.frequency: Frequency = frequency
        self.scheduled_start: Optional[datetime] = (
            _ensure_aware_utc(scheduled_start, "scheduled_start")
            if scheduled_start is not None
            else None
        )
        self.scheduled_end: Optional[datetime] = (
            _ensure_aware_utc(scheduled_end, "scheduled_end")
            if scheduled_end is not None
            else None
        )
        self.is_complete: bool = False
        self.conflict_flag: bool = False
        self.rescheduled_flag: bool = False

        if self.scheduled_start and self.scheduled_end:
            if self.scheduled_start >= self.scheduled_end:
                raise ValueError("scheduled_start must be before scheduled_end")
            actual_duration = int(
                (self.scheduled_end - self.scheduled_start).total_seconds() // 60
            )
            if actual_duration != self.duration_minutes:
                raise ValueError(
                    "duration_minutes must match scheduled_start/scheduled_end"
                )

    def mark_complete(self) -> None:
        """Mark this task as done. ONE_TIME tasks will not recur."""
        self.is_complete = True

    def __repr__(self) -> str:
        return f"Task(title={self.title!r}, priority={self.priority.value!r})"


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

class Pet:
    def __init__(self, name: str, species: str) -> None:
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.species: str = species
        self.tasks: list[Task] = []

    def _add_task(self, task: Task) -> None:
        """Internal helper used by Owner to attach a task to this pet."""
        if any(existing.id == task.id for existing in self.tasks):
            return
        self.tasks.append(task)

    def _remove_task(self, task_id: str) -> None:
        """Internal helper used by Owner to remove a task from this pet."""
        self.tasks = [task for task in self.tasks if task.id != task_id]

    def get_tasks(self) -> list[Task]:
        """Return all tasks for this pet."""
        return list(self.tasks)

    def __repr__(self) -> str:
        return f"Pet(name={self.name!r}, species={self.species!r})"


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

class Owner:
    def __init__(
        self,
        name: str,
        timezone: str = "UTC",
        preferences: Optional[OwnerPreferences] = None,
    ) -> None:
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self._tzinfo: ZoneInfo = _validate_timezone_name(timezone)
        self.timezone: str = timezone
        self.preferences: OwnerPreferences = preferences or OwnerPreferences()
        self.pets: list[Pet] = []
        self._pets_by_id: dict[str, Pet] = {}

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's care list."""
        if pet.id in self._pets_by_id:
            return
        self._pets_by_id[pet.id] = pet
        self.pets.append(pet)

    def get_pets(self) -> list[Pet]:
        """Return all pets this owner cares for."""
        return list(self.pets)

    def _get_pet_or_raise(self, pet_id: str) -> Pet:
        pet = self._pets_by_id.get(pet_id)
        if pet is None:
            raise ValueError(f"Unknown pet_id for owner {self.name!r}: {pet_id}")
        return pet

    def schedule_task(
        self,
        pet_id: str,
        title: str,
        duration_minutes: int,
        priority: Priority | str,
        description: str = "",
        frequency: Frequency = Frequency.DAILY,
        scheduled_start: Optional[datetime] = None,
        scheduled_end: Optional[datetime] = None,
    ) -> Task:
        pet = self._get_pet_or_raise(pet_id)

        if (scheduled_start is None) != (scheduled_end is None):
            raise ValueError("scheduled_start and scheduled_end must be provided together")

        task = Task(
            title=title,
            description=description,
            duration_minutes=duration_minutes,
            priority=priority,
            frequency=frequency,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
        )
        pet._add_task(task)
        return task

    def see_todays_tasks(self, target_date: date) -> list[Task]:
        """Return all tasks across all pets scheduled for target_date."""
        todays_tasks: list[Task] = []
        for pet in self.pets:
            for task in pet.tasks:
                if task.scheduled_start is None:
                    continue
                local_date = task.scheduled_start.astimezone(self._tzinfo).date()
                if local_date == target_date:
                    todays_tasks.append(task)
        return todays_tasks

    # -- Convenience task-creation helpers ----------------------------------

    def schedule_walk(
        self,
        pet_id: str,
        start: datetime,
        end: datetime,
        duration_minutes: int,
        priority: Priority | str,
    ) -> Task:
        """Create and attach a walk task to the specified pet."""
        return self.schedule_task(
            pet_id=pet_id,
            title="Walk",
            duration_minutes=duration_minutes,
            priority=priority,
            description="Walk",
            frequency=Frequency.DAILY,
            scheduled_start=start,
            scheduled_end=end,
        )

    def schedule_vet_appointment(
        self,
        pet_id: str,
        start: datetime,
        duration_minutes: int,
    ) -> Task:
        """Create and attach a vet appointment task (ONE_TIME) to the specified pet."""
        return self.schedule_task(
            pet_id=pet_id,
            title="Vet Appointment",
            duration_minutes=duration_minutes,
            priority=Priority.HIGH,
            description="Vet appointment",
            frequency=Frequency.ONE_TIME,
            scheduled_start=start,
            scheduled_end=start + timedelta(minutes=duration_minutes),
        )

    def administer_medication(
        self,
        pet_id: str,
        med_name: str,
        start: datetime,
        end: datetime,
        frequency: Frequency,
    ) -> Task:
        """Create and attach a medication task to the specified pet."""
        return self.schedule_task(
            pet_id=pet_id,
            title=f"Medication: {med_name}",
            duration_minutes=int((end - start).total_seconds() // 60),
            priority=Priority.HIGH,
            description=f"Administer {med_name}",
            frequency=frequency,
            scheduled_start=start,
            scheduled_end=end,
        )

    def __repr__(self) -> str:
        return f"Owner(name={self.name!r}, pets={len(self.pets)})"


# ---------------------------------------------------------------------------
# Scheduler  (stateless — all behaviour lives in methods)
# ---------------------------------------------------------------------------

class Scheduler:
    def collect_tasks(self, owner: Owner) -> list[Task]:
        """Gather all tasks from all of the owner's pets."""
        tasks: list[Task] = []
        for pet in owner.pets:
            tasks.extend(pet.get_tasks())
        return tasks

    def _is_due_on(self, task: Task, target_date: date, owner_tz: ZoneInfo) -> bool:
        if task.is_complete and task.frequency == Frequency.ONE_TIME:
            return False

        if task.frequency == Frequency.DAILY:
            return True

        if task.scheduled_start is None:
            return task.frequency == Frequency.ONE_TIME

        local_start = task.scheduled_start.astimezone(owner_tz)
        start_date = local_start.date()
        if task.frequency == Frequency.ONE_TIME:
            return start_date == target_date
        if task.frequency == Frequency.WEEKLY:
            return local_start.weekday() == target_date.weekday()
        if task.frequency == Frequency.MONTHLY:
            return local_start.day == target_date.day
        return False

    @staticmethod
    def _within_any_window(start: datetime, end: datetime, windows: list[TimeWindow]) -> bool:
        return any(w.start <= start and end <= w.end for w in windows)

    def generate_daily_schedule(
        self,
        owner: Owner,
        target_date: date,
        available_windows: list[TimeWindow],
    ) -> list[Task]:
        """
        Full scheduling pipeline:
          collect → assign slots (with priority-based conflict resolution) → detect conflicts.

        Works on shallow copies of tasks so the originals' scheduled_start/end
        are never mutated. Daily tasks whose pinned time falls outside the day's
        availability windows are automatically re-queued for the next open slot.
        """
        tasks = [
            copy.copy(task)
            for task in self.collect_tasks(owner)
            if self._is_due_on(task, target_date, owner._tzinfo)
        ]
        tasks = self.assign_time_slots(tasks, available_windows)
        tasks = self.detect_conflicts(tasks)
        # Sort final list by scheduled start for display; unscheduled tasks go last
        return sorted(
            tasks,
            key=lambda t: t.scheduled_start or datetime(9999, 1, 1, tzinfo=UTC),
        )

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks ordered high → medium → low priority."""
        return sorted(tasks, key=lambda task: PRIORITY_RANK[task.priority])

    @staticmethod
    def _task_rank(task: Task) -> tuple[int, int]:
        """
        Combined sort key: lower = higher priority.
          primary   — priority level  (high=0, medium=1, low=2)
          secondary — pinned first    (pinned=0, flexible=1)
        Result: pinned+high=0,0 … flexible+low=2,1

        Priority outranks pinned status, so a HIGH flexible task is processed
        before a LOW pinned task and may claim its slot.
        """
        pin_rank = 0 if task.scheduled_start is not None else 1
        return (PRIORITY_RANK[task.priority], pin_rank)

    def _find_next_slot(
        self,
        duration: timedelta,
        windows: list[TimeWindow],
        committed: list[tuple[datetime, datetime]],
    ) -> tuple[datetime, datetime] | None:
        """Return the first (start, end) gap in windows not blocked by committed intervals."""
        for window in windows:
            cursor = window.start
            while cursor + duration <= window.end:
                proposed_end = cursor + duration
                bump_to: datetime | None = None
                for c_start, c_end in committed:
                    if cursor < c_end and proposed_end > c_start:
                        if bump_to is None or c_end > bump_to:
                            bump_to = c_end
                if bump_to is None:
                    return cursor, proposed_end
                cursor = bump_to
        return None

    def assign_time_slots(
        self,
        tasks: list[Task],
        available_windows: list[TimeWindow],
    ) -> list[Task]:
        """
        Assign time slots using combined (priority, pinned) rank.

        Tasks are processed best-rank first:
          high+pinned → high+flexible → medium+pinned → … → low+flexible

        Priority outranks pinned status, so a HIGH flexible task is processed
        before a LOW pinned task and may claim its slot. A displaced pinned task
        is rescheduled to the next available slot and flagged with rescheduled_flag.
        Equal-priority pinned tasks that overlap are left at their original times
        and flagged by detect_conflicts. Tasks with no room stay unscheduled.
        """
        if not available_windows:
            return tasks

        windows = sorted(available_windows, key=lambda w: w.start)
        ordered = sorted(tasks, key=self._task_rank)

        committed: list[tuple[datetime, datetime]] = []
        committed_ranks: list[tuple[int, int]] = []
        to_reschedule: list[Task] = []

        for task in ordered:
            task_rank = self._task_rank(task)
            if task.scheduled_start is not None:
                # Daily tasks whose pinned time is outside today's windows get
                # demoted to flexible so they land in the next available slot.
                out_of_window = (
                    task.frequency == Frequency.DAILY
                    and bool(windows)
                    and not self._within_any_window(
                        task.scheduled_start, task.scheduled_end, windows
                    )
                )
                overlapping_ranks = [
                    committed_ranks[i]
                    for i in range(len(committed))
                    if task.scheduled_start < committed[i][1]
                    and task.scheduled_end > committed[i][0]
                ]
                if not overlapping_ranks and not out_of_window:
                    # No conflict — commit as pinned.
                    committed.append((task.scheduled_start, task.scheduled_end))
                    committed_ranks.append(task_rank)
                elif out_of_window or any(r < task_rank for r in overlapping_ranks):
                    # Yield: daily task outside window OR a higher-priority task
                    # already owns this slot. Reschedule and leave a warning.
                    task.rescheduled_flag = True
                    task.scheduled_start = None
                    task.scheduled_end = None
                    to_reschedule.append(task)
                else:
                    # Equal-priority pinned conflict: keep original time so
                    # detect_conflicts can flag both tasks.
                    committed.append((task.scheduled_start, task.scheduled_end))
                    committed_ranks.append(task_rank)
            else:
                # Flexible — find first open slot.
                slot = self._find_next_slot(
                    timedelta(minutes=task.duration_minutes), windows, committed
                )
                if slot:
                    task.scheduled_start, task.scheduled_end = slot
                    committed.append(slot)
                    committed_ranks.append(task_rank)

        # Place rescheduled tasks in whatever slots remain.
        for task in to_reschedule:
            slot = self._find_next_slot(
                timedelta(minutes=task.duration_minutes), windows, committed
            )
            if slot:
                task.scheduled_start, task.scheduled_end = slot
                committed.append(slot)
                committed_ranks.append(self._task_rank(task))
            # else: stays unscheduled — surfaced in display as "no room"

        return tasks

    def detect_conflicts(self, tasks: list[Task]) -> list[Task]:
        """
        Identify tasks with overlapping scheduled times.
        Returns the list with conflict information attached (or raises).
        """
        scheduled_tasks = [
            task
            for task in tasks
            if task.scheduled_start is not None and task.scheduled_end is not None
        ]

        for task in scheduled_tasks:
            task.conflict_flag = False

        events: list[tuple[datetime, int, Task]] = []
        for task in scheduled_tasks:
            events.append((task.scheduled_start, 0, task))
            events.append((task.scheduled_end, 1, task))

        # At equal timestamps, process END events (1) before START events (0)
        # so adjacent tasks (A ends at T, B starts at T) don't false-conflict.
        events.sort(key=lambda item: (item[0], 1 - item[1]))

        active: set[str] = set()
        task_lookup = {task.id: task for task in scheduled_tasks}
        for _, event_type, task in events:
            if event_type == 0:
                if active:
                    task.conflict_flag = True
                    for active_id in active:
                        task_lookup[active_id].conflict_flag = True
                active.add(task.id)
            else:
                active.discard(task.id)

        return tasks

    def explain(self, tasks: list[Task]) -> str:
        """Return a human-readable summary of the scheduled tasks and reasoning."""
        lines: list[str] = []
        for task in tasks:
            if task.scheduled_start is None or task.scheduled_end is None:
                reschedule_note = " (originally pinned, no room found)" if task.rescheduled_flag else ""
                lines.append(
                    f"[unscheduled] {task.title} ({task.duration_minutes}m, {task.priority.value}){reschedule_note}"
                )
                continue

            conflict = " CONFLICT" if task.conflict_flag else ""
            rescheduled = " (rescheduled)" if task.rescheduled_flag else ""
            lines.append(
                f"{task.scheduled_start.isoformat()} - {task.scheduled_end.isoformat()} | "
                f"{task.title} ({task.duration_minutes}m, {task.priority.value}){conflict}{rescheduled}"
            )
        return "\n".join(lines)
