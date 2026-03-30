import streamlit as st
from datetime import UTC, date, datetime, time, timedelta
from pawpal_system import Frequency, Owner, Pet, Priority, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pinned_overlaps(owner: Owner, start: datetime, end: datetime) -> list:
    """Return all pinned tasks across every pet that overlap [start, end)."""
    return [
        t for p in owner.get_pets()
        for t in p.get_tasks()
        if t.scheduled_start and t.scheduled_end
        and start < t.scheduled_end and end > t.scheduled_start
    ]



def _fmt_time(t) -> str:
    """Format a time object as e.g. '6a', '9p', '8:30a'."""
    h = t.hour % 12 or 12
    suffix = "a" if t.hour < 12 else "p"
    mins = f":{t.minute:02d}" if t.minute else ""
    return f"{h}{mins}{suffix}"


def _task_pet_map(owner: Owner) -> dict[str, str]:
    """Map task.id -> pet.name for all tasks across all pets."""
    return {
        t.id: p.name
        for p in owner.get_pets()
        for t in p.get_tasks()
    }


# ---------------------------------------------------------------------------
# 1. Owner (account-style)
# ---------------------------------------------------------------------------

if "owners" not in st.session_state:
    st.session_state.owners = {}
if "active_owner" not in st.session_state:
    st.session_state.active_owner = None
if "show_switch" not in st.session_state:
    st.session_state.show_switch = False

active = st.session_state.active_owner

with st.expander(active if active else "Owner", expanded=active is None):
    if active is None:
        new_name = st.text_input("Enter your name to get started", key="owner_name_input")
        if st.button("Continue", disabled=not new_name.strip()):
            name = new_name.strip()
            if name not in st.session_state.owners:
                st.session_state.owners[name] = Owner(name=name)
            st.session_state.active_owner = name
            st.session_state.show_switch = False
            st.rerun()
    else:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"Signed in as **{active}**")
        with col2:
            if st.button("Switch user"):
                st.session_state.show_switch = not st.session_state.show_switch
                st.rerun()

        if st.session_state.show_switch:
            st.caption("Select an existing account or create a new one:")
            others = [n for n in st.session_state.owners if n != active]
            for name in others:
                if st.button(f"Switch to {name}", key=f"sw_{name}"):
                    st.session_state.active_owner = name
                    st.session_state.show_switch = False
                    st.rerun()
            new_name2 = st.text_input("New owner name", key="new_owner_input")
            if st.button("Create new", disabled=not new_name2.strip()):
                name = new_name2.strip()
                if name not in st.session_state.owners:
                    st.session_state.owners[name] = Owner(name=name)
                st.session_state.active_owner = name
                st.session_state.show_switch = False
                st.rerun()

owner: Owner = st.session_state.owners.get(active, Owner(name="?")) if active else Owner(name="?")

st.divider()

# ---------------------------------------------------------------------------
# 2. Availability
# ---------------------------------------------------------------------------

_DAYS_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

with st.expander("Availability", expanded=False):
    if active:
        from pawpal_system import _default_weekly_availability

        st.caption("Flexible tasks will only be auto-scheduled within these windows.")

        # ── All-days shortcut ─────────────────────────────────────────────
        all_same = st.checkbox("Same window every day", key="avail_all_same")
        if all_same:
            c1, c2 = st.columns(2)
            bulk_s = c1.time_input("From (all days)", value=time(8, 0), key="bulk_s")
            bulk_e = c2.time_input("To (all days)",   value=time(21, 0), key="bulk_e")
            if bulk_e > bulk_s:
                for i in range(7):
                    owner.preferences.weekly_availability[i] = [(bulk_s, bulk_e)]
            else:
                st.warning("End must be after start.")

        # ── Per-day rows ──────────────────────────────────────────────────
        for i, day in enumerate(_DAYS_FULL):
            windows  = owner.preferences.weekly_availability.get(i, [])
            is_off   = len(windows) == 0
            cur_s    = windows[0][0] if windows else time(8, 0)
            cur_e    = windows[0][1] if windows else time(21, 0)

            c_name, c_from, c_to, c_off = st.columns([2, 2, 2, 1])
            c_name.write(f"**{day}**")
            off = c_off.checkbox("Off", key=f"off_{i}", value=is_off, disabled=all_same)

            if all_same:
                c_from.caption(f"{_fmt_time(cur_s)}")
                c_to.caption(f"{_fmt_time(cur_e)}")
            elif off:
                owner.preferences.weekly_availability[i] = []
                c_from.caption("—")
                c_to.caption("—")
            else:
                ns = c_from.time_input("From", value=cur_s, key=f"from_{i}", label_visibility="collapsed")
                ne = c_to.time_input(  "To",   value=cur_e, key=f"to_{i}",   label_visibility="collapsed")
                if ne > ns:
                    owner.preferences.weekly_availability[i] = [(ns, ne)]
                else:
                    c_to.caption("⚠ end ≤ start")

        if st.button("Reset to defaults", key="avail_reset"):
            owner.preferences.weekly_availability = _default_weekly_availability()
            for i in range(7):
                for k in [f"from_{i}", f"to_{i}", f"off_{i}"]:
                    st.session_state.pop(k, None)
            for k in ["avail_all_same", "bulk_s", "bulk_e"]:
                st.session_state.pop(k, None)
            st.rerun()
    else:
        st.info("Sign in above to configure availability.")

st.divider()

# ---------------------------------------------------------------------------
# 3. Pets
# ---------------------------------------------------------------------------

st.subheader("3. Pets")
col1, col2 = st.columns(2)
with col1:
    new_pet_name = st.text_input("Pet name", value="Mochi", key="new_pet_name")
with col2:
    new_species = st.selectbox("Species", ["dog", "cat", "other"], key="new_pet_species")

if st.button("Add pet"):
    if new_pet_name.strip():
        owner.add_pet(Pet(name=new_pet_name.strip(), species=new_species))
        st.rerun()

pets = owner.get_pets()
if pets:
    for p in pets:
        col1, col2 = st.columns([5, 1])
        with col1:
            n = len(p.get_tasks())
            st.write(f"**{p.name}** ({p.species}) — {n} task{'s' if n != 1 else ''}")
        with col2:
            if st.button("Remove", key=f"remove_pet_{p.id}"):
                owner.pets = [x for x in owner.pets if x.id != p.id]
                owner._pets_by_id.pop(p.id, None)
                st.rerun()
else:
    st.info("No pets yet — add one above.")

st.divider()

# ---------------------------------------------------------------------------
# 4. Add a Task
# ---------------------------------------------------------------------------

with st.expander("Task", expanded=True):
    if not pets:
        st.info("Add a pet first.")
    else:
        pet_options = {p.name: p for p in pets}
        selected_pet_name = st.selectbox("For pet", list(pet_options.keys()), key="task_pet_select")
        pet: Pet = pet_options[selected_pet_name]

        col1, col2, col3 = st.columns(3)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
        with col2:
            duration = st.number_input("Duration (min)", min_value=1, max_value=480, value=20)
        with col3:
            priority = st.selectbox("Priority", ["high", "medium", "low"])

        task_description = st.text_area("Description (optional)", value="", height=68)

        freq_labels = {f.value: f for f in Frequency}
        frequency = st.selectbox("Frequency", list(freq_labels.keys()))

        schedule_type = st.radio(
            "Scheduling",
            ["Flexible (auto-assign slot)", "Pinned (exact time)"],
            horizontal=True,
        )

        pinned_start: datetime | None = None
        pinned_end: datetime | None = None

        if schedule_type == "Pinned (exact time)":
            pin_date = st.date_input("On date", value=date.today(), key="pin_date")
            col1, col2 = st.columns(2)
            with col1:
                start_val = st.time_input("Start time (UTC)", value=time(8, 0))
            with col2:
                end_val = st.time_input("End time (UTC)", value=time(9, 0))

            pinned_start = datetime.combine(pin_date, start_val, tzinfo=UTC)
            pinned_end   = datetime.combine(pin_date, end_val,   tzinfo=UTC)

            if pinned_end <= pinned_start:
                st.error("End time must be after start time.")
                pinned_start = pinned_end = None
            else:
                duration = int((pinned_end - pinned_start).total_seconds() // 60)
                st.caption(f"Duration: {duration} min")
                overlaps = _pinned_overlaps(owner, pinned_start, pinned_end)
                if overlaps:
                    names = ", ".join(f"**{t.title}**" for t in overlaps)
                    st.warning(
                        f"Overlaps with: {names}. "
                        "Adding anyway will flag a conflict in the schedule."
                    )

        if st.button("Add task"):
            if schedule_type == "Pinned (exact time)" and pinned_start is None:
                st.error("Fix the time range before adding.")
            else:
                owner.schedule_task(
                    pet_id=pet.id,
                    title=task_title,
                    description=task_description,
                    duration_minutes=int(duration),
                    priority=priority,
                    frequency=freq_labels[frequency],
                    scheduled_start=pinned_start,
                    scheduled_end=pinned_end,
                )
                st.success(f"Added '{task_title}' for {pet.name}")

        # Task list for the selected pet
        tasks = pet.get_tasks()
        if tasks:
            st.write(f"**{pet.name}'s tasks ({len(tasks)}):**")
            _prio_opts = ["high", "medium", "low"]
            _freq_opts = list(freq_labels.keys())
            for t in tasks:
                col1, col2 = st.columns([5, 1])
                with col1:
                    pinned_label = (
                        f" · {t.scheduled_start.strftime('%I:%M %p')}–"
                        f"{t.scheduled_end.strftime('%I:%M %p')} UTC"
                        if t.scheduled_start else ""
                    )
                    st.write(
                        f"**{t.title}** — {t.duration_minutes} min · "
                        f"{t.priority.value} · {t.frequency.value}{pinned_label}"
                    )
                with col2:
                    if st.button("Remove", key=f"rm_{t.id}"):
                        pet._remove_task(t.id)
                        st.rerun()

                with st.expander(f"Edit '{t.title}'"):
                    e_title = st.text_input("Title", value=t.title, key=f"e_title_{t.id}")
                    e_desc  = st.text_area("Description", value=t.description, key=f"e_desc_{t.id}", height=68)
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        e_prio = st.selectbox("Priority", _prio_opts,
                                              index=_prio_opts.index(t.priority.value),
                                              key=f"e_prio_{t.id}")
                    with ec2:
                        e_freq = st.selectbox("Frequency", _freq_opts,
                                              index=_freq_opts.index(t.frequency.value),
                                              key=f"e_freq_{t.id}")

                    e_pin = st.checkbox("Pinned to specific time",
                                        value=t.scheduled_start is not None,
                                        key=f"e_pin_{t.id}")
                    if e_pin:
                        cur = t.scheduled_start or datetime.combine(date.today(), time(8, 0), tzinfo=UTC)
                        e_date  = st.date_input("Date", value=cur.date(), key=f"e_date_{t.id}")
                        e_start = st.time_input("Start (UTC)", value=cur.timetz().replace(tzinfo=None), key=f"e_start_{t.id}")
                        e_dur   = st.number_input("Duration (min)", min_value=1, max_value=480,
                                                  value=t.duration_minutes, key=f"e_dur_{t.id}")
                        new_start = datetime.combine(e_date, e_start, tzinfo=UTC)
                        new_end   = new_start + timedelta(minutes=int(e_dur))
                        st.caption(f"End time: {new_end.strftime('%I:%M %p')} UTC")
                    else:
                        e_dur     = st.number_input("Duration (min)", min_value=1, max_value=480,
                                                    value=t.duration_minutes, key=f"e_dur_{t.id}")
                        new_start = None
                        new_end   = None

                    if st.button("Save changes", key=f"save_{t.id}"):
                        t.title            = e_title
                        t.description      = e_desc
                        t.priority         = Priority(e_prio)
                        t.frequency        = freq_labels[e_freq]
                        t.duration_minutes = int(e_dur)
                        t.scheduled_start  = new_start
                        t.scheduled_end    = new_end
                        t.conflict_flag    = False
                        st.rerun()
        else:
            st.info(f"No tasks for {pet.name} yet.")

st.divider()

# ---------------------------------------------------------------------------
# 5. Generate Daily Schedule (all pets)
# ---------------------------------------------------------------------------

st.subheader("5. Generate Daily Schedule")

all_tasks = [t for p in owner.get_pets() for t in p.get_tasks()]

if not owner.get_pets():
    st.info("Add pets and tasks first.")
elif not all_tasks:
    st.info("Add at least one task first.")
else:
    target_date = st.date_input("Schedule for", value=date.today(), key="schedule_date")

    if st.button("Generate schedule"):
        scheduler = Scheduler()
        windows = owner.preferences.get_windows_for_date(target_date)
        scheduled = scheduler.generate_daily_schedule(owner, target_date, windows)
        pet_map = _task_pet_map(owner)

        st.markdown(f"### {owner.name}'s plan for {target_date}")

        conflicts = [t for t in scheduled if t.conflict_flag]
        if conflicts:
            names = ", ".join(f"**{t.title}**" for t in conflicts)
            st.error(
                f"Unresolvable conflict between pinned tasks: {names}. "
                "Flexible tasks were already bumped automatically — "
                "edit one of the pinned tasks above to fix this."
            )

        rows = []
        for t in scheduled:
            if t.scheduled_start and t.scheduled_end:
                time_str = (
                    f"{t.scheduled_start.strftime('%I:%M %p')} – "
                    f"{t.scheduled_end.strftime('%I:%M %p')}"
                )
            else:
                time_str = "unscheduled (no room)"

            rows.append({
                "Time (UTC)": time_str,
                "Pet": pet_map.get(t.id, "?"),
                "Task": t.title,
                "Duration (min)": t.duration_minutes,
                "Priority": t.priority.value,
                "⚠️": "conflict" if t.conflict_flag else "",
            })

        st.table(rows)

        with st.expander("Full explanation"):
            st.code(scheduler.explain(scheduled))