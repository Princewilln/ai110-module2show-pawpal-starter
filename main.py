"""
PawPal+ — main.py demo
======================
Demonstrates auto-rescheduling: when a daily or weekly recurring task is
marked complete, Scheduler.mark_task_complete() uses Python's timedelta to
compute the next due date and registers a fresh Task automatically.

Key timedelta rules implemented in Task.spawn_next():
    DAILY  → next_time = scheduled_time + timedelta(days=1)
    WEEKLY → next_time = scheduled_time + timedelta(weeks=1)
"""

from datetime import datetime, timedelta

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
    recur_tag = f"  ↺ {t.frequency.value}" if t.recurring else "  (retired)"
    time_str  = t.scheduled_time.strftime("%I:%M %p")
    type_str  = t.task_type.value.upper()
    print(f"    {status}  {time_str}   {type_str:<14}  {pet_label}{recur_tag}")


def print_all_tasks(scheduler) -> None:
    """Print every task in the scheduler, sorted by full datetime (spans multiple days)."""
    all_tasks = sorted(
        [t for pet in scheduler.pets for t in pet.tasks],
        key=lambda t: t.scheduled_time,
    )
    print(f"    {'ID':<18}  {'DUE DATE':<24}  {'TYPE':<12}  {'STATUS'}")
    print(f"    {THIN[:60]}")
    for t in all_tasks:
        due = t.scheduled_time.strftime("%a %b %d  %I:%M %p")
        if t.completed:
            status = "✓ done / retired"
        elif not t.recurring:
            status = "○ pending (one-off)"
        else:
            status = f"○ pending  ↺ {t.frequency.value}"
        print(f"    {t.id:<18}  {due}  {t.task_type.value:<12}  {status}")


def print_daily_plan(owner: Owner, date: datetime, pet_index: dict) -> None:
    tasks = owner.get_daily_schedule(date)
    label = date.strftime("%A, %B %d")
    print_section(f"DAILY PLAN — {label}")
    if not tasks:
        print("    (no tasks scheduled)")
        return
    for t in tasks:
        print_task_row(t, pet_index, date)
    done = sum(1 for t in tasks if t.is_done_for(date))
    print(f"\n    {len(tasks)} task(s) — {done} done, {len(tasks) - done} pending")


# ── Main demo ──────────────────────────────────────────────────────────────────

def main() -> None:
    today    = datetime.now()
    tomorrow = today + timedelta(days=1)
    day_2    = today + timedelta(days=2)

    # ── Setup ──────────────────────────────────────────────────────────────
    owner    = Owner("Alice")
    buddy    = Pet(id="p1", name="Buddy",    species="Golden Retriever", age=3)
    whiskers = Pet(id="p2", name="Whiskers", species="Persian Cat",      age=5)
    owner.add_pet(buddy)
    owner.add_pet(whiskers)
    pet_index = {p.id: p for p in owner.pets}

    print_header("PawPal+ — Auto-Reschedule with timedelta")
    print(f"  Owner : {owner.name}")
    print("  Pets  : Buddy (Golden Retriever)  |  Whiskers (Persian Cat)")

    # Three recurring tasks — two daily, one weekly
    owner.scheduler.add_task(Task(
        id="feed_buddy", pet_id="p1",
        task_type=TaskType.FEEDING,
        scheduled_time=today_at(7, 0),
        recurring=True, frequency=Frequency.DAILY,
    ))
    owner.scheduler.add_task(Task(
        id="walk_buddy", pet_id="p1",
        task_type=TaskType.WALK,
        scheduled_time=today_at(8, 0),
        recurring=True, frequency=Frequency.WEEKLY,
    ))
    owner.scheduler.add_task(Task(
        id="med_whiskers", pet_id="p2",
        task_type=TaskType.MEDICATION,
        scheduled_time=today_at(9, 0),
        recurring=True, frequency=Frequency.DAILY,
    ))

    # ── Before any completions ─────────────────────────────────────────────
    print_section("INITIAL TASK LIST  (3 tasks, all pending)")
    print_all_tasks(owner.scheduler)

    # ── Step 1: complete a DAILY task ─────────────────────────────────────
    #   spawn_next() runs: next_time = scheduled_time + timedelta(days=1)
    print_section("STEP 1 — mark_task_complete('feed_buddy')  [DAILY]")
    print("    Logic inside spawn_next():")
    print("      next_time = scheduled_time + timedelta(days=1)")
    print(f"      next_time = {today_at(7, 0).strftime('%b %d')} 07:00 AM  +  1 day")
    print(f"             → {(today_at(7, 0) + timedelta(days=1)).strftime('%a %b %d')} 07:00 AM\n")

    spawned = owner.scheduler.mark_task_complete("feed_buddy")

    print("    feed_buddy    → completed=True, recurring=False  (retired)")
    print(f"    {spawned.id:<14} → created, due {spawned.scheduled_time.strftime('%A %b %d at %I:%M %p')}")

    # ── Step 2: complete the spawned task — proves the chain continues ─────
    #   feed_buddy#2 is also DAILY → spawns feed_buddy#3
    print_section("STEP 2 — mark_task_complete('feed_buddy#2')  [chain: generation 3]")
    spawned2 = owner.scheduler.mark_task_complete("feed_buddy#2")
    print("    feed_buddy#2  → completed=True, recurring=False  (retired)")
    print(f"    {spawned2.id:<14} → created, due {spawned2.scheduled_time.strftime('%A %b %d at %I:%M %p')}")

    # ── Step 3: complete a WEEKLY task ────────────────────────────────────
    #   spawn_next() runs: next_time = scheduled_time + timedelta(weeks=1)
    print_section("STEP 3 — mark_task_complete('walk_buddy')  [WEEKLY]")
    print("    Logic inside spawn_next():")
    print("      next_time = scheduled_time + timedelta(weeks=1)")
    print(f"      next_time = {today_at(8, 0).strftime('%a %b %d')} 08:00 AM  +  7 days")
    print(f"             → {(today_at(8, 0) + timedelta(weeks=1)).strftime('%a %b %d')} 08:00 AM\n")

    spawned_walk = owner.scheduler.mark_task_complete("walk_buddy")
    print("    walk_buddy    → completed=True, recurring=False  (retired)")
    print(f"    {spawned_walk.id:<14} → created, due {spawned_walk.scheduled_time.strftime('%A %b %d at %I:%M %p')}")

    # ── Full task list after all completions ───────────────────────────────
    print_section("ALL TASKS — after 3 completions  (5 tasks now: 3 retired + 2 active + 1 untouched)")
    print_all_tasks(owner.scheduler)

    # ── Daily plans across 3 days ──────────────────────────────────────────
    #   Today:     feed_buddy ✓, walk_buddy ✓, med_whiskers ○
    #   Tomorrow:  feed_buddy#2 ✓ (already marked done), med_whiskers ○
    #   Day +2:    feed_buddy#3 ○ (first fresh instance), med_whiskers ○
    print_daily_plan(owner, today,    pet_index)
    print_daily_plan(owner, tomorrow, pet_index)
    print_daily_plan(owner, day_2,    pet_index)

    print()


if __name__ == "__main__":
    main()
