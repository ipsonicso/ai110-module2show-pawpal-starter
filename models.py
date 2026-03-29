"""
PawPal+ data models.

Class hierarchy (matches UML):
    Household -> Owner <-> Pet -> Task
    Scheduler -> DailyPlan -> ScheduledItem

Optional / removable sections are marked with:
    # [OPTIONAL] — safe to delete if feature is not implemented
These include: skip/skipped/skip_reason on ScheduledItem,
               reasoning on ScheduledItem, and typical_time on Task.
"""

from __future__ import annotations

import uuid
from datetime import date, time
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Frequency enum
# ---------------------------------------------------------------------------

class Frequency(Enum):
    ONE_TIME = "one_time"
    DAILY    = "daily"
    WEEKLY   = "weekly"
    MONTHLY  = "monthly"
    YEARLY   = "yearly"


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

class Owner:
    def __init__(self, name: str) -> None:
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner (and back-link the owner onto the pet)."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"Owner(name={self.name!r})"


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

class Pet:
    def __init__(
        self,
        name: str,
        species: str,
        age: Optional[int] = None,
        medical_conditions: Optional[list[str]] = None,
    ) -> None:
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.species: str = species
        self.age: Optional[int] = age
        self.medical_conditions: list[str] = medical_conditions or []
        self.owners: list[Owner] = []
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        """Attach a task template to this pet."""
        raise NotImplementedError

    def remove_task(self, task: Task) -> None:
        """Remove a task template from this pet."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"Pet(name={self.name!r}, species={self.species!r})"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

class Task:
    def __init__(
        self,
        title: str,
        description: str,
        duration_minutes: int,
        priority: str,          # "low" | "medium" | "high"
        frequency: Frequency,
        pet: Pet,
        time_constraint: Optional[str] = None,  # e.g. "after 17:00"
    ) -> None:
        self.id: str = str(uuid.uuid4())
        self.title: str = title
        self.description: str = description
        self.duration_minutes: int = duration_minutes
        self.priority: str = priority
        self.frequency: Frequency = frequency
        self.pet: Pet = pet
        self.time_constraint: Optional[str] = time_constraint
        self.is_complete: bool = False  # used to retire ONE_TIME tasks

    # [OPTIONAL] Remove if history / typical-time feature is not implemented.
    def typical_time(self) -> Optional[time]:
        """
        Scan past ScheduledItems for this task across the household's
        DailyPlan history and return the most common start_time.
        Returns None if no history exists.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"Task(title={self.title!r}, frequency={self.frequency.value})"


# ---------------------------------------------------------------------------
# ScheduledItem
# ---------------------------------------------------------------------------

class ScheduledItem:
    def __init__(
        self,
        task: Task,
        pet: Pet,
        assigned_to: Owner,
        start_time: time,
        end_time: time,
    ) -> None:
        self.task: Task = task
        self.pet: Pet = pet
        self.assigned_to: Owner = assigned_to
        self.start_time: time = start_time
        self.end_time: time = end_time
        self.conflict_flag: bool = False

        # [OPTIONAL] Remove if skip functionality is not implemented.
        self.skipped: bool = False
        self.skip_reason: Optional[str] = None

        # [OPTIONAL] Remove if reasoning / explanation feature is not implemented.
        self.reasoning: str = ""

    # [OPTIONAL] Remove if skip functionality is not implemented.
    def skip(self, reason: str) -> None:
        """Mark this occurrence as skipped without deleting the task template."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return (
            f"ScheduledItem(task={self.task.title!r}, "
            f"pet={self.pet.name!r}, "
            f"start={self.start_time})"
        )


# ---------------------------------------------------------------------------
# DailyPlan
# ---------------------------------------------------------------------------

class DailyPlan:
    def __init__(self, plan_date: date, household: "Household") -> None:
        self.date: date = plan_date
        self.household: Household = household
        self.items: list[ScheduledItem] = []

    # [OPTIONAL] Remove if reasoning / explanation feature is not implemented.
    def explain(self) -> str:
        """
        Return a human-readable summary of the schedule by aggregating
        each ScheduledItem's reasoning string.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"DailyPlan(date={self.date}, items={len(self.items)})"


# ---------------------------------------------------------------------------
# Household
# ---------------------------------------------------------------------------

class Household:
    def __init__(self, name: str) -> None:
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.members: list[Owner] = []
        self.history: list[DailyPlan] = []

    def add_member(self, owner: Owner) -> None:
        """Add an owner to this household."""
        raise NotImplementedError

    def get_all_pets(self) -> list[Pet]:
        """Return a deduplicated list of all pets across household members."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"Household(name={self.name!r}, members={len(self.members)})"


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    def __init__(self, household: Household, target_date: date) -> None:
        self.household: Household = household
        self.target_date: date = target_date

    def build_plan(self) -> DailyPlan:
        """
        Main entry point. Runs the full scheduling pipeline and returns
        a DailyPlan for target_date.
        """
        raise NotImplementedError

    def _collect_tasks(self) -> list[Task]:
        """Gather all eligible tasks from all pets in the household."""
        raise NotImplementedError

    def _sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted high → medium → low priority."""
        raise NotImplementedError

    def _apply_time_constraints(self, tasks: list[Task]) -> list[Task]:
        """Filter or reorder tasks that carry a time_constraint."""
        raise NotImplementedError

    def _assign_time_slots(self, tasks: list[Task]) -> list[ScheduledItem]:
        """Pack tasks into sequential time slots, producing ScheduledItems."""
        raise NotImplementedError

    def _assign_owners(self, items: list[ScheduledItem]) -> None:
        """Distribute tasks across household members (mutates items in place)."""
        raise NotImplementedError

    def _detect_conflicts(self, items: list[ScheduledItem]) -> None:
        """
        Flag any items where two household members are both scheduled
        for the same pet at overlapping times (mutates conflict_flag in place).
        """
        raise NotImplementedError
