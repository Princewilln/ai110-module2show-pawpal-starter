from datetime import datetime

from pawpal_system import Frequency, Owner, Pet, Task, TaskType


def today_at(hour: int, minute: int = 0) -> datetime:
    return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)


def print_schedule(owner: Owner, date: datetime) -> None:
    tasks     = owner.get_daily_schedule(date)
    pet_index = {p.id: p for p in owner.pets}

    W = 64
    bar  = "=" * W
    thin = "─" * W

    pet_summary = "  |  ".join(
        f"{p.name} ({p.species}, {p.age} yr{'s' if p.age != 1 else ''})"
        for p in owner.pets
    )

    print(f"\n{bar}")
    print(f"  PawPal — Smart Pet Care Manager")
    print(bar)
    print(f"  Owner : {owner.name}")
    print(f"  Pets  : {pet_summary}")
    print(f"{bar}\n")
    print(f"  TODAY'S SCHEDULE — {date.strftime('%A, %B %d, %Y')}")
    print(f"  {thin}")

    if not tasks:
        print("  No tasks scheduled for today.")
    else:
        for task in tasks:
            pet       = pet_index.get(task.pet_id)
            pet_label = f"{pet.name} ({pet.species})" if pet else task.pet_id
            status    = "✓" if task.completed else "○"
            recur_tag = f"  ↺ {task.frequency.value}" if task.recurring else ""
            time_str  = task.scheduled_time.strftime("%I:%M %p")
            type_str  = task.task_type.value.upper()

            print(f"  {status}  {time_str}   {type_str:<14}  {pet_label}{recur_tag}")

    completed = sum(1 for t in tasks if t.completed)
    remaining = len(tasks) - completed

    print(f"  {thin}")
    print(f"  {len(tasks)} task(s)  |  {completed} completed ✓  |  {remaining} remaining")
    print(f"{bar}\n")


def print_conflict_check(owner: Owner, candidate: Task) -> None:
    pet_index = {p.id: p for p in owner.pets}
    conflict  = owner.scheduler.detect_conflict(candidate)
    pet       = pet_index.get(candidate.pet_id)
    pet_name  = pet.name if pet else candidate.pet_id
    time_str  = candidate.scheduled_time.strftime("%I:%M %p")

    print(f"  Conflict check — {candidate.task_type.value} for {pet_name} at {time_str}")
    if conflict:
        conflict_pet  = pet_index.get(conflict.pet_id)
        conflict_name = conflict_pet.name if conflict_pet else conflict.pet_id
        print(f"  ⚠  Conflicts with: {conflict.task_type.value} for {conflict_name} "
              f"at {conflict.scheduled_time.strftime('%I:%M %p')}\n")
    else:
        print(f"  ✓  No conflict detected\n")


def main() -> None:
    today = datetime.now()

    # ── Owner & Pets ───────────────────────────────────────────────────────
    owner    = Owner("Alice")
    buddy    = Pet(id="p1", name="Buddy",    species="Golden Retriever", age=3)
    whiskers = Pet(id="p2", name="Whiskers", species="Persian Cat",      age=5)

    owner.add_pet(buddy)
    owner.add_pet(whiskers)

    # ── Tasks ──────────────────────────────────────────────────────────────
    tasks = [
        Task(
            id="t1", pet_id="p1",
            task_type=TaskType.FEEDING,
            scheduled_time=today_at(7, 0),
            recurring=True, frequency=Frequency.DAILY,
        ),
        Task(
            id="t2", pet_id="p2",
            task_type=TaskType.MEDICATION,
            scheduled_time=today_at(8, 30),
            recurring=True, frequency=Frequency.DAILY,
        ),
        Task(
            id="t3", pet_id="p1",
            task_type=TaskType.WALK,
            scheduled_time=today_at(12, 0),
        ),
        Task(
            id="t4", pet_id="p1",
            task_type=TaskType.FEEDING,
            scheduled_time=today_at(18, 0),
            recurring=True, frequency=Frequency.DAILY,
        ),
        Task(
            id="t5", pet_id="p2",
            task_type=TaskType.FEEDING,
            scheduled_time=today_at(18, 30),
            recurring=True, frequency=Frequency.DAILY,
        ),
    ]

    for task in tasks:
        owner.scheduler.add_task(task)

    # Simulate Buddy's morning feeding already being done
    tasks[0].mark_complete()

    # ── Schedule Output ────────────────────────────────────────────────────
    print_schedule(owner, today)

    # ── Conflict Detection Demo ────────────────────────────────────────────
    print("  Conflict Detection")
    print("  " + "─" * 40)

    # Should conflict — 7:05 AM is within 15 min of Buddy's 7:00 AM feeding
    near_conflict = Task(
        id="t_probe1", pet_id="p1",
        task_type=TaskType.WALK,
        scheduled_time=today_at(7, 5),
    )
    print_conflict_check(owner, near_conflict)

    # Should be clear — 10:00 AM has nothing nearby
    safe_task = Task(
        id="t_probe2", pet_id="p2",
        task_type=TaskType.APPOINTMENT,
        scheduled_time=today_at(10, 0),
    )
    print_conflict_check(owner, safe_task)


if __name__ == "__main__":
    main()
