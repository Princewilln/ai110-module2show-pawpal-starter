from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Task:
    id: str
    task_type: str  # e.g. "feeding", "walk", "medication", "appointment"
    scheduled_time: datetime
    recurring: bool = False
    frequency: Optional[str] = (
        None  # e.g. "daily", "weekly" — only relevant when recurring=True
    )
    completed: bool = False

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

    def add_pet(self, pet: Pet) -> None:
        pass

    def remove_pet(self, pet_id: str) -> None:
        pass

    def get_daily_schedule(self) -> list[Task]:
        pass


class Scheduler:
    def __init__(self) -> None:
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, task_id: str) -> None:
        pass

    def get_sorted_tasks(self) -> list[Task]:
        pass

    def detect_conflict(self, task: Task) -> bool:
        pass

    def generate_daily_plan(self) -> list[Task]:
        pass
