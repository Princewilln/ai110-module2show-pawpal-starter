# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
# e.g.:
# Daily plan for Biscuit (Golden Retriever):
#   08:00 — Morning walk (30 min) [priority: high]
#   09:00 — Feeding (10 min) [priority: high]
#   ...
```

```
  ○  12:00 PM   WALK            Buddy (Golden Retriever)
  ○  06:00 PM   FEEDING         Buddy (Golden Retriever)  ↺ daily
  ○  06:30 PM   FEEDING         Whiskers (Persian Cat)  ↺ daily
  ────────────────────────────────────────────────────────────────
  5 task(s)  |  1 completed ✓  |  4 remaining
================================================================

  Conflict Detection
  ────────────────────────────────────────
  Conflict check — walk for Buddy at 07:05 AM
  ⚠  Conflicts with: feeding for Buddy at 07:00 AM

  Conflict check — appointment for Whiskers at 10:00 AM
  ✓  No conflict detected
```



## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here

(.venv) meltingtech@meltingtech:~/codepath/ai110-module2show-pawpal-starter$ .venv/bin/pytest tests/test_pawpal.py -v
===================================================================================================================================================================== test session starts ======================================================================================================================================================================
platform linux -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0 -- /home/meltingtech/codepath/ai110-module2show-pawpal-starter/.venv/bin/python3.13
cachedir: .pytest_cache
rootdir: /home/meltingtech/codepath/ai110-module2show-pawpal-starter
plugins: anyio-4.14.1
collected 2 items                                                                                                                                                                                                                                                                                                                                              

tests/test_pawpal.py::test_mark_complete_changes_task_status PASSED                                                                                                                                                                                                                                                                                      [ 50%]
tests/test_pawpal.py::test_add_task_increases_pet_task_count PASSED                                                                                                                                                                                                                                                                                      [100%]

====================================================================================================================================================================== 2 passed in 0.02s =======================================================================================================================================================================
(.venv) meltingtech@meltingtech:~/codepath/ai110-module2show-pawpal-starter$ 

```

latet test

```
(.venv) meltingtech@meltingtech:~/codepath/ai110-module2show-pawpal-starter$ python3 -m pytest
===================================================================================================================================== test session starts ======================================================================================================================================
platform linux -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/meltingtech/codepath/ai110-module2show-pawpal-starter
plugins: anyio-4.14.1
collected 32 items                                                                                                                                                                                                                                                                             

tests/test_pawpal.py ................................                                                                                                                                                                                                                                    [100%]

====================================================================================================================================== 32 passed in 0.03s ======================================================================================================================================


What the PawPal+ test suite covers
32 tests across 6 groups:

Sorting — tasks added out of order come back chronologically; when two tasks share a time slot, the priority ranking (Medication → Appointment → Feeding → Walk) breaks the tie.

Conflict Detection — same-pet same-time triggers a warning; cross-pet same-time also triggers one (owner attends both); 8 minutes apart warns, exactly 15 minutes apart does not; completed tasks don't block their old slot.

Recurring Spawn — marking a daily task complete registers a new task shifted +1 day; the original is retired (recurring=False, completed=True); the ID chain increments correctly (feed1 → feed1#2 → feed1#3); weekly tasks shift +7 days; non-recurring tasks return None.

Per-date Completion — a recurring task marked done today shows as pending tomorrow; a non-recurring task stays completed permanently regardless of date.

Daily Plan Guard — a spawned task (due tomorrow) is excluded from today's plan but appears in tomorrow's; a date with no tasks returns an empty list.

Edge Cases — pet with zero tasks never crashes; recurring=True with no frequency raises ValueError; adding a task to the wrong pet raises ValueError; recurring tasks are never flagged as overdue; duplicate pet IDs are rejected.

Confidence Level" (1–5 stars) in the system's reliability based on my test results is 4.5

```
## 📐 Smarter Scheduling

All scheduling intelligence lives in `pawpal_system.py` across the `Task`,
`ConflictWarning`, and `Scheduler` classes.

---

### 1. Sorting

| Method | Behaviour |
|--------|-----------|
| `Scheduler.sort_by_time(tasks=None)` | Sorts by a `"HH:MM"` string key via `strftime`. Zero-padded 24-hour strings compare lexicographically in the correct time order (`"07:00" < "08:30" < "18:00"`), so no numeric conversion is needed. Pass a subset list to sort a filtered result, or call with no argument to sort every task in the scheduler. |
| `Scheduler.get_sorted_tasks()` | Full sort using a two-element tuple key `(scheduled_time, TASK_PRIORITY[task_type])`. When two tasks share the same time slot, task priority breaks the tie. Used internally by conflict detection and daily-plan generation. |

**Priority ranking** (`TASK_PRIORITY` dict in `pawpal_system.py`):

| Rank | TaskType | Reasoning |
|------|----------|-----------|
| 1 | `MEDICATION` | Highest — health impact if missed |
| 2 | `APPOINTMENT` | External party is waiting |
| 3 | `FEEDING` | Consistent but flexible by minutes |
| 4 | `WALK` | Lowest — most adjustable in timing |

---

### 2. Filtering

| Method | Filter criteria |
|--------|-----------------|
| `Scheduler.filter_tasks(*, pet_name, completed, reference_date)` | Combined filter: pass `pet_name` (human-readable string), `completed` (`True`/`False`), or both. All supplied arguments are ANDed. Results returned via `sort_by_time()`. |
| `Scheduler.filter_by_pet(pet_id)` | All tasks for one pet by internal ID, sorted by time and priority. Raises `ValueError` if the pet is not registered. |
| `Scheduler.filter_by_status(completed, reference_date)` | Tasks matching the completion flag on the given date. For recurring tasks, "completed" is per-date (via `Task.is_done_for()`), not a permanent boolean — the same daily feeding is done today but pending again tomorrow. |
| `Scheduler.get_overdue_tasks(now)` | Non-recurring tasks whose `scheduled_time` has passed and `completed` is still `False`. Recurring tasks are excluded — they never go overdue because `mark_task_complete()` auto-spawns a fresh instance instead. |

---

### 3. Conflict Detection

PawPal+ uses **lightweight conflict detection**: the program never crashes or
rejects a task. Warnings are returned as data and the caller decides what to do.

| Method / Class | Role |
|----------------|------|
| `ConflictWarning` (frozen dataclass) | Holds the two clashing `Task` objects. The `.message` property formats a ready-to-print string showing scope (`same pet` / `different pets`), gap in minutes, task IDs, types, and times. `frozen=True` — warnings are immutable facts, not editable state. |
| `Scheduler.add_task_safe(task)` | Registers the task unconditionally, then returns `list[ConflictWarning]` for every active task within the `conflict_window`. Empty list = no clashes. Suitable for real-time feedback as the owner builds their schedule. |
| `Scheduler.detect_conflict(task)` | Probes one candidate task and returns the **first** conflicting active task, or `None`. For single-task pre-flight checks before committing an add. |
| `Scheduler.detect_all_conflicts()` | Full scan of every active task pair — **both same-pet and cross-pet**. The owner physically attends every task, so two tasks at the same time clash regardless of which pet they belong to. Returns `list[ConflictWarning]`. |

**Algorithm optimisations in `detect_all_conflicts()`:**

- `abs()` removed — input is pre-sorted, so `b` is always ≥ `a` in time; the gap is always non-negative.
- `conflict_window.total_seconds()` hoisted above the loops — computed once, not n·(n−1)/2 times.
- `break` on `gap >= window` — sorted order guarantees no later `b` can conflict with `a`, making the inner loop O(k) per step where k ≈ tasks-per-slot (usually 1–2).

---

### 4. Recurring Tasks

| Method | Behaviour |
|--------|-----------|
| `Task.spawn_next()` | Creates and returns the **next instance** of a recurring task using `timedelta`: `DAILY → scheduled_time + timedelta(days=1)`, `WEEKLY → scheduled_time + timedelta(weeks=1)`. Assigns a lineage ID so the chain is traceable: `"feed_buddy"` → `"feed_buddy#2"` → `"feed_buddy#3"`. |
| `Scheduler.mark_task_complete(task_id)` | Orchestrates the full completion sequence in four steps: (1) call `spawn_next()` to build the next instance, (2) call `mark_complete()` on the original, (3) set `recurring=False` and `completed=True` to retire the original so it stops appearing in future daily plans, (4) register the new instance. Returns the spawned `Task`, or `None` for non-recurring and monthly tasks. |
| `Task.is_done_for(on_date)` | Per-date completion check. Recurring tasks store each completed date in `completed_dates: set[date]`; non-recurring tasks use the permanent `completed` bool. This lets a daily task reset each morning without requiring a new object for every new day. |
| `Scheduler._is_scheduled_on(task, date)` | Decides whether a task belongs in a given day's plan. Includes a **start-date guard** (`if date < task.scheduled_time.date(): return False`) that prevents a spawned task due tomorrow from appearing in today's daily plan. |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
