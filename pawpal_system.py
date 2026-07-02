from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class TaskType(str, Enum):
    FEEDING     = "feeding"
    WALK        = "walk"
    MEDICATION  = "medication"
    APPOINTMENT = "appointment"


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

    def __post_init__(self) -> None:
        """Raise ValueError if the task is recurring but has no frequency set."""
        if self.recurring and not self.frequency:
            raise ValueError(f"Task '{self.id}' is recurring but has no frequency set.")

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True


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
        """Return all tasks scheduled for the given date, sorted by time."""
        return self.scheduler.generate_daily_plan(date)


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

    def remove_task(self, task_id: str) -> None:
        """Search all pets for the task by ID and remove it, raising ValueError if not found."""
        for pet in self.pets:
            for task in pet.tasks:
                if task.id == task_id:
                    pet.remove_task(task_id)
                    return
        raise ValueError(f"Task '{task_id}' not found across any registered pet.")

    def get_sorted_tasks(self) -> list[Task]:
        """Return every task across all pets sorted by scheduled time."""
        all_tasks = [task for pet in self.pets for task in pet.tasks]
        return sorted(all_tasks, key=lambda t: t.scheduled_time)

    def detect_conflict(self, task: Task) -> Optional[Task]:
        """Return the first existing task within the conflict window, or None if the slot is free."""
        for existing in self.get_sorted_tasks():
            if existing.id == task.id:
                continue
            delta = abs((existing.scheduled_time - task.scheduled_time).total_seconds())
            if delta < self.conflict_window.total_seconds():
                return existing
        return None

    def generate_daily_plan(self, date: datetime) -> list[Task]:
        """Collect and sort all tasks scheduled on the given date, including recurring ones."""
        daily_tasks = [
            task
            for pet in self.pets
            for task in pet.tasks
            if self._is_scheduled_on(task, date)
        ]
        return sorted(daily_tasks, key=lambda t: t.scheduled_time)

    # ── private helpers ────────────────────────────────────────────────────

    def _find_pet(self, pet_id: str) -> Pet:
        """Look up a pet by ID, raising ValueError if it is not registered."""
        for pet in self.pets:
            if pet.id == pet_id:
                return pet
        raise ValueError(f"Pet '{pet_id}' not registered with this scheduler.")

    def _is_scheduled_on(self, task: Task, date: datetime) -> bool:
        """Return True if the task falls on the given date based on its recurrence rule."""
        if not task.recurring:
            return task.scheduled_time.date() == date.date()
        if task.frequency == Frequency.DAILY:
            return True
        if task.frequency == Frequency.WEEKLY:
            return task.scheduled_time.weekday() == date.weekday()
        if task.frequency == Frequency.MONTHLY:
            return task.scheduled_time.day == date.day
        return False
