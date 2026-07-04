# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

When I started, I sketched out four classes: `Owner`, `Pet`, `Scheduler`, and `Task`. The idea was pretty straightforward — an owner has pets, pets have tasks, and a scheduler figures out the order. I drafted the UML in Mermaid first before writing any Python, which forced me to think about what each class was actually responsible for before I got distracted by implementation details.

The original diagram had `Owner`, `Pet`, `Scheduler`, and `Task` with simple association arrows between them. At that point `Task` just had an ID, a type, a scheduled time, a recurring boolean, and a `mark_complete()` method. `Scheduler` had about five methods. That was it.

What I didn't think through at the start was how `Scheduler` would actually get access to the pets' tasks — I just had a vague arrow. That turned out to be one of the first real design problems I had to solve.

**b. Design changes**

Yes, the design changed pretty significantly once I started implementing. Here's an honest summary of what broke early and what I changed:

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| 1 | `Owner` had no `self.scheduler` attribute — I was treating it as a standalone object | High | Made `Scheduler` an attribute of `Owner`, wired in `__init__` |
| 2 | `Task` had no `pet_id` — the scheduler couldn't route tasks back to the right pet | High | Added `pet_id: str` to `Task` |
| 3 | `Scheduler` held its own separate pet list, which meant `Owner.pets` and `Scheduler.pets` could drift out of sync | High | Made `Scheduler` hold a shared reference to `Owner.pets` — same list object, no syncing needed |
| 4 | `detect_conflict()` returned a `bool` — caller had to do a second lookup to find out *which* task caused the conflict | Medium | Changed return type to `Optional[Task]` |
| 5 | A `Task` could be created with `recurring=True` and `frequency=None`, which was silently invalid | Medium | Added a `__post_init__` guard that raises `ValueError` immediately |
| 6 | `generate_daily_plan()` had no `date` parameter — it always used "today" which made it impossible to test | Medium | Added `date: datetime` as an explicit argument |

The biggest lesson from all of this was that the UML I drew before coding looked clean but hid several implicit assumptions — like assuming "the scheduler knows about all the pets" without specifying *how* it knows. Implementation forced me to be explicit about things the diagram was glossing over.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

My scheduler considers four constraints:

1. **Time** — every `Task` carries a `scheduled_time` (a Python `datetime`). The `Scheduler` flags any two active tasks whose times fall within a `conflict_window` (default 15 minutes) as a conflict. This is the primary constraint — a schedule without time is just a to-do list.

2. **Task priority** — a `TASK_PRIORITY` dict ranks task types: MEDICATION (1) > APPOINTMENT (2) > FEEDING (3) > WALK (4). When two tasks land at the same time, `sorted()` uses this as a tiebreaker so the most urgent task always appears first in the daily plan.

3. **Recurrence rules** — tasks declare DAILY, WEEKLY, or MONTHLY frequency. `_is_scheduled_on()` checks whether a task belongs on a given date, and a start-date guard prevents auto-spawned future tasks from leaking into today's plan.

4. **Completion state** — `is_done_for(date)` tracks whether a specific day's instance of a recurring task has been completed. Completed tasks are excluded from conflict detection so a finished task doesn't block new ones from being added.

**How I decided which constraints mattered most:**

Time came first because without it there's no scheduler — just a list. Priority came second because real pet care has a clear urgency order: a missed medication has real health consequences; a delayed walk usually doesn't. The 15-minute conflict window was chosen as the smallest practical buffer — tight enough to catch actual double-bookings, wide enough to flag tasks that realistically can't both start on time. Completion state was added later, specifically to fix a bug where a finished recurring task kept blocking new slots even after it was done.

**b. Tradeoffs**

The biggest tradeoff in my scheduler is what I'm calling **warn-don't-block**. `add_task_safe()` always registers the task regardless of conflicts and returns a list of `ConflictWarning` objects instead of raising an exception or refusing the add. The schedule can therefore contain unresolved conflicts — that's intentional.

A secondary tradeoff is in how recurring tasks work. Instead of computing future occurrences on demand at query time, each call to `mark_task_complete()` physically spawns a new `Task` object (`spawn_next()`) for the next occurrence. The task list grows with every completion.

**Why these are reasonable:**

Warn-don't-block is the right call because the owner is the decision-maker, not the app. Two tasks at 9:00 AM might look like a conflict to the algorithm but be fine in practice — filling a bowl takes 30 seconds, which is compatible with starting a walk. Blocking the add would take away the owner's agency. The warning gives the information; the owner decides what to do with it.

Spawn-on-complete is reasonable because concrete Task objects are independently completable, reschedulable, and auditable. If Tuesday's medication gets skipped, only Tuesday's instance is marked overdue — Wednesday's instance is untouched. Computing occurrences on demand would make individual-day overrides much harder to express. For a single-owner pet schedule the task list will never grow large enough for the memory cost to matter.

---

## 3. AI Collaboration

**a. How I used AI**

I used Claude as my AI coding assistant throughout this project, but I tried to use it in phases rather than just pasting in "build me a pet app." Here's roughly how it broke down:

- **Design phase** — I described what I wanted the system to do in plain English and asked it to point out anything my UML was missing. That's where I found out `Task` needed a `pet_id` and that the dual-ownership problem with the `Scheduler.pets` list would cause sync bugs.

- **Implementation** — Once I had class stubs, I'd ask it to implement one method at a time. I'd give it the method signature and a sentence about what it should do, then read the output carefully before accepting it.

- **Debugging** — When something felt off (like `detect_conflict()` returning a bool), I'd describe the problem and ask what a better return type would be. Usually one prompt was enough to get an option I could evaluate.

- **Testing** — I asked it to generate test stubs for the behaviors I cared about, then went through each one and either kept it, tweaked it, or threw it out if it was testing the wrong thing.

The most effective prompts were specific ones with a constraint: "What are the most important edge cases to test for a pet scheduler with sorting and recurring tasks?" worked much better than "write me some tests." Giving it the design context — not just the code — got much better answers.

**b. One moment where I didn't accept the AI suggestion**

Early on, when I was building the task-adding flow, the AI suggested implementing conflict detection as a hard block: call `detect_conflict()` before adding the task, and if a conflict exists, don't add the task at all and show an error. The code looked like this:

```python
conflict = scheduler.detect_conflict(candidate)
if conflict:
    st.error("Conflict — task not added.")
else:
    scheduler.add_task(candidate)
```

I rejected this. The reason is that "task not added" puts the app in the position of overriding the owner's decision, which isn't the right dynamic for a personal care tool. A pet owner who knows their own routine better than the algorithm should be able to add overlapping tasks if they want to. The warning-not-block design (`add_task_safe()`) was the right call, and the AI was defaulting to the more obvious "reject on conflict" pattern without considering the UX tradeoff.

I modified it to always register the task and return warnings as data, letting the UI decide what to display. This also simplified the backend — `add_task_safe()` doesn't need to know anything about UI logic.

**c. How separate sessions helped**

I used different chat sessions for different phases — UML review, implementation, test generation, and the Streamlit UI wiring. This helped more than I expected. When I was working on tests, I didn't want the session full of implementation context making the AI second-guess what I was trying to verify. A fresh session with just the class structure and "here are the behaviors I need to test" got cleaner, more focused test stubs.

It also helped me stay organized as the person driving the work. Mixing "fix this bug" with "now write tests" with "now update the README" in one long session would have made it hard to track what decisions had been made and why. Keeping them separate forced me to re-summarize the relevant context each time, which also meant I was regularly re-checking my own understanding.

**d. What I learned about being the lead architect**

The biggest thing I learned is that AI is very fast at producing code but has no idea what your system is *for* unless you tell it — repeatedly and specifically. It will generate technically correct solutions to the wrong problem if you're not precise about the intent.

Being the lead architect meant I had to know what I wanted before I asked for it. When I didn't have a clear idea — like early on when I hadn't thought through the ownership of the task list — the AI's suggestions felt plausible but introduced bugs I didn't catch until implementation. When I came in with a clear constraint ("the Scheduler needs to share Owner's pets list, not hold its own copy"), the output was immediately usable.

The relationship that worked for me was: I make the design decisions, the AI handles the boilerplate and catches things I might miss. I never let it make architectural choices without running them through my own reasoning first — and that saved me from a few suggestions that were clean in isolation but would have made the system harder to test or extend.

---

## 4. Testing and Verification

**a. What I tested**

My final test suite has 32 tests across six groups:

1. **Sorting** — verified that tasks come back in chronological order when added out of order, and that MEDICATION beats WALK when both are scheduled at the same time slot.

2. **Conflict detection** — tested the full boundary spectrum: same-pet same-time, cross-pet same-time, 8 minutes apart (within window), exactly 15 minutes apart (not a conflict — the condition is `< window`, not `<=`), and 20 minutes apart (clean). Also tested that a completed task doesn't block its old time slot.

3. **Recurring spawn** — confirmed that `mark_task_complete()` on a daily task spawns a new Task shifted +1 day, retires the original (`recurring=False, completed=True`), and that the lineage ID chain increments correctly: `"feed1"` → `"feed1#2"` → `"feed1#3"`.

4. **Per-date completion** — verified that a recurring task marked done today shows as pending on a different date using `is_done_for()`, and that non-recurring tasks stay completed permanently.

5. **Daily plan guard** — confirmed a spawned task stays out of today's plan but appears in tomorrow's, and that a date with no tasks returns an empty list rather than crashing.

6. **Edge cases** — pet with zero tasks, recurring task created without a frequency (should raise `ValueError`), task assigned to the wrong pet (should raise `ValueError`), recurring tasks excluded from overdue checks, duplicate pet IDs rejected.

**Why these tests mattered:**

Most of the edge cases came directly from bugs I hit during development. The boundary test (exactly 15 minutes apart) exists because I initially wrote `<=` instead of `<` and didn't notice until I thought carefully about what the condition should be. The recurring task overdue test exists because I realized recurring tasks could slip into `get_overdue_tasks()` if I wasn't careful about the filter condition. Real bugs caught by tests I wrote because of the experience of writing the code.

**b. Confidence**

I'd say 4 out of 5. The core logic — sorting, conflict detection, recurring spawn, per-date completion — I'm very confident in because those behaviors are fully covered by tests that I verified individually. The area I'm less certain about is monthly recurring tasks: the `spawn_next()` logic for monthly uses `replace(month=...)` with a fallback for short months, and I only wrote smoke-level tests for that path. I'd want to test February 28/29 edge cases and month-end rollovers more thoroughly before trusting it in production. The Streamlit UI also has no automated tests — I verified it manually by running the app, but that's not the same as a proper test.

---

## 5. Reflection

**a. What went well**

The part I'm most satisfied with is how the `ConflictWarning` + `add_task_safe()` design came together. Making `ConflictWarning` a frozen dataclass with a `.message` property meant the conflict information is self-contained — any caller (CLI, Streamlit, test) can use it without knowing anything about how it was generated. And `add_task_safe()` always adding the task regardless of conflicts kept the backend totally decoupled from the UI's display logic. That boundary is clean and I think it would hold up well if someone added a different frontend later.

The test suite also went better than expected. I ended up with 32 tests covering behaviors I actually care about, not just happy paths. Writing them made me find two real bugs — the `<=` vs `<` boundary issue and the fact that recurring tasks were briefly slipping through the overdue filter. Tests that catch real bugs are much more satisfying than tests that just confirm things you already knew worked.

**b. What I would improve**

The biggest gap in the current design is that tasks have a scheduled *start time* but no *duration*. That means the conflict window (15 minutes) is a rough proxy for "these two tasks are too close together" rather than "these two tasks actually overlap." A walk that takes 45 minutes and a feeding that starts 20 minutes later are technically outside the conflict window but obviously can't both happen on time. If I had another iteration I'd add a `duration: timedelta` to `Task` and update conflict detection to check actual time intervals rather than a fixed buffer.

I'd also add integration tests for the Streamlit UI — at least smoke tests that verify the session state initializes correctly and that `add_task_safe()` is being called (not the old `detect_conflict()` pattern). Right now the only UI verification is manual.

**c. Key takeaway**

The most important thing I learned from this project is that designing with AI is a fundamentally different skill than coding with AI. When I asked AI to write code, I got code. When I asked AI to help me think through a design decision — "should conflict detection block or warn?" — I got trade-off analysis that I still had to evaluate myself.

Being the lead architect means your main job is making the decisions the AI can't make: what the system is for, who it serves, what the right tradeoff is between strictness and flexibility. AI can execute those decisions very fast once they're made. But if you outsource the decision itself to the AI, you end up with a system that's technically correct and misses the point. I learned to treat AI like a very capable colleague who needs a clear brief — not a designer who can figure out the intent on their own.

