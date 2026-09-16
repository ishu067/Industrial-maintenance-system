from datetime import date

import pandas as pd
import streamlit as st

from frontend import api

st.set_page_config(page_title="Robotic Arm Operations", page_icon="RA", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Space+Grotesk:wght@500;600&display=swap');
:root { --ink: #17191c; --muted: #687078; --line: #dfe2e5; --paper: #f7f8f9; --panel: #ffffff; --accent: #1f6f68; --warn: #a05a17; --danger: #a83b3b; }
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; color: var(--ink); }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { background: var(--paper) !important; }
.main h1, .main h2, .main h3, .main p, .main label, .main [data-testid="stMarkdownContainer"], .main [data-testid="stMetricValue"] { color: var(--ink) !important; }
.main [data-testid="stDataFrame"] { color: var(--ink) !important; }
[data-testid="stAppViewContainer"] h1, [data-testid="stAppViewContainer"] h2, [data-testid="stAppViewContainer"] h3, [data-testid="stAppViewContainer"] p, [data-testid="stAppViewContainer"] label, [data-testid="stAppViewContainer"] .metric-value { color: var(--ink) !important; }
.metric-value { color: var(--ink) !important; }
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; letter-spacing: 0; }
[data-testid="stSidebar"], [data-testid="stSidebar"] > div { background: #151719 !important; }
[data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] div { color: #f4f5f6 !important; }
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p, [data-testid="stSidebar"] [role="radiogroup"] label { color: #f4f5f6 !important; opacity: 1 !important; }
.block-container { padding: 2.4rem 3.2rem 3.5rem; max-width: 1500px; }
.metric { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 1.1rem 1.2rem; }
.metric-label { color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; }
.metric-value { font-family: 'Space Grotesk'; font-size: 1.8rem; font-weight: 600; margin-top: .3rem; white-space: nowrap; }
.section { border-bottom: 1px solid var(--line); margin: 2rem 0 1.2rem; padding-bottom: .6rem; }
.badge { display: inline-block; padding: .2rem .55rem; border-radius: 3px; font-size: .78rem; font-weight: 600; background: #e8f1ef; color: var(--accent); }
.auth-kicker { color: var(--accent); font-size: .78rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; }
.st-key-auth-card { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; box-shadow: 0 8px 24px rgba(23, 25, 28, .10); padding: 2rem 2.1rem 1.4rem; }
.st-key-auth-card h1 { font-size: 2.15rem !important; line-height: 1.12 !important; overflow-wrap: normal !important; word-break: normal !important; }
</style>
""", unsafe_allow_html=True)

try:
    api.health()
except Exception:
    st.error(f"API unavailable at {api.BASE_URL}. Start it with `python -m backend`.")
    st.stop()


def render_authentication() -> None:
    _, auth_column, _ = st.columns([0.8, 2.2, 0.8])
    with auth_column:
        with st.container(key="auth-card"):
            st.markdown('<div class="auth-kicker">Robotic Arm Operations</div>', unsafe_allow_html=True)
            st.title("Sign in to your workspace")
            st.caption("Monitor fleet health, telemetry, risk, and maintenance from one operational view.")
            mode = st.radio("Account action", ["Sign in", "Register"], horizontal=True, label_visibility="collapsed")
            with st.form("authentication"):
                if mode == "Register":
                    full_name = st.text_input("Full name")
                email = st.text_input("Email", placeholder="operator@example.com")
                password = st.text_input("Password", type="password")
                if mode == "Register":
                    confirm_password = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button(mode, type="primary", use_container_width=True)
            if mode == "Sign in":
                st.caption("Demo account: operator01@robotic-arm.local / operator123")
            if submitted:
                try:
                    if mode == "Sign in":
                        user = api.login(email, password)
                    else:
                        user = api.register(full_name, email, password, confirm_password)
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = user
                    st.rerun()
                except Exception as error:
                    st.error(str(error))


if not st.session_state.get("authenticated", False):
    render_authentication()
    st.stop()

st.sidebar.markdown("## ROBOTIC ARM")
st.sidebar.caption("Operations intelligence")
user = st.session_state.get("user", {})
st.sidebar.caption(user.get("full_name", "Operator"))
page = st.sidebar.radio("Workspace", ["Overview", "Telemetry input", "Maintenance", "Sensors", "Incidents"], label_visibility="collapsed")
st.sidebar.divider()
if st.sidebar.button("Log out", use_container_width=True):
    st.session_state.clear()
    st.rerun()

if page == "Overview":
    st.title("Operations overview")
    st.caption(f"Live fleet status · {date.today().strftime('%d %b %Y')}")
    robots = api.robots()
    predictions = api.predictions()
    tasks = api.maintenance()
    high_risk = sum(item["risk_level"] == "High" for item in predictions)
    active_tasks = sum(not item["completed"] for item in tasks)
    columns = st.columns(4)
    for column, label, value in zip(columns, ["Fleet units", "High risk", "Open tasks", "API status"], [len(robots), high_risk, active_tasks, "Healthy"]):
        column.markdown(f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>', unsafe_allow_html=True)

    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.subheader("Risk distribution")
        risk_counts = pd.Series([item["risk_level"] for item in predictions]).value_counts().reindex(["Low", "Medium", "High"], fill_value=0)
        st.bar_chart(risk_counts, height=230, color="#1f6f68")
    with chart_right:
        st.subheader("Fleet status")
        status_counts = pd.Series([item["status"] for item in robots]).value_counts()
        st.bar_chart(status_counts, height=230, color="#687078")

    st.markdown('<div class="section"><h3>Risk register</h3></div>', unsafe_allow_html=True)
    if predictions:
        frame = pd.DataFrame(predictions)
        frame["risk_score"] = (frame["risk_score"] * 100).round(1).astype(str) + "%"
        st.dataframe(frame[["robot_name", "location", "risk_level", "risk_score", "recommendation"]], use_container_width=True, hide_index=True)
    else:
        st.info("No telemetry has been recorded yet. Use Telemetry input to add a reading.")

    telemetry = api.latest_telemetry()
    if telemetry:
        st.markdown('<div class="section"><h3>Latest telemetry signals</h3></div>', unsafe_allow_html=True)
        telemetry_frame = pd.DataFrame(telemetry).set_index("name")[["temperature", "vibration", "motor_current"]]
        st.line_chart(telemetry_frame, height=280, color=["#a83b3b", "#1f6f68", "#687078"])

    st.markdown('<div class="section"><h3>Fleet</h3></div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(robots)[["name", "model", "location", "status", "installed_on"]], use_container_width=True, hide_index=True)

elif page == "Telemetry input":
    st.title("Record telemetry")
    st.caption("Submit a sensor reading to run a new risk assessment.")
    robot_options = {f'{robot["name"]} · {robot["location"]}': robot["id"] for robot in api.robots()}
    with st.form("telemetry"):
        selected = st.selectbox("Robot", list(robot_options))
        first, second = st.columns(2)
        temperature = first.number_input("Temperature (°C)", min_value=0.0, max_value=150.0, value=48.0, step=0.5)
        vibration = second.number_input("Vibration (mm/s)", min_value=0.0, max_value=20.0, value=1.8, step=0.1)
        motor_current = first.number_input("Motor current (A)", min_value=0.0, max_value=50.0, value=5.2, step=0.1)
        cycle_count = second.number_input("Cycle count", min_value=0, value=42000, step=1000)
        submitted = st.form_submit_button("Run assessment", type="primary")
    if submitted:
        result = api.submit_telemetry({"robot_id": robot_options[selected], "temperature": temperature, "vibration": vibration, "motor_current": motor_current, "cycle_count": cycle_count})
        st.success(f"Assessment completed: {result['risk_level']} risk at {result['risk_score']:.0%}.")
        st.write(result["recommendation"])
    st.markdown('<div class="section"><h3>Six-axis telemetry</h3></div>', unsafe_allow_html=True)
    telemetry_rows = api.latest_telemetry()
    if telemetry_rows:
        axis_columns = [f"axis_{axis}" for axis in range(1, 7)]
        axis_frame = pd.DataFrame(telemetry_rows).set_index("name")[axis_columns]
        axis_frame.columns = [f"Axis {axis}" for axis in range(1, 7)]
        st.line_chart(axis_frame, height=360, color=["#1f6f68", "#2c7c95", "#687078", "#a05a17", "#a83b3b", "#5b4b8a"])
        st.caption("Latest joint position or load values by robot. Each line represents one arm axis.")

elif page == "Maintenance":
    st.title("Maintenance queue")
    st.caption("Prioritize work before it affects production.")
    tasks = api.maintenance()
    if tasks:
        st.dataframe(pd.DataFrame(tasks)[["robot_name", "title", "priority", "due_date", "completed"]], use_container_width=True, hide_index=True)
        st.subheader("Priority breakdown")
        priority_counts = pd.Series([task["priority"] for task in tasks]).value_counts().reindex(["Low", "Medium", "High"], fill_value=0)
        st.bar_chart(priority_counts, height=220, color="#a05a17")
    st.markdown('<div class="section"><h3>Add work order</h3></div>', unsafe_allow_html=True)
    robot_options = {robot["name"]: robot["id"] for robot in api.robots()}
    with st.form("maintenance"):
        selected = st.selectbox("Robot", list(robot_options))
        title = st.text_input("Task")
        priority = st.selectbox("Priority", ["Low", "Medium", "High"])
        due_date = st.date_input("Due date", min_value=date.today())
        submitted = st.form_submit_button("Create work order", type="primary")
    if submitted and title.strip():
        api.create_maintenance({"robot_id": robot_options[selected], "title": title, "priority": priority, "due_date": due_date.isoformat()})
        st.success("Work order created.")
        st.rerun()

elif page == "Sensors":
    st.title("Sensor network")
    st.caption("Connected instrumentation across the robot fleet.")
    sensor_rows = api.sensors()
    st.dataframe(pd.DataFrame(sensor_rows)[["robot_name", "name", "sensor_type", "last_value", "unit", "status"]], use_container_width=True, hide_index=True)
    sensor_frame = pd.DataFrame(sensor_rows)
    sensor_chart = sensor_frame.groupby("sensor_type")["last_value"].mean().sort_values(ascending=False)
    st.subheader("Average reading by sensor type")
    st.bar_chart(sensor_chart, height=260, color="#1f6f68")

elif page == "Incidents":
    st.title("Incidents and alerts")
    st.caption("Review active events and operational notifications.")
    incidents = api.incidents()
    notifications = api.notifications()
    left, right = st.columns(2)
    with left:
        st.subheader("Incidents")
        st.dataframe(pd.DataFrame(incidents)[["robot_name", "title", "severity", "status", "description"]], use_container_width=True, hide_index=True)
    with right:
        st.subheader("Notifications")
        st.dataframe(pd.DataFrame(notifications)[["robot_name", "title", "severity", "read"]], use_container_width=True, hide_index=True)

