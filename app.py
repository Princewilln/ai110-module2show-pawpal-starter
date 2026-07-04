import streamlit as st
from datetime import datetime, timedelta

from pawpal_system import Frequency, Owner, Pet, Task, TaskType

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Smart pet care scheduling — sorted, filtered, and conflict-aware.")

# ── Session State ──────────────────────────────────────────────────────────────
# Streamlit reruns top-to-bottom on every interaction. The "not in" guard keeps
# live data from being overwritten on each rerun.
if "owner" not in st.session_state:
    st.session_state.owner = None
if "pet_counter" not in st.session_state:
    st.session_state.pet_counter = 0
if "task_counter" not in st.session_state:
    st.session_state.task_counter = 0

# ── Step 1: Owner ──────────────────────────────────────────────────────────────
st.subheader("Step 1 — Create Owner")
st.caption("Calls: `Owner(name)` — wires the Scheduler automatically.")

owner_name = st.text_input("Owner name", value="Jordan")

if st.button("Create Owner"):
    st.session_state.owner = Owner(owner_name)
    st.session_state.pet_counter = 0
    st.session_state.task_counter = 0
    st.success(f"Owner **{owner_name}** created. Scheduler is ready.")

if st.session_state.owner is None:
    st.info("Enter a name and click **Create Owner** to unlock the rest of the app.")
    st.stop()

owner = st.session_state.owner

# ── Step 2: Add Pets ───────────────────────────────────────────────────────────
st.divider()
st.subheader("Step 2 — Add a Pet")
st.caption("Calls: `owner.add_pet(pet)` — add as many pets as needed.")

col1, col2, col3 = st.columns(3)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
with col3:
    age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)

if st.button("Add Pet"):
    new_pet = Pet(
        id=f"p{st.session_state.pet_counter}",
        name=pet_name,
        species=species,
        age=int(age),
    )
    try:
        owner.add_pet(new_pet)
        st.session_state.pet_counter += 1
        st.success(
            f"**{pet_name}** ({species}, age {int(age)}) added to {owner.name}'s care plan."
        )
    except ValueError as e:
        st.error(str(e))

if not owner.pets:
    st.info("Add at least one pet above before scheduling tasks.")
    st.stop()

pet_index = {p.id: p for p in owner.pets}

st.markdown("**Registered pets**")
st.table(
    [
        {
            "Name": p.name,
            "Species": p.species,
            "Age (yrs)": p.age,
            "Tasks": len(p.tasks),
        }
        for p in owner.pets
    ]
)

# ── Step 3: Schedule a Task ────────────────────────────────────────────────────
st.divider()
st.subheader("Step 3 — Schedule a Task")
st.caption(
    "Calls: `scheduler.add_task_safe(task)` — the task is **always added**. "
    "A conflict warning is shown when any existing task falls within 15 minutes."
)

pet_labels = {p.name: p.id for p in owner.pets}
selected_pet_name = st.selectbox("Pet", list(pet_labels.keys()))
selected_pet_id = pet_labels[selected_pet_name]

col4, col5, col6 = st.columns(3)
with col4:
    task_type_val = st.selectbox("Task type", [t.value for t in TaskType])
with col5:
    task_hour = st.number_input("Hour (0–23)", min_value=0, max_value=23, value=8)
with col6:
    task_min = st.number_input("Minute", min_value=0, max_value=59, value=0, step=15)

recurring = st.checkbox("Recurring?")
freq_val = None
if recurring:
    freq_val = st.selectbox("Frequency", [f.value for f in Frequency])

if st.button("Add Task"):
    scheduled_time = datetime.now().replace(
        hour=int(task_hour), minute=int(task_min), second=0, microsecond=0
    )
    candidate = Task(
        id=f"t{st.session_state.task_counter}",
        pet_id=selected_pet_id,
        task_type=TaskType(task_type_val),
        scheduled_time=scheduled_time,
        recurring=recurring,
        frequency=Frequency(freq_val) if freq_val else None,
    )

    # add_task_safe always registers the task and returns any ConflictWarning objects.
    # This is lightweight conflict detection: warn the owner but never block the operation.
    warnings = owner.scheduler.add_task_safe(candidate)
    st.session_state.task_counter += 1

    if warnings:
        for w in warnings:
            clash_pet = pet_index.get(w.task_b.pet_id)
            gap_sec = abs(
                (w.task_a.scheduled_time - w.task_b.scheduled_time).total_seconds()
            )
            gap_min = int(gap_sec // 60)
            gap_str = (
                "**exact same time**" if gap_min == 0 else f"**{gap_min} min apart**"
            )
            scope = (
                "same pet" if w.task_a.pet_id == w.task_b.pet_id else "different pet"
            )

            st.warning(
                f"⚠️ **Conflict detected** ({scope} · {gap_str})\n\n"
                f"The task was added, but it overlaps with an existing booking:"
            )

            # Side-by-side view: new task vs. clashing task
            c_new, c_vs, c_clash = st.columns([5, 1, 5])
            with c_new:
                st.markdown("**New task**")
                st.markdown(f"🐾 {selected_pet_name}")
                st.markdown(f"📋 {task_type_val.upper()}")
                st.markdown(f"🕐 {scheduled_time.strftime('%I:%M %p')}")
            with c_vs:
                st.markdown("&nbsp;")
                st.markdown("↔")
            with c_clash:
                st.markdown("**Existing task**")
                st.markdown(f"🐾 {clash_pet.name if clash_pet else w.task_b.pet_id}")
                st.markdown(f"📋 {w.task_b.task_type.value.upper()}")
                st.markdown(f"🕐 {w.task_b.scheduled_time.strftime('%I:%M %p')}")

            st.caption(
                "💡 **Tip:** Adjust one task by at least 15 minutes to clear this conflict."
            )
    else:
        recur_note = f" ↺ repeats {freq_val}" if recurring and freq_val else ""
        st.success(
            f"✅ **{task_type_val.capitalize()}** scheduled for **{selected_pet_name}** "
            f"at {scheduled_time.strftime('%I:%M %p')}{recur_note} — no conflicts."
        )

# ── Step 4: Today's Schedule ───────────────────────────────────────────────────
st.divider()
st.subheader("Step 4 — Today's Schedule")
st.caption(
    "Calls: `owner.get_daily_schedule(date)` → `Scheduler.generate_daily_plan()`. "
    "Tasks are sorted chronologically; same-time tasks are ordered by priority "
    "(Medication → Appointment → Feeding → Walk)."
)

today = datetime.now()

if st.button("Generate Schedule"):
    plan = owner.get_daily_schedule(today)

    if not plan:
        st.info("No tasks scheduled for today. Add some in Step 3.")
    else:
        # ── Summary metrics ───────────────────────────────────────────────────
        total = len(plan)
        done = sum(1 for t in plan if t.is_done_for(today))
        remaining = total - done

        m1, m2, m3 = st.columns(3)
        m1.metric("Total tasks", total)
        m2.metric("Completed ✅", done)
        m3.metric("Remaining 🔲", remaining)

        # ── Sorted task table ─────────────────────────────────────────────────
        rows = []
        for task in plan:
            pet = pet_index.get(task.pet_id)
            status = "✅ Done" if task.is_done_for(today) else "🔲 Pending"
            recur_tag = f"↺ {task.frequency.value}" if task.recurring else "—"
            rows.append(
                {
                    "Time": task.scheduled_time.strftime("%I:%M %p"),
                    "Task": task.task_type.value.upper(),
                    "Pet": pet.name if pet else task.pet_id,
                    "Recurring": recur_tag,
                    "Status": status,
                }
            )

        st.dataframe(rows, use_container_width=True, hide_index=True)

        if done == total:
            st.success("🎉 All tasks for today are complete — great job!")

# ── Step 5: Conflict Report ────────────────────────────────────────────────────
st.divider()
st.subheader("Step 5 — Conflict Report")
st.caption(
    "Calls: `scheduler.detect_all_conflicts()` — scans **every** active task pair, "
    "including cross-pet conflicts (the owner physically attends every task)."
)

if st.button("Run Full Conflict Scan"):
    all_conflicts = owner.scheduler.detect_all_conflicts()

    if not all_conflicts:
        st.success("✅ Schedule is conflict-free — no overlapping tasks detected.")
    else:
        st.error(
            f"⚠️ **{len(all_conflicts)} conflict(s) found.** "
            "Review each one below and adjust task times to resolve."
        )

        for i, w in enumerate(all_conflicts, 1):
            pet_a = pet_index.get(w.task_a.pet_id)
            pet_b = pet_index.get(w.task_b.pet_id)
            scope = "Same pet" if w.task_a.pet_id == w.task_b.pet_id else "Cross-pet"
            gap_sec = abs(
                (w.task_a.scheduled_time - w.task_b.scheduled_time).total_seconds()
            )
            gap_min = int(gap_sec // 60)
            gap_str = "exact same time" if gap_min == 0 else f"{gap_min} min apart"

            with st.expander(f"Conflict {i} — {scope} · {gap_str}", expanded=True):
                ca, csep, cb = st.columns([5, 1, 5])
                with ca:
                    st.markdown(f"**{w.task_a.task_type.value.upper()}**")
                    st.markdown(f"🐾 {pet_a.name if pet_a else w.task_a.pet_id}")
                    st.markdown(f"🕐 {w.task_a.scheduled_time.strftime('%I:%M %p')}")
                with csep:
                    st.markdown("↔")
                with cb:
                    st.markdown(f"**{w.task_b.task_type.value.upper()}**")
                    st.markdown(f"🐾 {pet_b.name if pet_b else w.task_b.pet_id}")
                    st.markdown(f"🕐 {w.task_b.scheduled_time.strftime('%I:%M %p')}")
                st.caption(
                    "💡 Move one task at least 15 minutes away to resolve this conflict."
                )

# ── Step 6: Filter Schedule ────────────────────────────────────────────────────
st.divider()
st.subheader("Step 6 — Filter Schedule")
st.caption(
    "Calls: `scheduler.filter_tasks(pet_name=..., completed=...)` — "
    "filters are ANDed. Results are sorted by time."
)

fcol1, fcol2 = st.columns(2)
with fcol1:
    filter_pet = st.selectbox("Pet", ["All pets"] + [p.name for p in owner.pets])
with fcol2:
    filter_status = st.selectbox("Status", ["All", "Pending", "Completed"])

filter_kwargs: dict = {}
if filter_pet != "All pets":
    filter_kwargs["pet_name"] = filter_pet
if filter_status == "Pending":
    filter_kwargs["completed"] = False
    filter_kwargs["reference_date"] = today
elif filter_status == "Completed":
    filter_kwargs["completed"] = True
    filter_kwargs["reference_date"] = today

filtered = owner.scheduler.filter_tasks(**filter_kwargs)

if not filtered:
    st.info("No tasks match the selected filters.")
else:
    filter_rows = []
    for task in filtered:
        pet = pet_index.get(task.pet_id)
        status = "✅ Done" if task.is_done_for(today) else "🔲 Pending"
        filter_rows.append(
            {
                "Time": task.scheduled_time.strftime("%I:%M %p"),
                "Task": task.task_type.value.upper(),
                "Pet": pet.name if pet else task.pet_id,
                "Status": status,
            }
        )
    st.dataframe(filter_rows, use_container_width=True, hide_index=True)

# ── Step 7: Mark Task Complete ─────────────────────────────────────────────────
st.divider()
st.subheader("Step 7 — Mark Task Complete")
st.caption(
    "Calls: `scheduler.mark_task_complete(task_id)` — "
    "daily and weekly recurring tasks automatically spawn the next occurrence."
)

pending_tasks = [t for pet in owner.pets for t in pet.tasks if not t.is_done_for(today)]

if not pending_tasks:
    st.success("🎉 All tasks are complete for today — nothing left to do!")
else:

    def task_label(t: Task) -> str:
        pet = pet_index.get(t.pet_id)
        name = pet.name if pet else t.pet_id
        return (
            f"{t.task_type.value.upper()} — {name} "
            f"@ {t.scheduled_time.strftime('%I:%M %p')}  [{t.id}]"
        )

    label_to_id = {task_label(t): t.id for t in pending_tasks}
    selected_label = st.selectbox("Select task", list(label_to_id.keys()))
    selected_id = label_to_id[selected_label]

    if st.button("Mark Complete"):
        spawned = owner.scheduler.mark_task_complete(selected_id, on_date=today)
        if spawned:
            next_dt = spawned.scheduled_time.strftime("%A, %B %d at %I:%M %p")
            st.success(
                f"✅ Task marked complete.\n\n"
                f"**Next occurrence auto-scheduled:** "
                f"{spawned.task_type.value.upper()} on {next_dt}  "
                f"(ID: `{spawned.id}`)"
            )
        else:
            st.success("✅ Task marked complete.")
