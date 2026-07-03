import streamlit as st
from datetime import datetime

from pawpal_system import Frequency, Owner, Pet, Task, TaskType

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Smart pet care management — powered by your backend classes.")

# ── Session State Vault ────────────────────────────────────────────────────
# Streamlit reruns this entire script top-to-bottom on every button click.
# The "not in" guard checks the vault first — if the key already exists we
# leave it untouched, so a rerun never overwrites live data.
if "owner" not in st.session_state:
    st.session_state.owner = None

if "task_counter" not in st.session_state:
    st.session_state.task_counter = 0

if "pet_counter" not in st.session_state:
    st.session_state.pet_counter = 0

# ── Step 1: Owner & Pet Setup ──────────────────────────────────────────────
st.subheader("Step 1 — Owner & Pet")

col1, col2 = st.columns(2)
with col1:
    owner_name = st.text_input("Owner name", value="Jordan")
with col2:
    pet_name = st.text_input("Pet name", value="Mochi")

col3, col4 = st.columns(2)
with col3:
    species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
with col4:
    age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)

if st.button("Create Owner & Pet"):
    new_owner = Owner(owner_name)
    new_pet   = Pet(
        id=f"p{st.session_state.pet_counter}",
        name=pet_name,
        species=species,
        age=int(age),
    )
    st.session_state.pet_counter += 1
    new_owner.add_pet(new_pet)
    st.session_state.owner = new_owner   # store the Owner object in the vault
    st.success(f"'{owner_name}' registered with pet '{pet_name}' ({species}, {int(age)} yrs).")

# Guard: nothing below this line renders until the vault holds an Owner.
if st.session_state.owner is None:
    st.info("Complete Step 1 above to unlock the rest of the app.")
    st.stop()

owner     = st.session_state.owner          # local alias — reads from the vault
pet_index = {p.id: p for p in owner.pets}  # id → Pet, used by both steps below

# ── Step 2: Add a Task ─────────────────────────────────────────────────────
st.divider()
st.subheader("Step 2 — Add a Task")

pet_labels        = {p.name: p.id for p in owner.pets}
selected_pet_name = st.selectbox("Pet", list(pet_labels.keys()))
selected_pet_id   = pet_labels[selected_pet_name]

col5, col6, col7 = st.columns(3)
with col5:
    task_type_val = st.selectbox("Task type", [t.value for t in TaskType])
with col6:
    task_hour = st.number_input("Hour (0–23)", min_value=0, max_value=23, value=8)
with col7:
    task_min = st.number_input("Minute", min_value=0, max_value=59, value=0, step=15)

recurring = st.checkbox("Recurring?")
freq_val  = None
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

    conflict = owner.scheduler.detect_conflict(candidate)
    if conflict:
        clash_pet = pet_index.get(conflict.pet_id)
        st.warning(
            f"⚠ Conflict detected — '{task_type_val}' at "
            f"{scheduled_time.strftime('%I:%M %p')} clashes with "
            f"'{conflict.task_type.value}' for "
            f"**{clash_pet.name if clash_pet else conflict.pet_id}** "
            f"at {conflict.scheduled_time.strftime('%I:%M %p')}. Task not added."
        )
    else:
        owner.scheduler.add_task(candidate)
        st.session_state.task_counter += 1
        st.success(
            f"'{task_type_val}' added for {selected_pet_name} "
            f"at {scheduled_time.strftime('%I:%M %p')}."
        )

# ── Step 3: Today's Schedule ───────────────────────────────────────────────
st.divider()
st.subheader("Step 3 — Today's Schedule")

if st.button("Generate Schedule"):
    plan = owner.get_daily_schedule(datetime.now())
    if not plan:
        st.info("No tasks scheduled for today. Add some tasks in Step 2.")
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
        st.caption(f"{len(plan)} task(s) today — {completed} done, {len(plan) - completed} remaining.")
