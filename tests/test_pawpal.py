"""
PawPal+ test suite — covers core behaviors and key edge cases.

Core behaviors verified:
  1. Sorting with priority tiebreaker
  2. Conflict detection in/out of the 15-minute window (same-pet and cross-pet)
  3. Recurring task auto-spawn on completion + ID lineage
  4. Per-date completion semantics for recurring tasks
  5. Daily plan start-date guard (spawned task stays out of today's plan)

Edge cases covered:
  - Pet with zero tasks
  - Two tasks at the exact same time
  - Tasks at the exact 15-minute boundary (no conflict)
  - Recurring task with no frequency raises ValueError
  - spawn_next() on non-recurring task raises ValueError
  - Task added to the wrong pet raises ValueError
  - Recurring tasks are excluded from overdue checks
  - ID lineage chain: "t1" → "t1#2" → "t1#3"
"""

import pytest
from datetime import datetime, timedelta

from pawpal_system import (
    ConflictWarning,
    Frequency,
    Owner,
    Pet,
    Scheduler,
    Task,
    TaskType,
)

# ── shared fixtures ────────────────────────────────────────────────────────────

TODAY = datetime(2026, 7, 3, 0, 0)          # fixed calendar anchor for all tests


def at(hour: int, minute: int = 0) -> datetime:
    """Return TODAY at the given hour:minute."""
    return TODAY.replace(hour=hour, minute=minute, second=0, microsecond=0)


def make_pet(pet_id: str = "p1", name: str = "Buddy") -> Pet:
    return Pet(id=pet_id, name=name, species="Dog", age=3)


def make_task(
    task_id: str,
    pet_id: str,
    task_type: TaskType,
    hour: int,
    minute: int = 0,
    recurring: bool = False,
    frequency: Frequency | None = None,
) -> Task:
    return Task(
        id=task_id,
        pet_id=pet_id,
        task_type=task_type,
        scheduled_time=at(hour, minute),
        recurring=recurring,
        frequency=frequency,
    )


# ── existing tests (kept intact) ──────────────────────────────────────────────

FIXED_TIME = datetime(2026, 1, 1, 9, 0)


def test_mark_complete_changes_task_status():
    task = Task(
        id="t1",
        pet_id="p1",
        task_type=TaskType.WALK,
        scheduled_time=FIXED_TIME,
    )

    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet(id="p1", name="Buddy", species="Golden Retriever", age=3)
    task = Task(
        id="t1",
        pet_id="p1",
        task_type=TaskType.FEEDING,
        scheduled_time=FIXED_TIME,
    )

    assert len(pet.tasks) == 0
    pet.add_task(task)
    assert len(pet.tasks) == 1


# ── BEHAVIOR 1: Sorting with priority tiebreaker ──────────────────────────────

class TestSorting:
    def test_tasks_sorted_chronologically(self):
        """Tasks at different times come back in ascending time order."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        scheduler.add_task(make_task("walk_pm", "p1", TaskType.WALK,     18))
        scheduler.add_task(make_task("feed_am", "p1", TaskType.FEEDING,   8))
        scheduler.add_task(make_task("med_noon","p1", TaskType.MEDICATION,12))

        result = scheduler.sort_by_time()
        times = [t.scheduled_time.hour for t in result]
        assert times == [8, 12, 18]

    def test_priority_tiebreaker_at_same_time(self):
        """When two tasks share a time slot, lower priority-number wins.
        MEDICATION (1) must appear before WALK (4)."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        scheduler.add_task(make_task("walk1", "p1", TaskType.WALK,       9))
        scheduler.add_task(make_task("med1",  "p1", TaskType.MEDICATION, 9))

        result = scheduler.get_sorted_tasks()
        assert result[0].task_type == TaskType.MEDICATION
        assert result[1].task_type == TaskType.WALK

    def test_full_priority_ranking_at_same_time(self):
        """MEDICATION < APPOINTMENT < FEEDING < WALK when all share a slot."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        for tid, ttype in [
            ("w", TaskType.WALK),
            ("f", TaskType.FEEDING),
            ("a", TaskType.APPOINTMENT),
            ("m", TaskType.MEDICATION),
        ]:
            scheduler.add_task(make_task(tid, "p1", ttype, 9))

        result = scheduler.get_sorted_tasks()
        expected_order = [
            TaskType.MEDICATION,
            TaskType.APPOINTMENT,
            TaskType.FEEDING,
            TaskType.WALK,
        ]
        assert [t.task_type for t in result] == expected_order


# ── BEHAVIOR 2: Conflict detection ────────────────────────────────────────────

class TestConflictDetection:
    def _two_pet_scheduler(self):
        p1 = make_pet("p1", "Buddy")
        p2 = make_pet("p2", "Whiskers")
        return Scheduler([p1, p2]), p1, p2

    def test_same_pet_same_time_is_conflict(self):
        scheduler, p1, _ = self._two_pet_scheduler()
        scheduler.add_task(make_task("t1", "p1", TaskType.WALK,    9))
        w = scheduler.add_task_safe(
            make_task("t2", "p1", TaskType.FEEDING, 9), reference_date=at(8)
        )
        assert len(w) == 1
        assert isinstance(w[0], ConflictWarning)

    def test_cross_pet_same_time_is_conflict(self):
        """Owner physically attends every task → cross-pet same-time is still a conflict."""
        scheduler, p1, p2 = self._two_pet_scheduler()
        scheduler.add_task(make_task("t1", "p1", TaskType.WALK,    9))
        w = scheduler.add_task_safe(
            make_task("t2", "p2", TaskType.MEDICATION, 9), reference_date=at(8)
        )
        assert len(w) >= 1

    def test_within_window_is_conflict(self):
        """8 minutes apart (< 15-min default window) must generate a warning."""
        scheduler, p1, _ = self._two_pet_scheduler()
        scheduler.add_task(make_task("t1", "p1", TaskType.WALK, 9, 0))
        w = scheduler.add_task_safe(
            make_task("t2", "p1", TaskType.FEEDING, 9, 8), reference_date=at(8)
        )
        assert len(w) >= 1

    def test_exactly_at_window_boundary_is_no_conflict(self):
        """15 minutes apart == conflict_window → NOT a conflict (condition is < window)."""
        scheduler, p1, _ = self._two_pet_scheduler()
        scheduler.add_task(make_task("t1", "p1", TaskType.WALK, 9, 0))
        w = scheduler.add_task_safe(
            make_task("t2", "p1", TaskType.FEEDING, 9, 15), reference_date=at(8)
        )
        assert len(w) == 0

    def test_outside_window_is_no_conflict(self):
        """20 minutes apart → completely safe, no warning."""
        scheduler, p1, _ = self._two_pet_scheduler()
        scheduler.add_task(make_task("t1", "p1", TaskType.WALK, 9, 0))
        w = scheduler.add_task_safe(
            make_task("t2", "p1", TaskType.FEEDING, 9, 20), reference_date=at(8)
        )
        assert len(w) == 0

    def test_detect_all_conflicts_counts_every_pair(self):
        """Three tasks in the same slot = 3 pairs → 3 ConflictWarnings."""
        p1 = make_pet("p1", "Buddy")
        scheduler = Scheduler([p1])
        for tid, ttype in [("a","p1"), ("b","p1"), ("c","p1")]:
            scheduler.add_task(
                make_task(tid, "p1", TaskType.WALK, 9)
            )
        # override task types to avoid identical tasks
        p1.tasks[1].task_type = TaskType.FEEDING
        p1.tasks[2].task_type = TaskType.MEDICATION

        warnings = scheduler.detect_all_conflicts(reference_date=at(8))
        assert len(warnings) == 3

    def test_completed_task_does_not_block_new_slot(self):
        """A task already completed must not generate a conflict for a new task in its slot."""
        p1 = make_pet("p1", "Buddy")
        scheduler = Scheduler([p1])
        t1 = make_task("t1", "p1", TaskType.WALK, 9)
        scheduler.add_task(t1)
        t1.mark_complete(at(9))   # mark done for TODAY

        w = scheduler.add_task_safe(
            make_task("t2", "p1", TaskType.FEEDING, 9),
            reference_date=at(9),
        )
        assert len(w) == 0


# ── BEHAVIOR 3: Recurring task auto-spawn ─────────────────────────────────────

class TestRecurringSpawn:
    def test_mark_complete_spawns_next_daily_task(self):
        """Completing a daily task registers a new task shifted +1 day."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        t = make_task("feed1", "p1", TaskType.FEEDING, 8, recurring=True, frequency=Frequency.DAILY)
        scheduler.add_task(t)

        spawned = scheduler.mark_task_complete("feed1", on_date=at(8))

        assert spawned is not None
        assert spawned.scheduled_time == t.scheduled_time + timedelta(days=1)

    def test_original_is_retired_after_spawn(self):
        """After completion the original must have recurring=False and completed=True."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        t = make_task("feed1", "p1", TaskType.FEEDING, 8, recurring=True, frequency=Frequency.DAILY)
        scheduler.add_task(t)
        scheduler.mark_task_complete("feed1", on_date=at(8))

        assert t.recurring is False
        assert t.completed is True

    def test_id_lineage_first_spawn(self):
        """First spawn: 'feed1' → 'feed1#2'."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        t = make_task("feed1", "p1", TaskType.FEEDING, 8, recurring=True, frequency=Frequency.DAILY)
        scheduler.add_task(t)

        spawned = scheduler.mark_task_complete("feed1", on_date=at(8))
        assert spawned.id == "feed1#2"

    def test_id_lineage_second_spawn(self):
        """Second spawn: 'feed1#2' → 'feed1#3'."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        t = make_task("feed1", "p1", TaskType.FEEDING, 8, recurring=True, frequency=Frequency.DAILY)
        scheduler.add_task(t)

        spawned1 = scheduler.mark_task_complete("feed1", on_date=at(8))
        tomorrow = TODAY + timedelta(days=1)
        spawned2 = scheduler.mark_task_complete(spawned1.id, on_date=tomorrow.replace(hour=8))

        assert spawned2.id == "feed1#3"

    def test_weekly_spawn_shifts_one_week(self):
        """Completing a weekly task shifts scheduled_time by exactly 7 days."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        t = make_task("walk_w", "p1", TaskType.WALK, 10, recurring=True, frequency=Frequency.WEEKLY)
        scheduler.add_task(t)

        spawned = scheduler.mark_task_complete("walk_w", on_date=at(10))
        assert spawned.scheduled_time == t.scheduled_time + timedelta(weeks=1)

    def test_non_recurring_mark_complete_returns_none(self):
        """Non-recurring tasks return None from mark_task_complete — no spawn."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        t = make_task("appt1", "p1", TaskType.APPOINTMENT, 14)
        scheduler.add_task(t)

        result = scheduler.mark_task_complete("appt1")
        assert result is None
        assert t.completed is True

    def test_spawn_next_on_non_recurring_raises(self):
        """spawn_next() on a non-recurring task must raise ValueError."""
        t = make_task("t1", "p1", TaskType.WALK, 9)
        with pytest.raises(ValueError):
            t.spawn_next()


# ── BEHAVIOR 4: Per-date completion semantics ─────────────────────────────────

class TestPerDateCompletion:
    def test_recurring_task_done_today_pending_tomorrow(self):
        """A recurring task marked done today shows as pending on a different date."""
        t = make_task("feed1", "p1", TaskType.FEEDING, 8, recurring=True, frequency=Frequency.DAILY)
        t.mark_complete(at(8))

        assert t.is_done_for(at(8)) is True
        assert t.is_done_for(at(8) + timedelta(days=1)) is False

    def test_non_recurring_completion_is_permanent(self):
        """A non-recurring task stays completed regardless of the date passed."""
        t = make_task("walk1", "p1", TaskType.WALK, 9)
        t.mark_complete(at(9))

        assert t.is_done_for(at(9)) is True
        assert t.is_done_for(at(9) + timedelta(days=5)) is True

    def test_filter_by_status_respects_reference_date(self):
        """filter_by_status uses the reference_date to decide if a recurring task is pending."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        t = make_task("feed1", "p1", TaskType.FEEDING, 8, recurring=True, frequency=Frequency.DAILY)
        scheduler.add_task(t)
        t.mark_complete(at(8))   # done for TODAY

        tomorrow = TODAY + timedelta(days=1)
        pending = scheduler.filter_by_status(completed=False, reference_date=tomorrow)
        assert any(task.id == "feed1" for task in pending)


# ── BEHAVIOR 5: Daily plan start-date guard ───────────────────────────────────

class TestDailyPlan:
    def test_spawned_task_excluded_from_today_plan(self):
        """A task spawned for tomorrow must not appear in today's daily plan."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        t = make_task("feed1", "p1", TaskType.FEEDING, 8, recurring=True, frequency=Frequency.DAILY)
        scheduler.add_task(t)
        spawned = scheduler.mark_task_complete("feed1", on_date=at(8))

        today_plan = scheduler.generate_daily_plan(at(8))
        assert all(task.id != spawned.id for task in today_plan)

    def test_spawned_task_appears_in_tomorrows_plan(self):
        """The same spawned task must appear in tomorrow's daily plan."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        t = make_task("feed1", "p1", TaskType.FEEDING, 8, recurring=True, frequency=Frequency.DAILY)
        scheduler.add_task(t)
        spawned = scheduler.mark_task_complete("feed1", on_date=at(8))

        tomorrow = TODAY + timedelta(days=1)
        tomorrow_plan = scheduler.generate_daily_plan(tomorrow.replace(hour=0))
        assert any(task.id == spawned.id for task in tomorrow_plan)

    def test_plan_for_date_with_no_tasks_is_empty(self):
        """A date with no scheduled tasks returns an empty list."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        scheduler.add_task(make_task("t1", "p1", TaskType.WALK, 9))

        yesterday = TODAY - timedelta(days=1)
        assert scheduler.generate_daily_plan(yesterday) == []


# ── EDGE CASES ─────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_pet_with_no_tasks_returns_empty_lists(self):
        """All scheduler queries on a pet with zero tasks must return empty lists, not crash."""
        pet = make_pet()
        scheduler = Scheduler([pet])

        assert scheduler.filter_by_pet("p1") == []
        assert scheduler.detect_all_conflicts() == []
        assert scheduler.get_overdue_tasks(now=at(23)) == []
        assert scheduler.generate_daily_plan(at(0)) == []

    def test_recurring_task_missing_frequency_raises(self):
        """A recurring=True task with no frequency must raise ValueError at construction."""
        with pytest.raises(ValueError):
            Task(
                id="bad",
                pet_id="p1",
                task_type=TaskType.WALK,
                scheduled_time=at(9),
                recurring=True,
                frequency=None,
            )

    def test_add_task_wrong_pet_raises(self):
        """Adding a task whose pet_id doesn't match the pet's id must raise ValueError."""
        pet = make_pet("p1")
        task = make_task("t1", "p2", TaskType.WALK, 9)   # pet_id = "p2", not "p1"
        with pytest.raises(ValueError):
            pet.add_task(task)

    def test_recurring_task_never_overdue(self):
        """Recurring tasks must not appear in get_overdue_tasks(), even if past their time."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        past = TODAY - timedelta(hours=2)
        t = Task(
            id="feed_daily",
            pet_id="p1",
            task_type=TaskType.FEEDING,
            scheduled_time=past,
            recurring=True,
            frequency=Frequency.DAILY,
        )
        scheduler.add_task(t)

        overdue = scheduler.get_overdue_tasks(now=at(23))
        assert not any(task.id == "feed_daily" for task in overdue)

    def test_non_recurring_past_due_is_overdue(self):
        """A non-recurring incomplete task past its scheduled time IS overdue."""
        pet = make_pet()
        scheduler = Scheduler([pet])
        past = TODAY - timedelta(hours=2)
        t = Task(id="appt1", pet_id="p1", task_type=TaskType.APPOINTMENT, scheduled_time=past)
        scheduler.add_task(t)

        overdue = scheduler.get_overdue_tasks(now=at(23))
        assert any(task.id == "appt1" for task in overdue)

    def test_owner_rejects_duplicate_pet_id(self):
        """Owner.add_pet must raise ValueError when the same pet ID is added twice."""
        owner = Owner("Alice")
        owner.add_pet(make_pet("p1", "Buddy"))
        with pytest.raises(ValueError):
            owner.add_pet(make_pet("p1", "Clone"))

    def test_filter_tasks_by_pet_name(self):
        """filter_tasks(pet_name=...) returns only that pet's tasks."""
        p1 = make_pet("p1", "Buddy")
        p2 = make_pet("p2", "Whiskers")
        scheduler = Scheduler([p1, p2])
        scheduler.add_task(make_task("b1", "p1", TaskType.WALK,    9))
        scheduler.add_task(make_task("w1", "p2", TaskType.FEEDING, 8))

        result = scheduler.filter_tasks(pet_name="Buddy")
        assert all(t.pet_id == "p1" for t in result)
        assert len(result) == 1
        assert result[0].id == "b1"
