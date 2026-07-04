# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.

you are a senior software engineer designing a pet care app with four classes which includes:  owner, Pet, scheduler and task. The owner will have a pet and be able to use the scheduler to schedule a task. This classes should have attributes and methods. This pet care app is a smart pet care management sustem that helps owners keeps their pet happy and friiendly, the app tracks daily routines --fedings, walks, medications, and appoinments while using algorithmic logic to organize and prioritize tasks.

You are a senior system designer create a mermaid.js class diagram with owners name and list of pets, methods to add , remove and get daily schedule. Pet will have an ID and name, specie, age and list of task, should  and remove task. The scheduler will be a list of tasks, have a method to add task, remove task, get sorted tasks, detect conflict and generate daily plan. Task will have an ID, type of task, datetime scheduled time, bool recurring, frequency, bool completed and a mark complete method.

- What classes did you include, and what responsibilities did you assign to each?

classes which includes:  owner, Pet, scheduler and task. The owner will have a pet and be able to use the scheduler to schedule a task. This classes should have attributes and methods. This pet care app is a smart pet care management sustem that helps owners keeps their pet happy and friiendly, the app tracks daily routines --fedings, walks, medications, and appoinments while using algorithmic logic to organize and prioritize tasks.

**b. Design changes**

- Did your design change during implementation?
yes
- If yes, describe at least one change and why you made it.

Summary Table
#	Issue	                                 Severity	                                       Fix
1	Owner missing self.scheduler	    High — broken feature	              Add Scheduler as attribute
2	Task missing pet_id         	    High — lost context in Scheduler	  Add pet_id: str to Task
3	Dual ownership of tasks      	    High — sync bugs in production	      Scheduler derives from Owner.pets
4	detect_conflict returns bool	    Medium — forces double lookup	      Return Optional[Task]
5	recurring + None frequency	        Medium — silent invalid state	      Add __post_init__ guard
6	generate_daily_plan has no date 	Medium — untestable	                  Add date: datetime param

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?

The scheduler enforces four constraints:

1. **Time** — every Task carries a `scheduled_time` (a Python `datetime`). The Scheduler flags any two active tasks whose times fall within a `conflict_window` (default 15 minutes) as a conflict. This is the primary constraint: a schedule without time is just a list.

2. **Task priority** — a `TASK_PRIORITY` dictionary ranks task types: MEDICATION (1) > APPOINTMENT (2) > FEEDING (3) > WALK (4). When two tasks land at the exact same time slot, `sorted()` uses priority as a tiebreaker so the most medically urgent task always appears first in the daily plan.

3. **Recurrence rules** — tasks declare DAILY, WEEKLY, or MONTHLY frequency. `_is_scheduled_on()` checks whether a task belongs on a given date using that rule, and a start-date guard prevents auto-spawned future tasks from bleeding into today's plan.

4. **Completion state** — `is_done_for(date)` tracks whether a specific day's instance of a recurring task has been completed. Completed tasks are excluded from conflict detection so a finished task never blocks a new one.

- How did you decide which constraints mattered most?

Time came first because without it there is no scheduler — just a to-do list. Priority came second because real pet care has clear urgency ordering: a missed medication has health consequences; a delayed walk does not. The 15-minute conflict window was set as the smallest practical buffer — tight enough to catch genuine double-bookings, wide enough to flag tasks that realistically can't both start on time. Completion state was added last, specifically to fix the bug where a finished recurring task kept blocking new slots even after it was done.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.

`add_task_safe()` always registers the task and returns a list of `ConflictWarning` objects rather than refusing the operation. The schedule can therefore contain unresolved conflicts — the method never raises an exception or rejects a task.

A secondary tradeoff is in recurring task handling: instead of computing occurrences on demand at query time, each call to `mark_task_complete()` physically spawns a new `Task` object (`spawn_next()`) for the next occurrence. The task list grows with every completion.

- Why is that tradeoff reasonable for this scenario?

**Warn-don't-block** is reasonable because the owner is the decision-maker, not the software. Two tasks at 9:00 AM may look like a conflict to the algorithm but be perfectly manageable in practice — filling a food bowl takes 30 seconds, which is compatible with starting a walk. Blocking the add would remove the owner's agency over their own schedule. The warning gives the information; the owner decides what to do with it.

**Spawn-on-complete** is reasonable because concrete Task objects are independently completable, reschedulable, and auditable. If Tuesday's medication is skipped, only Tuesday's instance is marked overdue — Wednesday's is untouched. Generating instances on demand would make individual-day overrides much harder to express, and for a single-owner pet schedule the list will never grow large enough for the memory cost to matter.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
I check if app.py successfully imports the logic layer! Adding a pet in the browser actually creates a Pet object that stays in memory.
- Why were these tests important?
FThe test is important because it test if the logic layer is accessible to the UI

**b. Confidence**

- How confident are you that your scheduler works correctly?
100% Confident
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
