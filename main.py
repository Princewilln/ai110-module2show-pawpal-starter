"""
PawPal+ — main.py  (Conflict Detection Demo)
=============================================
Demonstrates lightweight conflict detection in Scheduler:

  add_task_safe(task)      — always registers the task, returns list[ConflictWarning]
  detect_all_conflicts()   — full scan of all active task pairs, returns list[ConflictWarning]

ConflictWarning.message is a pre-formatted string — the program never crashes;
callers read warnings and decide what to do.

Conflict scenarios tested:
  1. Same pet, exact same time
  2. Different pets, exact same time
  3. Same pet, within the 15-minute overlap window
  4. Clean task (no overlap) — confirms empty warning list
"""

from datetime import datetime

from pawpal_system import ConflictWarning, Owner, Pet, Task, TaskType

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


def print_warnings(warnings: list[ConflictWarning]) -> None:
    """Print every ConflictWarning message, or a clear ✓ when none exist."""
    if not warnings:
        print("    ✓  No conflicts — schedule is clear.")
    else:
        for w in warnings:
            print(f"    {w.message}")


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

    owner    = Owner("Alice")
    buddy    = Pet(id="p1", name="Buddy",    species="Golden Retriever", age=3)
    whiskers = Pet(id="p2", name="Whiskers", species="Persian Cat",      age=5)
    owner.add_pet(buddy)
    owner.add_pet(whiskers)
    pet_index = {p.id: p for p in owner.pets}

    print_header("PawPal+ — Lightweight Conflict Detection")
    print(f"  Owner : {owner.name}")
    print("  Pets  : Buddy (Golden Retriever)  |  Whiskers (Persian Cat)")
    print(f"  Conflict window : {owner.scheduler.conflict_window.seconds // 60} minutes")

    # ── Anchor task: Buddy's walk at 09:00 AM ─────────────────────────────
    #   Added with plain add_task — no conflicts yet (schedule is empty)
    print_section("SETUP — anchor task, no conflicts yet")
    owner.scheduler.add_task(Task(
        id="walk_buddy",
        pet_id="p1",
        task_type=TaskType.WALK,
        scheduled_time=today_at(9, 0),
    ))
    print("    Added: walk_buddy  (Buddy, WALK @ 09:00 AM)")
    print_warnings(owner.scheduler.detect_all_conflicts())

    # ── DEMO 1: Same pet, exact same time ─────────────────────────────────
    #   Buddy already has a walk at 09:00.
    #   Adding a feeding at 09:00 for the same pet → same-pet conflict.
    print_section("DEMO 1 — same pet, exact same time")
    print("    Adding: feed_buddy  (Buddy, FEEDING @ 09:00 AM)\n")

    w1 = owner.scheduler.add_task_safe(Task(
        id="feed_buddy",
        pet_id="p1",
        task_type=TaskType.FEEDING,
        scheduled_time=today_at(9, 0),
    ))
    print_warnings(w1)

    # ── DEMO 2: Different pets, exact same time ────────────────────────────
    #   Whiskers gets a medication at 09:00 — same slot already has two Buddy tasks.
    #   Owner can only physically be in one place, so this is a cross-pet conflict too.
    print_section("DEMO 2 — different pets, exact same time")
    print("    Adding: med_whiskers  (Whiskers, MEDICATION @ 09:00 AM)\n")

    w2 = owner.scheduler.add_task_safe(Task(
        id="med_whiskers",
        pet_id="p2",
        task_type=TaskType.MEDICATION,
        scheduled_time=today_at(9, 0),
    ))
    print_warnings(w2)

    # ── DEMO 3: Same pet, within the 15-minute overlap window ────────────
    #   Buddy's appointment at 09:08 — only 8 minutes after the 09:00 cluster.
    #   Still within the 15-minute conflict_window.
    print_section("DEMO 3 — same pet, 8 min apart  (within 15-min window)")
    print("    Adding: appt_buddy  (Buddy, APPOINTMENT @ 09:08 AM)\n")

    w3 = owner.scheduler.add_task_safe(Task(
        id="appt_buddy",
        pet_id="p1",
        task_type=TaskType.APPOINTMENT,
        scheduled_time=today_at(9, 8),
    ))
    print_warnings(w3)

    # ── DEMO 4: Clean task — no conflict ──────────────────────────────────
    #   Afternoon walk for Whiskers at 03:00 PM — nothing nearby.
    #   add_task_safe returns an empty list → prints the clear message.
    print_section("DEMO 4 — clean task, no overlap")
    print("    Adding: walk_whiskers  (Whiskers, WALK @ 03:00 PM)\n")

    w4 = owner.scheduler.add_task_safe(Task(
        id="walk_whiskers",
        pet_id="p2",
        task_type=TaskType.WALK,
        scheduled_time=today_at(15, 0),
    ))
    print_warnings(w4)

    # ── FULL SCAN: detect_all_conflicts() ────────────────────────────────
    #   Scans every active pair — same-pet AND cross-pet.
    #   Returns a ConflictWarning for each pair within the window.
    print_section("FULL SCAN — detect_all_conflicts()  (all active task pairs)")
    all_w = owner.scheduler.detect_all_conflicts()
    print(f"    {len(all_w)} conflict(s) found:\n")
    print_warnings(all_w)

    # ── CURRENT SCHEDULE ──────────────────────────────────────────────────
    #   All 5 tasks were registered — add_task_safe never blocked anything.
    print_section(f"TODAY'S SCHEDULE  ({today.strftime('%A, %B %d')})  — all tasks registered")
    for t in owner.scheduler.sort_by_time():
        print_task_row(t, pet_index, today)

    print()


if __name__ == "__main__":
    main()
