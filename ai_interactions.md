# AI Interactions Log

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

I used Claude Code (Anthropic's CLI agent) across several sessions to handle multi-step tasks I'd scoped out. The biggest single autonomous run was: "Review `pawpal_system.py`, list 3–5 core behaviors to verify, identify the most important edge cases for a pet scheduler with sorting and recurring tasks, then generate a full pytest suite covering happy paths and edge cases."

That was one prompt that turned into the agent reading the source file, reading the existing two-test file, generating 32 tests across six groups, running `pytest` to confirm they all passed, and explaining every test before saving the final file.

**What did the agent do?**

In that session the agent:

1. Read `pawpal_system.py` to understand every class, method, and relationship
2. Read `tests/test_pawpal.py` to see what was already covered (two tests at the time)
3. Identified the five core behaviors to test: sorting with tiebreaker, conflict detection in/out of window, recurring auto-spawn, per-date completion, and the daily plan start-date guard
4. Identified eight edge cases: pet with no tasks, same-time conflict, 15-minute boundary, recurring without frequency, `spawn_next()` on non-recurring, wrong pet assignment, recurring task overdue exclusion, and ID lineage chain
5. Wrote all 32 tests with class-based grouping (`TestSorting`, `TestConflictDetection`, etc.) and shared helper factories (`make_pet`, `make_task`, `at()`)
6. Ran `pytest` — all 32 passed on the first run
7. Explained each test in plain English, including why the boundary test exists and what real bug it catches

In a separate session, the agent also autonomously updated `app.py` in one pass — switching from the blocking `detect_conflict()` pattern to `add_task_safe()`, adding `st.metric` summary tiles, replacing the bare markdown schedule with `st.dataframe`, and adding Steps 5–7 (conflict scan, filter, mark complete).

**What did you have to verify or fix manually?**

A few things needed human review before I accepted them:

- **The conflict detection approach** — the agent initially suggested blocking the add on conflict. I overrode that to use `add_task_safe()` (warn-not-block). The agent implemented whatever I decided, but the decision was mine.
- **Test scope** — the agent's first pass on test ideas included some redundant tests that were just confirming the same thing twice. I trimmed those down and redirected it toward the boundary cases I actually cared about.
- **Conflict warning UI layout** — the agent's first version of the warning was a single `st.warning` text block. I asked it to redo it as a side-by-side column layout, which made the two conflicting tasks much easier to compare at a glance.
- **UML relationships** — the agent updated the Mermaid diagram but I had to check that the `Scheduler o-- Pet` aggregation arrow was correct (shared reference, not ownership) and that the `Task ..> Task` self-reference for `spawn_next()` was included.

---

## Prompt Comparison (SF11)

> Compare two different prompts on the same task: generating conflict detection tests.

| | Option A — Vague prompt | Option B — Constrained prompt |
|-|------------------------|-------------------------------|
| **Prompt** | "Write tests for the conflict detection in my scheduler." | "What are the most important edge cases to test for conflict detection in a pet scheduler where the window is 15 minutes and completed tasks should not block new ones? Then write pytest functions for each." |
| **Response summary** | Generated three tests: same time = conflict, different time = no conflict, and one for `detect_all_conflicts()` counting results. All correct but shallow. | Generated seven tests covering: same-pet same-time, cross-pet same-time, 8 min apart (inside window), exactly 15 min (boundary — NOT a conflict), 20 min (outside), full scan counting all pairs, and completed task not blocking new slot. |
| **What was useful** | Fast, no setup needed | Directly addressed the real failure modes — especially the `<` vs `<=` boundary |
| **Problems noticed** | Missed the cross-pet case entirely. Missed the boundary. Missed the completed-task exclusion. | Slightly longer prompt but the output needed almost no editing |
| **Decision** | Discarded after review | Used this version in the final test suite |

**Which approach did you use in your final implementation and why?**

Option B. The key insight was that giving the agent the *constraint* ("15-minute window," "completed tasks should not block") meant it could reason about what would break the invariant rather than just generating happy-path tests. Vague prompts get plausible tests; constrained prompts get tests that actually catch bugs. The boundary test (`test_exactly_at_window_boundary_is_no_conflict`) only appeared when I told the agent the window was `< 15`, not `<= 15` — without that context it had no way to know the condition was worth testing at the edge.
