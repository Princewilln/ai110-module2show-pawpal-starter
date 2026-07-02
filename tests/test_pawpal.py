from datetime import datetime

from pawpal_system import Pet, Task, TaskType

FIXED_TIME = datetime(2026, 1, 1, 9, 0)


def test_mark_complete_changes_task_status():
    task = Task(
        id="t1",
        pet_id="p1",
        task_type=TaskType.WALK,
        scheduled_time=FIXED_TIME,
    )

    assert task.completed is False   # confirm starting state before acting
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

    assert len(pet.tasks) == 0   # confirm empty before acting
    pet.add_task(task)
    assert len(pet.tasks) == 1
