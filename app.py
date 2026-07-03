import streamlit as st
from datetime import datetime

from pawpal_system import Frequency, Owner, Pet, Task, TaskType

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Smart pet care management — powered by your backend classes.")

# ── Session State Vault ────────────────────────────────────────────────────
# Streamlit reruns this entire script top-to-bottom on every button click.
# The "not in" guard checks the vault first so a rerun never overwrites live data.
if "owner" not in st.session_state:
    st.session_state.owner = None

if "pet_counter" not in st.session_state:
    st.session_state.pet_counter = 0

if "task_counter" not in st.session_state:
    st.session_state.task_counter = 0

# ── Step 1: Create Owner ───────────────────────────────────────────────────
st.subheader("Step 1 — Create Owner")
st.caption("Calls: `Owner(name)` — also wires the Scheduler internally.")

owner_name = st.text_input("Owner name", value="Jordan")

if st.button("Create Owner"):
    st.session_state.owner = Owner(owner_name)   # Owner.__init__ wires Scheduler automatically
    st.session_state.pet_counter  = 0            # reset counters on a fresh owner
    st.session_state.task_counter = 0
    st.success(f"Owner '{owner_name}' created. Scheduler is ready.")

if st.session_state.owner is None:
    st.info("Enter a name and click 'Create Owner' to unlock the rest of the app.")
    st.stop()

owner = st.session_state.owner   # local alias into the vault

# ── Step 2: Add a Pet ──────────────────────────────────────────────────────
st.divider()
st.subheader("Step 2 — Add a Pet")
st.caption("Calls: `owner.add_pet(pet)` — you can add as many pets as needed.")

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
        owner.add_pet(new_pet)                   # → registers pet; raises if duplicate id
        st.session_state.pet_counter += 1
        st.success(f"'{pet_name}' ({species}, {int(age)} yrs) added to {owner.name}'s pets.")
    except ValueError as e:
        st.error(str(e))

# Live pet roster — updates every rerun because owner lives in session_state
if owner.pets:
    st.markdown("**Registered pets:**")
    st.table([
        {"Name": p.name, "Species": p.species, "Age (yrs)": p.age, "Tasks": len(p.tasks)}
        for p in owner.pets
    ])
else:
    st.info("No pets yet — add one above before scheduling tasks.")
    st.stop()

pet_index = {p.id: p for p in owner.pets}   # id → Pet lookup, shared by Steps 3 & 4

# ── Step 3: Schedule a Task ────────────────────────────────────────────────
st.divider()
st.subheader("Step 3 — Schedule a Task")
st.caption("Calls: `owner.scheduler.detect_conflict(task)` then `owner.scheduler.add_task(task)`.")

pet_labels        = {p.name: p.id for p in owner.pets}
selected_pet_name = st.selectbox("Pet", list(pet_labels.keys()))
selected_pet_id   = pet_labels[selected_pet_name]

col4, col5, col6 = st.columns(3)
with col4:
    task_type_val = st.selectbox("Task type", [t.value for t in TaskType])
with col5:
    task_hour = st.number_input("Hour (0–23)", min_value=0, max_value=23, value=8)
with col6:
    task_min = st.number_input("Minute", min_value=0, max_value=59, value=0, step=15)

recurring = st.checkbox("Recurring?")
freq_val  = None
if recurring:
    freq_val = st.selectbox("Frequency", [f.value for f in Frequency])

if st.button("Schedule Task"):
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

    conflict = owner.scheduler.detect_conflict(candidate)   # check before committing

    if conflict:
        clash_pet = pet_index.get(conflict.pet_id)
        st.warning(
            f"⚠ Conflict — '{task_type_val}' at {scheduled_time.strftime('%I:%M %p')} "
            f"clashes with '{conflict.task_type.value}' for "
            f"**{clash_pet.name if clash_pet else conflict.pet_id}** "
            f"at {conflict.scheduled_time.strftime('%I:%M %p')}. Task not added."
        )
    else:
        owner.scheduler.add_task(candidate)          # → routed to Pet.add_task() via pet_id
        st.session_state.task_counter += 1
        st.success(
            f"'{task_type_val}' scheduled for {selected_pet_name} "
            f"at {scheduled_time.strftime('%I:%M %p')}."
        )

    # Refresh the pet roster so task counts stay current
    st.markdown("**Updated pet roster:**")
    st.table([
        {"Name": p.name, "Species": p.species, "Age (yrs)": p.age, "Tasks": len(p.tasks)}
        for p in owner.pets
    ])

# ── Step 4: Today's Schedule ───────────────────────────────────────────────
st.divider()
st.subheader("Step 4 — Today's Schedule")
st.caption("Calls: `owner.get_daily_schedule(date)` → `Scheduler.generate_daily_plan(date)`.")

if st.button("Generate Schedule"):
    plan = owner.get_daily_schedule(datetime.now())

    if not plan:
        st.info("No tasks for today. Schedule some tasks in Step 3.")
    else:
        for task in plan:
            pet    = pet_index.get(task.pet_id)
            status = "✅" if task.completed else "🔲"
            recur  = f"  ↺ *{task.frequency.value}*" if task.recurring else ""
            st.markdown(
                f"{status} **{task.scheduled_time.strftime('%I:%M %p')}** — "
                f"`{task.task_type.value.upper()}` → **{pet.name if pet else task.pet_id}**{recur}"
            )
        completed = sum(1 for t in plan if t.completed)
        st.caption(
            f"{len(plan)} task(s) today — {completed} done, {len(plan) - completed} remaining."
        )
