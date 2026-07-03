"""
PawPal+ — main.py demo
======================
Demonstrates:
  1. sort_by_time()  — sorted() with a lambda key on "HH:MM" strings
  2. filter_tasks()  — filter by pet name, completion status, or both
"""

from datetime import datetime

from pawpal_system import Frequency, Owner, Pet, Task, TaskType

SEP  = "=" * 64
THIN = "─" * 64


def today_at(hour: int, minute: int = 0) -> datetime:
    return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)


# ── Print helpers ──────────────────────────────────────────────────────────────

def print_header(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def print_section(label: str) -> None:
    print(f"\n  {label}")
    print(f"  {THIN}")


def print_task_row(t: Task, pet_index: dict, ref: datetime) -> None:
    pet       = pet_index.get(t.pet_id)
    pet_label = pet.name if pet else t.pet_id
    status    = "✓" if t.is_done_for(ref) else "○"
    recur_tag = f"  ↺ {t.frequency.value}" if t.recurring else ""
    time_str  = t.scheduled_time.strftime("%I:%M %p")
    type_str  = t.task_type.value.upper()
    print(f"    {status}  {time_str}   {type_str:<14}  {pet_label}{recur_tag}")


# ── Main demo ──────────────────────────────────────────────────────────────────

def main() -> None:
    today = datetime.now()

    # ── Setup ──────────────────────────────────────────────────────────────
    owner    = Owner("Alice")
    buddy    = Pet(id="p1", name="Buddy",    species="Golden Retriever", age=3)
    whiskers = Pet(id="p2", name="Whiskers", species="Persian Cat",      age=5)
    owner.add_pet(buddy)
    owner.add_pet(whiskers)

    pet_index = {p.id: p for p in owner.pets}

    print_header("PawPal+ — Sort & Filter Demo")
    print(f"  Owner : {owner.name}")
    print("  Pets  : Buddy (Golden Retriever)  |  Whiskers (Persian Cat)")

    # ── Tasks added INTENTIONALLY out of order ─────────────────────────────
    #   Evening tasks are registered first, morning tasks last,
    #   so the raw list order does NOT match the schedule order.
    tasks = [
        Task(                                   # ← added first, but latest in the day
            id="t5", pet_id="p2",
            task_type=TaskType.FEEDING,
            scheduled_time=today_at(18, 30),
            recurring=True, frequency=Frequency.DAILY,
        ),
        Task(                                   # ← evening walk for Buddy
            id="t4", pet_id="p1",
            task_type=TaskType.WALK,
            scheduled_time=today_at(17, 0),
        ),
        Task(                                   # ← midday appointment
            id="t3", pet_id="p2",
            task_type=TaskType.APPOINTMENT,
            scheduled_time=today_at(11, 0),
        ),
        Task(                                   # ← mid-morning medication
            id="t2", pet_id="p1",
            task_type=TaskType.MEDICATION,
            scheduled_time=today_at(9, 0),
            recurring=True, frequency=Frequency.DAILY,
        ),
        Task(                                   # ← added last, but earliest in the day
            id="t1", pet_id="p1",
            task_type=TaskType.FEEDING,
            scheduled_time=today_at(7, 0),
            recurring=True, frequency=Frequency.DAILY,
        ),
        Task(                                   # ← Whiskers noon feeding
            id="t6", pet_id="p2",
            task_type=TaskType.FEEDING,
            scheduled_time=today_at(12, 0),
            recurring=True, frequency=Frequency.DAILY,
        ),
    ]

    for task in tasks:
        owner.scheduler.add_task(task)

    # ── SECTION 1: Raw insertion order ────────────────────────────────────
    #   This is what the list looks like before any sorting — scrambled.
    print_section("RAW INSERTION ORDER  (tasks added out of order on purpose)")
    print("    id    time        type")
    print(f"    {THIN[:44]}")
    for t in [t for pet in owner.pets for t in pet.tasks]:
        print(f"    {t.id:<6}  {t.scheduled_time.strftime('%I:%M %p')}  {t.task_type.value}")

    # ── SECTION 2: sort_by_time() ─────────────────────────────────────────
    #   sorted() uses a lambda that extracts the "HH:MM" string from each task.
    #   Zero-padded 24-hour strings compare lexicographically in time order:
    #     "07:00" < "09:00" < "11:00" < "12:00" < "17:00" < "18:30"
    print_section('SORTED BY TIME  —  sort_by_time() uses: key=lambda t: t.scheduled_time.strftime("%H:%M")')
    print("    id    time        type")
    print(f"    {THIN[:44]}")
    for t in owner.scheduler.sort_by_time():
        print(f"    {t.id:<6}  {t.scheduled_time.strftime('%I:%M %p')}  {t.task_type.value}")

    # ── SECTION 3: filter_tasks(pet_name=...) ─────────────────────────────
    #   Pass pet_name to get only that pet's tasks, already sorted by time.
    print_section("FILTER BY PET NAME  —  filter_tasks(pet_name='Buddy')")
    for t in owner.scheduler.filter_tasks(pet_name="Buddy"):
        print_task_row(t, pet_index, today)

    print_section("FILTER BY PET NAME  —  filter_tasks(pet_name='Whiskers')")
    for t in owner.scheduler.filter_tasks(pet_name="Whiskers"):
        print_task_row(t, pet_index, today)

    # ── SECTION 4: filter_tasks(completed=...) ────────────────────────────
    #   Mark two tasks done, then filter on status.
    tasks[4].mark_complete(on_date=today)   # Buddy's 7 AM feeding ✓
    tasks[1].mark_complete()                # Buddy's 5 PM walk ✓  (non-recurring → permanent)

    print_section("FILTER BY STATUS  —  filter_tasks(completed=True)  [done tasks]")
    done = owner.scheduler.filter_tasks(completed=True, reference_date=today)
    if done:
        for t in done:
            print_task_row(t, pet_index, today)
    else:
        print("    (none)")

    print_section("FILTER BY STATUS  —  filter_tasks(completed=False)  [still pending]")
    pending = owner.scheduler.filter_tasks(completed=False, reference_date=today)
    for t in pending:
        print_task_row(t, pet_index, today)

    # ── SECTION 5: Combined filter ────────────────────────────────────────
    #   Both arguments are ANDed — only Buddy's pending tasks.
    print_section("COMBINED FILTER  —  filter_tasks(pet_name='Buddy', completed=False)")
    for t in owner.scheduler.filter_tasks(pet_name="Buddy", completed=False, reference_date=today):
        print_task_row(t, pet_index, today)

    print()


if __name__ == "__main__":
    main()
