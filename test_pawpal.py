"""
pytest tests for PawPal+ scheduling behaviors.

Covers:
  1. Tracking pet care tasks (walks, feeding, meds, enrichment, grooming)
  2. Constraints (time windows, owner daily budget, priority ordering)
  3. Daily plan generation + explain() output
"""

import pytest
from datetime import UTC, date, datetime, timedelta

from pawpal_system import (
    Frequency,
    Owner,
    Pet,
    Priority,
    Scheduler,
    Task,
    TimeWindow,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DAY = date(2025, 6, 16)  # Monday


def _dt(hour: int, minute: int = 0, day: date = DAY) -> datetime:
    """Return a UTC-aware datetime on DAY."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)


def _window(start_h: int, end_h: int, day: date = DAY) -> TimeWindow:
    return TimeWindow(_dt(start_h, day=day), _dt(end_h, day=day))


@pytest.fixture
def owner():
    return Owner(name="Alex")


@pytest.fixture
def dog(owner):
    pet = Pet(name="Biscuit", species="dog")
    owner.add_pet(pet)
    return pet


@pytest.fixture
def cat(owner):
    pet = Pet(name="Luna", species="cat")
    owner.add_pet(pet)
    return pet


@pytest.fixture
def scheduler():
    return Scheduler()


# ---------------------------------------------------------------------------
# 1. Task tracking — various care types
# ---------------------------------------------------------------------------

class TestTaskTracking:
    def test_schedule_walk(self, owner, dog):
        task = owner.schedule_walk(
            pet_id=dog.id,
            start=_dt(7),
            end=_dt(7, 30),
            duration_minutes=30,
            priority=Priority.HIGH,
        )
        assert task.title == "Walk"
        assert task.duration_minutes == 30
        assert task.priority == Priority.HIGH
        assert task in dog.get_tasks()

    def test_schedule_feeding(self, owner, dog):
        task = owner.schedule_task(
            pet_id=dog.id,
            title="Feeding",
            duration_minutes=10,
            priority=Priority.HIGH,
            description="Morning kibble",
            frequency=Frequency.DAILY,
        )
        assert task.title == "Feeding"
        assert task.frequency == Frequency.DAILY
        assert task in dog.get_tasks()

    def test_schedule_medication(self, owner, dog):
        task = owner.administer_medication(
            pet_id=dog.id,
            med_name="Heartgard",
            start=_dt(8),
            end=_dt(8, 5),
            frequency=Frequency.MONTHLY,
        )
        assert "Heartgard" in task.title
        assert task.priority == Priority.HIGH
        assert task.frequency == Frequency.MONTHLY

    def test_schedule_vet_appointment(self, owner, dog):
        task = owner.schedule_vet_appointment(
            pet_id=dog.id,
            start=_dt(9),
            duration_minutes=60,
        )
        assert task.title == "Vet Appointment"
        assert task.frequency == Frequency.ONE_TIME
        assert task.priority == Priority.HIGH

    def test_schedule_enrichment(self, owner, cat):
        task = owner.schedule_task(
            pet_id=cat.id,
            title="Enrichment",
            duration_minutes=20,
            priority=Priority.MEDIUM,
            description="Puzzle feeder",
            frequency=Frequency.DAILY,
        )
        assert task.title == "Enrichment"
        assert task.priority == Priority.MEDIUM

    def test_schedule_grooming(self, owner, cat):
        task = owner.schedule_task(
            pet_id=cat.id,
            title="Grooming",
            duration_minutes=15,
            priority=Priority.LOW,
            description="Brushing",
            frequency=Frequency.WEEKLY,
        )
        assert task.title == "Grooming"
        assert task.frequency == Frequency.WEEKLY

    def test_tasks_isolated_per_pet(self, owner, dog, cat):
        owner.schedule_task(pet_id=dog.id, title="Walk", duration_minutes=30,
                            priority="high", frequency=Frequency.DAILY)
        owner.schedule_task(pet_id=cat.id, title="Feeding", duration_minutes=5,
                            priority="high", frequency=Frequency.DAILY)
        assert len(dog.get_tasks()) == 1
        assert len(cat.get_tasks()) == 1

    def test_remove_task(self, owner, dog):
        task = owner.schedule_task(pet_id=dog.id, title="Walk", duration_minutes=30,
                                   priority="high", frequency=Frequency.DAILY)
        dog._remove_task(task.id)
        assert task not in dog.get_tasks()

    def test_task_duration_must_be_positive(self):
        with pytest.raises(ValueError):
            Task(title="Bad", description="", duration_minutes=0,
                 priority=Priority.LOW, frequency=Frequency.DAILY)

    def test_pinned_task_mismatched_duration_raises(self):
        """scheduled_end - scheduled_start must equal duration_minutes."""
        with pytest.raises(ValueError):
            Task(
                title="Mismatch",
                description="",
                duration_minutes=45,
                priority=Priority.LOW,
                frequency=Frequency.DAILY,
                scheduled_start=_dt(8),
                scheduled_end=_dt(9),   # 60 min ≠ 45
            )


# ---------------------------------------------------------------------------
# 2. Constraints
# ---------------------------------------------------------------------------

class TestConstraints:
    def test_flexible_tasks_fit_within_window(self, owner, dog, scheduler):
        """Flexible tasks must be auto-assigned inside the availability window."""
        for title in ["Feeding", "Walk", "Enrichment"]:
            owner.schedule_task(pet_id=dog.id, title=title, duration_minutes=20,
                                priority="medium", frequency=Frequency.DAILY)

        windows = [_window(6, 9)]   # 3-hour window = 180 min
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)

        for task in scheduled:
            assert task.scheduled_start is not None, f"{task.title} left unscheduled"
            assert task.scheduled_start >= _dt(6)
            assert task.scheduled_end <= _dt(9)

    def test_task_that_doesnt_fit_is_unscheduled(self, owner, dog, scheduler):
        """A 90-min task in a 60-min window should remain unscheduled."""
        owner.schedule_task(pet_id=dog.id, title="Long Groom", duration_minutes=90,
                            priority="low", frequency=Frequency.DAILY)
        windows = [_window(8, 9)]   # only 60 min available
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)
        assert scheduled[0].scheduled_start is None

    def test_high_priority_scheduled_before_low(self, owner, dog, scheduler):
        """High-priority flexible task should get an earlier slot than low-priority."""
        owner.schedule_task(pet_id=dog.id, title="Meds", duration_minutes=5,
                            priority="high", frequency=Frequency.DAILY)
        owner.schedule_task(pet_id=dog.id, title="Grooming", duration_minutes=5,
                            priority="low", frequency=Frequency.DAILY)

        windows = [_window(8, 10)]
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)
        by_title = {t.title: t for t in scheduled}

        assert by_title["Meds"].scheduled_start <= by_title["Grooming"].scheduled_start

    def test_priority_sort_order(self, scheduler):
        tasks = [
            Task("Low task",    "", 10, Priority.LOW,    Frequency.DAILY),
            Task("High task",   "", 10, Priority.HIGH,   Frequency.DAILY),
            Task("Medium task", "", 10, Priority.MEDIUM, Frequency.DAILY),
        ]
        sorted_tasks = scheduler.sort_by_priority(tasks)
        priorities = [t.priority for t in sorted_tasks]
        assert priorities == [Priority.HIGH, Priority.MEDIUM, Priority.LOW]

    def test_no_overlap_in_assigned_slots(self, owner, dog, scheduler):
        """Auto-assigned tasks must not overlap each other."""
        for title in ["A", "B", "C", "D"]:
            owner.schedule_task(pet_id=dog.id, title=title, duration_minutes=20,
                                priority="medium", frequency=Frequency.DAILY)

        windows = [_window(6, 9)]
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)
        assigned = [t for t in scheduled if t.scheduled_start is not None]
        assigned.sort(key=lambda t: t.scheduled_start)

        for i in range(len(assigned) - 1):
            assert assigned[i].scheduled_end <= assigned[i + 1].scheduled_start, \
                f"Overlap between {assigned[i].title} and {assigned[i+1].title}"

    def test_pinned_high_priority_displaces_pinned_low(self, owner, dog, scheduler):
        """
        A HIGH flexible task outranks a LOW pinned task. The LOW pinned task
        is rescheduled to another slot and gets rescheduled_flag = True.
        """
        # Low pinned task occupying 8:00-8:20
        owner.schedule_task(
            pet_id=dog.id, title="Low Pinned", duration_minutes=20,
            priority="low", frequency=Frequency.DAILY,
            scheduled_start=_dt(8), scheduled_end=_dt(8, 20),
        )
        # High flexible task needing any 20-min slot
        owner.schedule_task(
            pet_id=dog.id, title="High Flex", duration_minutes=20,
            priority="high", frequency=Frequency.DAILY,
        )

        windows = [_window(8, 9)]
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)
        by_title = {t.title: t for t in scheduled}

        # High task must be scheduled
        assert by_title["High Flex"].scheduled_start is not None
        # Low pinned task must have been rescheduled (with warning flag)
        assert by_title["Low Pinned"].rescheduled_flag is True
        # Both tasks must end up at non-overlapping times
        assert not any(t.conflict_flag for t in scheduled)

    def test_owner_without_windows_leaves_tasks_unscheduled(self, owner, dog, scheduler):
        """With no availability windows, flexible tasks remain unscheduled."""
        owner.schedule_task(pet_id=dog.id, title="Walk", duration_minutes=30,
                            priority="high", frequency=Frequency.DAILY)
        scheduled = scheduler.generate_daily_schedule(owner, DAY, available_windows=[])
        assert all(t.scheduled_start is None for t in scheduled)

    def test_tasks_from_multiple_pets_all_scheduled(self, owner, dog, cat, scheduler):
        owner.schedule_task(pet_id=dog.id, title="Dog Walk", duration_minutes=20,
                            priority="high", frequency=Frequency.DAILY)
        owner.schedule_task(pet_id=cat.id, title="Cat Feeding", duration_minutes=10,
                            priority="medium", frequency=Frequency.DAILY)

        windows = [_window(6, 9)]
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)
        assert len(scheduled) == 2
        assert all(t.scheduled_start is not None for t in scheduled)


# ---------------------------------------------------------------------------
# 3. Daily plan + explain()
# ---------------------------------------------------------------------------

class TestDailyPlan:
    def test_see_todays_tasks_returns_only_today(self, owner, dog):
        """see_todays_tasks should filter by date."""
        tomorrow = DAY + timedelta(days=1)
        owner.schedule_task(
            pet_id=dog.id, title="Today Task", duration_minutes=20, priority="high",
            frequency=Frequency.ONE_TIME,
            scheduled_start=_dt(8), scheduled_end=_dt(8, 20),
        )
        owner.schedule_task(
            pet_id=dog.id, title="Tomorrow Task", duration_minutes=20, priority="high",
            frequency=Frequency.ONE_TIME,
            scheduled_start=_dt(8, day=tomorrow),
            scheduled_end=_dt(8, 20, day=tomorrow),
        )
        todays = owner.see_todays_tasks(DAY)
        assert len(todays) == 1
        assert todays[0].title == "Today Task"

    def test_generate_schedule_is_sorted_by_start(self, owner, dog, scheduler):
        for h, title in [(8, "B"), (7, "A"), (9, "C")]:
            owner.schedule_task(
                pet_id=dog.id, title=title, duration_minutes=10, priority="medium",
                frequency=Frequency.DAILY,
                scheduled_start=_dt(h), scheduled_end=_dt(h, 10),
            )
        windows = [_window(6, 12)]
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)
        starts = [t.scheduled_start for t in scheduled if t.scheduled_start]
        assert starts == sorted(starts)

    def test_overlapping_pinned_tasks_flagged_as_conflict(self, owner, dog, scheduler):
        """
        Two pinned tasks at the same slot must both be flagged as conflicts
        and kept at their original times (not silently rescheduled).
        """
        owner.schedule_task(
            pet_id=dog.id, title="Task A", duration_minutes=30, priority="high",
            frequency=Frequency.ONE_TIME,
            scheduled_start=_dt(8), scheduled_end=_dt(8, 30),
        )
        owner.schedule_task(
            pet_id=dog.id, title="Task B", duration_minutes=30, priority="high",
            frequency=Frequency.ONE_TIME,
            scheduled_start=_dt(8), scheduled_end=_dt(8, 30),
        )
        windows = [_window(6, 12)]
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)

        conflicted = [t for t in scheduled if t.conflict_flag]
        assert len(conflicted) == 2

    def test_adjacent_tasks_no_false_conflict(self, owner, dog, scheduler):
        """A ends at T, B starts at T — should NOT be a conflict."""
        owner.schedule_task(
            pet_id=dog.id, title="Task A", duration_minutes=30, priority="high",
            frequency=Frequency.ONE_TIME,
            scheduled_start=_dt(8), scheduled_end=_dt(8, 30),
        )
        owner.schedule_task(
            pet_id=dog.id, title="Task B", duration_minutes=30, priority="high",
            frequency=Frequency.ONE_TIME,
            scheduled_start=_dt(8, 30), scheduled_end=_dt(9),
        )
        windows = [_window(6, 12)]
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)
        assert not any(t.conflict_flag for t in scheduled)

    def test_explain_includes_all_tasks(self, owner, dog, scheduler):
        for title in ["Walk", "Feeding", "Meds"]:
            owner.schedule_task(pet_id=dog.id, title=title, duration_minutes=10,
                                priority="high", frequency=Frequency.DAILY)
        windows = [_window(7, 10)]
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)
        explanation = scheduler.explain(scheduled)

        assert "Walk" in explanation
        assert "Feeding" in explanation
        assert "Meds" in explanation

    def test_explain_marks_unscheduled_tasks(self, owner, dog, scheduler):
        """A task that doesn't fit must appear as [unscheduled] in explain()."""
        owner.schedule_task(pet_id=dog.id, title="Big Groom", duration_minutes=120,
                            priority="low", frequency=Frequency.DAILY)
        windows = [_window(8, 9)]   # 60 min — not enough
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)
        explanation = scheduler.explain(scheduled)
        assert "[unscheduled]" in explanation

    def test_explain_marks_conflicts(self, owner, dog, scheduler):
        """explain() outputs CONFLICT for overlapping pinned tasks."""
        for title in ["Walk", "Feeding"]:
            owner.schedule_task(
                pet_id=dog.id, title=title, duration_minutes=30, priority="high",
                frequency=Frequency.ONE_TIME,
                scheduled_start=_dt(8), scheduled_end=_dt(8, 30),
            )
        windows = [_window(6, 12)]
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)
        explanation = scheduler.explain(scheduled)
        assert "CONFLICT" in explanation

    def test_completed_one_time_task_not_rescheduled(self, owner, dog, scheduler):
        """A completed ONE_TIME task must not appear in the daily plan."""
        task = owner.schedule_task(
            pet_id=dog.id, title="Vet", duration_minutes=60, priority="high",
            frequency=Frequency.ONE_TIME,
            scheduled_start=_dt(9), scheduled_end=_dt(10),
        )
        task.mark_complete()

        windows = [_window(6, 12)]
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)
        assert not any(t.title == "Vet" for t in scheduled)

    def test_weekly_task_only_on_matching_weekday(self, owner, dog, scheduler):
        """A WEEKLY task pinned to Monday should not appear on Tuesday."""
        owner.schedule_task(
            pet_id=dog.id, title="Weekly Groom", duration_minutes=20, priority="low",
            frequency=Frequency.WEEKLY,
            scheduled_start=_dt(8), scheduled_end=_dt(8, 20),
        )
        tuesday = DAY + timedelta(days=1)
        windows = [_window(6, 12, day=tuesday)]
        scheduled = scheduler.generate_daily_schedule(owner, tuesday, windows)
        assert not any(t.title == "Weekly Groom" for t in scheduled)

    def test_rescheduled_flag_on_out_of_window_daily_task(self, owner, dog, scheduler):
        """A DAILY pinned task outside today's window is rescheduled with a warning."""
        # Pinned daily task at 5am, but window only starts at 8am
        owner.schedule_task(
            pet_id=dog.id, title="Early Walk", duration_minutes=20,
            priority="medium", frequency=Frequency.DAILY,
            scheduled_start=_dt(5), scheduled_end=_dt(5, 20),
        )
        windows = [_window(8, 10)]
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)
        task = scheduled[0]

        assert task.rescheduled_flag is True
        assert task.scheduled_start >= _dt(8)  # moved into the window

    def test_explain_marks_rescheduled(self, owner, dog, scheduler):
        """explain() outputs (rescheduled) for tasks that were moved."""
        owner.schedule_task(
            pet_id=dog.id, title="Early Walk", duration_minutes=20,
            priority="medium", frequency=Frequency.DAILY,
            scheduled_start=_dt(5), scheduled_end=_dt(5, 20),
        )
        windows = [_window(8, 10)]
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)
        explanation = scheduler.explain(scheduled)
        assert "(rescheduled)" in explanation

    def test_daily_plan_full_scenario(self, owner, dog, cat, scheduler):
        """
        Full-day scenario: dog + cat, various priorities, verify every
        task is scheduled and there are no conflicts.
        """
        owner.schedule_task(pet_id=dog.id, title="Morning Walk", duration_minutes=30,
                            priority="high", frequency=Frequency.DAILY)
        owner.schedule_task(pet_id=dog.id, title="Dog Feeding", duration_minutes=10,
                            priority="high", frequency=Frequency.DAILY)
        owner.schedule_task(pet_id=dog.id, title="Enrichment", duration_minutes=15,
                            priority="medium", frequency=Frequency.DAILY)
        owner.schedule_task(pet_id=cat.id, title="Cat Feeding", duration_minutes=5,
                            priority="high", frequency=Frequency.DAILY)
        owner.schedule_task(pet_id=cat.id, title="Grooming", duration_minutes=10,
                            priority="low", frequency=Frequency.DAILY)

        windows = [_window(6, 9)]   # 180 min total; tasks sum to 70 min
        scheduled = scheduler.generate_daily_schedule(owner, DAY, windows)

        assert len(scheduled) == 5
        assert all(t.scheduled_start is not None for t in scheduled), \
            "Every task should fit in the 3-hour window"
        assert not any(t.conflict_flag for t in scheduled), \
            "No conflicts expected when there is enough room"
