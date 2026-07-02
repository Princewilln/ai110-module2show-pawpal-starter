from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class Task:
    id: str
    pet_id: str
    task_type: str               # "feeding", "walk", "medication", "appointment"
    scheduled_time: datetime
    recurring: bool = False
    frequency: Optional[str] = None  # "daily", "weekly", "monthly" — only when recurring=True
    completed: bool = False

    def __post_init__(self) -> None:
        if self.recurring and not self.frequency:
            raise ValueError(f"Task '{self.id}' is recurring but has no frequency set.")

    def mark_complete(self) -> None:
        self.completed = True


@dataclass
class Pet:
    id: str
    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        if task.pet_id != self.id:
            raise ValueError(
                f"Task '{task.id}' belongs to pet '{task.pet_id}', not '{self.id}'."
            )
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
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
        if any(p.id == pet.id for p in self.pets):
            raise ValueError(f"Pet '{pet.id}' is already registered to owner '{self.name}'.")
        self.pets.append(pet)

    def remove_pet(self, pet_id: str) -> None:
        for i, pet in enumerate(self.pets):
            if pet.id == pet_id:
                self.pets.pop(i)
                return
        raise ValueError(f"Pet '{pet_id}' not found for owner '{self.name}'.")

    def get_daily_schedule(self, date: datetime) -> list[Task]:
        return self.scheduler.generate_daily_plan(date)


class Scheduler:
    # Two tasks within this window are considered a scheduling conflict.
    _CONFLICT_WINDOW = timedelta(minutes=15)

    def __init__(self, pets: list[Pet]) -> None:
        self.pets: list[Pet] = pets  # shared reference to Owner.pets — single source of truth

    def add_task(self, task: Task) -> None:
        pet = self._find_pet(task.pet_id)
        pet.add_task(task)

    def remove_task(self, task_id: str) -> None:
        for pet in self.pets:
            for task in pet.tasks:
                if task.id == task_id:
                    pet.remove_task(task_id)
                    return
        raise ValueError(f"Task '{task_id}' not found across any registered pet.")

    def get_sorted_tasks(self) -> list[Task]:
        all_tasks = [task for pet in self.pets for task in pet.tasks]
        return sorted(all_tasks, key=lambda t: t.scheduled_time)

    def detect_conflict(self, task: Task) -> Optional[Task]:
        for existing in self.get_sorted_tasks():
            if existing.id == task.id:
                continue
            delta = abs((existing.scheduled_time - task.scheduled_time).total_seconds())
            if delta < self._CONFLICT_WINDOW.total_seconds():
                return existing
        return None

    def generate_daily_plan(self, date: datetime) -> list[Task]:
        daily_tasks = [
            task
            for pet in self.pets
            for task in pet.tasks
            if self._is_scheduled_on(task, date)
        ]
        return sorted(daily_tasks, key=lambda t: t.scheduled_time)

    # ── private helpers ────────────────────────────────────────────────────

    def _find_pet(self, pet_id: str) -> Pet:
        for pet in self.pets:
            if pet.id == pet_id:
                return pet
        raise ValueError(f"Pet '{pet_id}' not registered with this scheduler.")

    def _is_scheduled_on(self, task: Task, date: datetime) -> bool:
        if not task.recurring:
            return task.scheduled_time.date() == date.date()
        if task.frequency == "daily":
            return True
        if task.frequency == "weekly":
            return task.scheduled_time.weekday() == date.weekday()
        if task.frequency == "monthly":
            return task.scheduled_time.day == date.day
        return False
