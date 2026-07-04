from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional


class TaskType(str, Enum):
    FEEDING     = "feeding"
    WALK        = "walk"
    MEDICATION  = "medication"
    APPOINTMENT = "appointment"


# Lower number = higher priority; used as tiebreaker when two tasks share the same time slot.
TASK_PRIORITY: dict[TaskType, int] = {
    TaskType.MEDICATION:  1,
    TaskType.APPOINTMENT: 2,
    TaskType.FEEDING:     3,
    TaskType.WALK:        4,
}


class Frequency(str, Enum):
    DAILY   = "daily"
    WEEKLY  = "weekly"
    MONTHLY = "monthly"


@dataclass
class Task:
    id: str
    pet_id: str
    task_type: TaskType
    scheduled_time: datetime
    recurring: bool = False
    frequency: Optional[Frequency] = None
    completed: bool = False
    # Tracks which calendar dates a recurring task has been completed on.
    completed_dates: set[date] = field(default_factory=set, compare=False, repr=False)

    def __post_init__(self) -> None:
        """Raise ValueError if the task is recurring but has no frequency set."""
        if self.recurring and not self.frequency:
            raise ValueError(f"Task '{self.id}' is recurring but has no frequency set.")

    def mark_complete(self, on_date: Optional[datetime] = None) -> None:
        """Mark this task done. Recurring tasks record the specific date so they reset the next day."""
        target = (on_date or datetime.now()).date()
        self.completed_dates.add(target)
        if not self.recurring:
            self.completed = True

    def is_done_for(self, on_date: datetime) -> bool:
        """Return True if this task has been completed for the given date."""
        if self.recurring:
            return on_date.date() in self.completed_dates
        return self.completed

    def next_occurrence(self, after: datetime) -> Optional[datetime]:
        """Return the next scheduled datetime after `after`; None for non-recurring tasks."""
        if not self.recurring:
            return None
        base = self.scheduled_time
        if self.frequency == Frequency.DAILY:
            candidate = base.replace(year=after.year, month=after.month, day=after.day)
            if candidate <= after:
                candidate += timedelta(days=1)
            return candidate
        if self.frequency == Frequency.WEEKLY:
            days_ahead = (base.weekday() - after.weekday()) % 7
            candidate = (after + timedelta(days=days_ahead)).replace(
                hour=base.hour, minute=base.minute, second=0, microsecond=0
            )
            if candidate <= after:
                candidate += timedelta(weeks=1)
            return candidate
        if self.frequency == Frequency.MONTHLY:
            try:
                candidate = base.replace(year=after.year, month=after.month)
                if candidate <= after:
                    month = after.month % 12 + 1
                    year  = after.year + (1 if after.month == 12 else 0)
                    candidate = base.replace(year=year, month=month)
                return candidate
            except ValueError:
                return None
        return None

    def spawn_next(self) -> Task:
        """Create and return the next recurring instance of this task.

        Computes next_time using timedelta — the standard Python way to shift dates:
            DAILY  → scheduled_time + timedelta(days=1)
            WEEKLY → scheduled_time + timedelta(weeks=1)

        Assigns a lineage ID so the chain is traceable:
            "feed_buddy" → "feed_buddy#2" → "feed_buddy#3" → ...

        Raises ValueError if the task is not recurring.
        """
        if not self.recurring:
            raise ValueError(
                f"Task '{self.id}' is not recurring — cannot spawn a next occurrence."
            )

        if self.frequency == Frequency.DAILY:
            next_time = self.scheduled_time + timedelta(days=1)
        elif self.frequency == Frequency.WEEKLY:
            next_time = self.scheduled_time + timedelta(weeks=1)
        elif self.frequency == Frequency.MONTHLY:
            month = self.scheduled_time.month % 12 + 1
            year  = self.scheduled_time.year + (1 if self.scheduled_time.month == 12 else 0)
            try:
                next_time = self.scheduled_time.replace(year=year, month=month)
            except ValueError:
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                next_time = self.scheduled_time.replace(year=year, month=month, day=last_day)
        else:
            raise ValueError(f"Cannot spawn next: unsupported frequency '{self.frequency}'.")

        # Build lineage ID: "t1" → "t1#2", "t1#2" → "t1#3", etc.
        if "#" in self.id:
            base_id, gen = self.id.rsplit("#", 1)
            next_id = f"{base_id}#{int(gen) + 1}"
        else:
            next_id = f"{self.id}#2"

        return Task(
            id=next_id,
            pet_id=self.pet_id,
            task_type=self.task_type,
            scheduled_time=next_time,
            recurring=True,
            frequency=self.frequency,
        )


@dataclass
class Pet:
    id: str
    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a task to this pet, rejecting tasks that belong to a different pet."""
        if task.pet_id != self.id:
            raise ValueError(
                f"Task '{task.id}' belongs to pet '{task.pet_id}', not '{self.id}'."
            )
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove a task by ID, raising ValueError if it does not exist on this pet."""
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                self.tasks.pop(i)
                return
        raise ValueError(f"Task '{task_id}' not found on pet '{self.id}'.")


class Owner:
    def __init__(self, name: str) -> None:
        self.name: str = name
        self.pets: list[Pet] = []
        self.scheduler: Scheduler = Scheduler(self.pets)  # shares same list object — no sync needed

    def add_pet(self, pet: Pet) -> None:
        """Register a new pet to this owner, rejecting duplicate pet IDs."""
        if any(p.id == pet.id for p in self.pets):
            raise ValueError(f"Pet '{pet.id}' is already registered to owner '{self.name}'.")
        self.pets.append(pet)

    def remove_pet(self, pet_id: str) -> None:
        """Unregister a pet by ID, raising ValueError if not found."""
        for i, pet in enumerate(self.pets):
            if pet.id == pet_id:
                self.pets.pop(i)
                return
        raise ValueError(f"Pet '{pet_id}' not found for owner '{self.name}'.")

    def get_daily_schedule(self, date: datetime) -> list[Task]:
        """Return all tasks scheduled for the given date, sorted by time then priority."""
        return self.scheduler.generate_daily_plan(date)


@dataclass(frozen=True)
class ConflictWarning:
    """A lightweight conflict report — carries the two clashing tasks and a message string.

    Returned by add_task_safe() and detect_all_conflicts() instead of raising exceptions,
    so the program keeps running and the caller decides what to do with the information.
    frozen=True: warnings are immutable facts, not editable state.
    """
    task_a: Task
    task_b: Task

    @property
    def message(self) -> str:
        """Format a human-readable warning string. Never raises."""
        scope   = "same pet" if self.task_a.pet_id == self.task_b.pet_id else "different pets"
        gap_sec = abs(
            (self.task_a.scheduled_time - self.task_b.scheduled_time).total_seconds()
        )
        timing  = "same time" if gap_sec == 0 else f"{int(gap_sec // 60)} min apart"
        return (
            f"⚠  CONFLICT ({scope}, {timing})  "
            f"'{self.task_a.id}' {self.task_a.task_type.value} "
            f"@ {self.task_a.scheduled_time.strftime('%I:%M %p')}  ↔  "
            f"'{self.task_b.id}' {self.task_b.task_type.value} "
            f"@ {self.task_b.scheduled_time.strftime('%I:%M %p')}"
        )


class Scheduler:
    def __init__(
        self,
        pets: list[Pet],
        conflict_window: timedelta = timedelta(minutes=15),
    ) -> None:
        self.pets: list[Pet] = pets  # shared reference to Owner.pets — single source of truth
        self.conflict_window: timedelta = conflict_window

    def add_task(self, task: Task) -> None:
        """Route a task to the correct pet using the task's pet_id."""
        pet = self._find_pet(task.pet_id)
        pet.add_task(task)

    def add_task_safe(
        self, task: Task, reference_date: Optional[datetime] = None
    ) -> list[ConflictWarning]:
        """Add a task and return any ConflictWarning objects it introduces. Never raises.

        The task is always registered — this is lightweight conflict detection:
        warn the caller, but never block the operation or crash the program.
        Returns an empty list when the new task has no clashes.
        """
        self.add_task(task)
        ref     = reference_date or datetime.now()
        active  = [
            t for t in self.get_sorted_tasks()
            if not t.is_done_for(ref) and t.id != task.id
        ]
        warnings: list[ConflictWarning] = []
        for existing in active:
            delta = abs(
                (existing.scheduled_time - task.scheduled_time).total_seconds()
            )
            if delta < self.conflict_window.total_seconds():
                warnings.append(ConflictWarning(task_a=task, task_b=existing))
        return warnings

    def remove_task(self, task_id: str) -> None:
        """Search all pets for the task by ID and remove it, raising ValueError if not found."""
        for pet in self.pets:
            for task in pet.tasks:
                if task.id == task_id:
                    pet.remove_task(task_id)
                    return
        raise ValueError(f"Task '{task_id}' not found across any registered pet.")

    def mark_task_complete(
        self, task_id: str, on_date: Optional[datetime] = None
    ) -> Optional[Task]:
        """Mark a task complete and auto-spawn the next occurrence for daily/weekly recurring tasks.

        For a recurring task the sequence is:
          1. Call spawn_next() to build the next Task (timedelta shifts the scheduled_time).
          2. Call mark_complete() on the original (records completion, sets completed=True).
          3. Set recurring=False on the original so it stops appearing in future daily plans.
          4. Register the new instance via add_task().

        For non-recurring or monthly tasks, only step 2 runs.
        Returns the newly spawned Task, or None if nothing was spawned.
        """
        target = self._find_task(task_id)

        # Spawn BEFORE touching the original — spawn_next() reads self.recurring
        next_task: Optional[Task] = None
        if target.recurring and target.frequency in (Frequency.DAILY, Frequency.WEEKLY):
            next_task = target.spawn_next()

        target.mark_complete(on_date)

        if next_task is not None:
            target.recurring  = False  # retire: won't repeat in future daily plans
            target.completed  = True   # mark_complete ran while recurring=True so didn't set this
            self.add_task(next_task)

        return next_task

    def sort_by_time(self, tasks: Optional[list[Task]] = None) -> list[Task]:
        """Return tasks sorted by scheduled time using a lambda on the 'HH:MM' string key.

        Why 'HH:MM' strings sort correctly: zero-padded 24-hour strings compare
        lexicographically in the right order — '07:00' < '08:30' < '18:00' — so
        a plain string comparison is equivalent to a time comparison.

        Example key behaviour:
            sorted(tasks, key=lambda t: t.scheduled_time.strftime("%H:%M"))
        """
        source = tasks if tasks is not None else [t for pet in self.pets for t in pet.tasks]
        return sorted(source, key=lambda t: t.scheduled_time.strftime("%H:%M"))

    def filter_tasks(
        self,
        *,
        pet_name: Optional[str] = None,
        completed: Optional[bool] = None,
        reference_date: Optional[datetime] = None,
    ) -> list[Task]:
        """Filter tasks by pet name, completion status, or both (all filters are ANDed).

        Pass pet_name to select one pet's tasks by human-readable name.
        Pass completed=True/False to select done or pending tasks.
        Omit a parameter to skip that filter.
        Results are returned sorted by time via sort_by_time().
        """
        ref = reference_date or datetime.now()
        name_to_id = {p.name: p.id for p in self.pets}

        results: list[Task] = [t for pet in self.pets for t in pet.tasks]

        if pet_name is not None:
            target_id = name_to_id.get(pet_name)
            results = [t for t in results if t.pet_id == target_id]

        if completed is not None:
            results = [t for t in results if t.is_done_for(ref) == completed]

        return self.sort_by_time(results)

    def get_sorted_tasks(self) -> list[Task]:
        """Return every task across all pets sorted by time, with priority as a tiebreaker."""
        all_tasks = [task for pet in self.pets for task in pet.tasks]
        return sorted(all_tasks, key=lambda t: (t.scheduled_time, TASK_PRIORITY[t.task_type]))

    def filter_by_pet(self, pet_id: str) -> list[Task]:
        """Return all tasks for a specific pet sorted by time and priority."""
        pet = self._find_pet(pet_id)
        return sorted(pet.tasks, key=lambda t: (t.scheduled_time, TASK_PRIORITY[t.task_type]))

    def filter_by_status(
        self, completed: bool, reference_date: Optional[datetime] = None
    ) -> list[Task]:
        """Return tasks matching the given completion status for the reference date (default: now)."""
        ref = reference_date or datetime.now()
        return [t for t in self.get_sorted_tasks() if t.is_done_for(ref) == completed]

    def get_overdue_tasks(self, now: Optional[datetime] = None) -> list[Task]:
        """Return non-recurring tasks that are past due and not yet completed."""
        cutoff = now or datetime.now()
        return [
            t for t in self.get_sorted_tasks()
            if not t.recurring and not t.completed and t.scheduled_time < cutoff
        ]

    def detect_conflict(
        self, task: Task, reference_date: Optional[datetime] = None
    ) -> Optional[Task]:
        """Return the first active task within the conflict window, or None. Skips completed tasks."""
        ref = reference_date or datetime.now()
        for existing in self.get_sorted_tasks():
            if existing.id == task.id or existing.is_done_for(ref):
                continue
            delta = abs((existing.scheduled_time - task.scheduled_time).total_seconds())
            if delta < self.conflict_window.total_seconds():
                return existing
        return None

    def detect_all_conflicts(
        self, reference_date: Optional[datetime] = None
    ) -> list[ConflictWarning]:
        """Scan every pair of active tasks for time overlaps. Returns ConflictWarning objects.

        Checks BOTH same-pet and cross-pet pairs: the owner physically attends every
        task, so two tasks at the same time clash whether they belong to the same pet
        or different pets.
        Returns an empty list when the schedule is conflict-free. Never raises.
        """
        ref    = reference_date or datetime.now()
        active = [t for t in self.get_sorted_tasks() if not t.is_done_for(ref)]
        warnings: list[ConflictWarning] = []
        for i, a in enumerate(active):
            for b in active[i + 1:]:
                delta = abs((a.scheduled_time - b.scheduled_time).total_seconds())
                if delta < self.conflict_window.total_seconds():
                    warnings.append(ConflictWarning(task_a=a, task_b=b))
        return warnings

    def generate_daily_plan(self, date: datetime) -> list[Task]:
        """Collect all tasks scheduled on the given date, sorted by time then priority."""
        daily_tasks = [
            task
            for pet in self.pets
            for task in pet.tasks
            if self._is_scheduled_on(task, date)
        ]
        return sorted(daily_tasks, key=lambda t: (t.scheduled_time, TASK_PRIORITY[t.task_type]))

    # ── private helpers ────────────────────────────────────────────────────

    def _find_pet(self, pet_id: str) -> Pet:
        """Look up a pet by ID, raising ValueError if it is not registered."""
        for pet in self.pets:
            if pet.id == pet_id:
                return pet
        raise ValueError(f"Pet '{pet_id}' not registered with this scheduler.")

    def _find_task(self, task_id: str) -> Task:
        """Look up a task by ID across all pets, raising ValueError if not found."""
        for pet in self.pets:
            for task in pet.tasks:
                if task.id == task_id:
                    return task
        raise ValueError(f"Task '{task_id}' not found across any registered pet.")

    def _is_scheduled_on(self, task: Task, date: datetime) -> bool:
        """Return True if the task falls on the given date based on its recurrence rule.

        For recurring tasks, dates earlier than the task's own scheduled_time.date()
        are always excluded — a spawned task due tomorrow must not bleed into today's plan.
        """
        if not task.recurring:
            return task.scheduled_time.date() == date.date()
        # Never show a recurring task on a date before its start date.
        if date.date() < task.scheduled_time.date():
            return False
        if task.frequency == Frequency.DAILY:
            return True
        if task.frequency == Frequency.WEEKLY:
            return task.scheduled_time.weekday() == date.weekday()
        if task.frequency == Frequency.MONTHLY:
            return task.scheduled_time.day == date.day
        return False
