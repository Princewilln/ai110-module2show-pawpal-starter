from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Task:
    id: str
    pet_id: str                  # fix #2: back-reference to owning Pet
    task_type: str               # "feeding", "walk", "medication", "appointment"
    scheduled_time: datetime
    recurring: bool = False
    frequency: Optional[str] = None  # "daily", "weekly" — only when recurring=True
    completed: bool = False

    def __post_init__(self) -> None:  # fix #5: guard invalid recurring state
        if self.recurring and not self.frequency:
            raise ValueError(f"Task '{self.id}' is recurring but has no frequency set.")

    def mark_complete(self) -> None:
        pass


@dataclass
class Pet:
    id: str
    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, task_id: str) -> None:
        pass


class Owner:
    def __init__(self, name: str) -> None:
        self.name: str = name
        self.pets: list[Pet] = []
        self.scheduler: Scheduler = Scheduler(self.pets)  # fix #1: wire Scheduler; fix #3: shared list reference

    def add_pet(self, pet: Pet) -> None:
        pass

    def remove_pet(self, pet_id: str) -> None:
        pass

    def get_daily_schedule(self, date: datetime) -> list[Task]:  # fix #6: date param
        pass


class Scheduler:
    def __init__(self, pets: list[Pet]) -> None:
        self.pets: list[Pet] = pets  # fix #3: single source of truth — derives tasks from Pet.tasks

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, task_id: str) -> None:
        pass

    def get_sorted_tasks(self) -> list[Task]:
        pass

    def detect_conflict(self, task: Task) -> Optional[Task]:  # fix #4: returns conflicting Task or None
        pass

    def generate_daily_plan(self, date: datetime) -> list[Task]:  # fix #6: date param
        pass
