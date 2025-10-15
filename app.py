# app.py
"""
Business Sense IT — Bot Dashboard (Production-style POC)
Single-file Streamlit app:
- Multi-bot with roles & tasks
- Scheduling and background worker
- Simulated multi-search (Google/Bing/DuckDuckGo/Yahoo)
- Save internet data to files
- Advertising/image task simulation (save placeholders)
- Browser & app launcher (simulated / safe)
- Attractive responsive UI (light/dark card style)
- Local SQLite storage under ~/.biz_sense_bot/
Password default: admin123
"""

import streamlit as st
import sqlite3, json, os, time, threading, queue, subprocess, sys, zipfile, re
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import contextlib

# -----------------------------
# Configuration (change as needed)
# -----------------------------
APP_NAME = "Business Sense IT — Bot Dashboard"
DEFAULT_PASSWORD = "admin123"
BASE_DIR = Path.home() / ".biz_sense_bot"
BASE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = BASE_DIR / "bot_state.db"
INTERNET_DIR = BASE_DIR / "internet_information"
ADS_DIR = BASE_DIR / "advertising_pictures"
INTERNET_DIR.mkdir(parents=True, exist_ok=True)
ADS_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = BASE_DIR / "activity.log"
ZIP_SNAPSHOT = BASE_DIR / "snapshot.zip"

# -----------------------------
# UI Styling
# -----------------------------
st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    /* page background */
    .stApp { background: linear-gradient(180deg,#0f1724 0%, #0b1220 100%); color: #e6eef8;}
    .block-container { padding: 1rem 2rem; }
    .card { background: rgba(255,255,255,0.04); padding: 1rem; border-radius: 10px; margin-bottom: 12px; }
    .muted { color: #afc3d9; font-size: 0.95rem; }
    .small { font-size: 0.85rem; color: #9fb2cf; }
    .title { color: #fff; font-weight:700; }
    .success-badge { background: #10b981; color: #021; padding: 4px 8px; border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Database Connection Management
# -----------------------------
def get_db_connection():
    """Get a new database connection for each operation"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    with get_db_connection() as conn:
        c = conn.cursor()
        # Create tables if not exist
        c.execute(
            """CREATE TABLE IF NOT EXISTS bots (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                description TEXT,
                roles_json TEXT,
                created_at TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                description TEXT,
                created_at TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                bot_id INTEGER,
                role_name TEXT,
                command TEXT,
                status TEXT,
                scheduled_at TEXT,
                result TEXT,
                duration INTEGER,
                created_at TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS internet_data (
                id INTEGER PRIMARY KEY,
                bot_id INTEGER,
                query TEXT,
                source TEXT,
                content TEXT,
                saved_at TEXT
            )"""
        )
        conn.commit()

# Initialize database on startup
init_db()

# -----------------------------
# Utility helpers
# -----------------------------
def log(msg: str):
    ts = datetime.utcnow().isoformat()
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{ts} - {msg}\n")

def save_snapshot():
    with zipfile.ZipFile(ZIP_SNAPSHOT, "w") as z:
        for p in [DB_PATH, LOG_PATH]:
            if p.exists():
                z.write(p, arcname=p.name)
    log("Snapshot exported")
    return ZIP_SNAPSHOT

def fetch_bots():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT id, name, description, roles_json FROM bots ORDER BY id").fetchall()
        bots = []
        for r in rows:
            roles = json.loads(r[3]) if r[3] else []
            bots.append({"id": r[0], "name": r[1], "description": r[2], "roles": roles})
        return bots

def fetch_roles():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT id, name, description FROM roles ORDER BY id").fetchall()
        return [{"id": r[0], "name": r[1], "description": r[2]} for r in rows]

def add_role(name, desc=""):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO roles (name, description, created_at) VALUES (?,?,?)", 
                          (name, desc, datetime.utcnow().isoformat()))
            conn.commit()
            log(f"Role created: {name}")
            return True, "Success"
    except sqlite3.IntegrityError:
        return False, f"Role '{name}' already exists"
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            time.sleep(0.1)  # Small delay and retry once
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO roles (name, description, created_at) VALUES (?,?,?)", 
                                  (name, desc, datetime.utcnow().isoformat()))
                    conn.commit()
                    log(f"Role created: {name}")
                    return True, "Success"
            except Exception as retry_e:
                log(f"Role create error (retry): {retry_e}")
                return False, f"Database error: {str(retry_e)}"
        else:
            log(f"Role create error: {e}")
            return False, f"Database error: {str(e)}"
    except Exception as e:
        log(f"Role create error: {e}")
        return False, f"Database error: {str(e)}"

def add_bot(name, desc, roles_list):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Check if bot name already exists (case-insensitive check)
            existing = cursor.execute("SELECT name FROM bots WHERE LOWER(name) = LOWER(?)", (name,)).fetchone()
            if existing:
                return False, f"Bot name '{name}' already exists"
            
            cursor.execute("INSERT INTO bots (name, description, roles_json, created_at) VALUES (?,?,?,?)", 
                          (name.strip(), desc, json.dumps(roles_list), datetime.utcnow().isoformat()))
            conn.commit()
            log(f"Bot created: {name}")
            return True, "Success"
    except sqlite3.IntegrityError:
        return False, f"Bot name '{name}' already exists"
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            time.sleep(0.1)  # Small delay and retry once
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    existing = cursor.execute("SELECT name FROM bots WHERE LOWER(name) = LOWER(?)", (name,)).fetchone()
                    if existing:
                        return False, f"Bot name '{name}' already exists"
                    cursor.execute("INSERT INTO bots (name, description, roles_json, created_at) VALUES (?,?,?,?)", 
                                  (name.strip(), desc, json.dumps(roles_list), datetime.utcnow().isoformat()))
                    conn.commit()
                    log(f"Bot created: {name}")
                    return True, "Success"
            except Exception as retry_e:
                log(f"Bot create error (retry): {retry_e}")
                return False, f"Database error: {str(retry_e)}"
        else:
            log(f"Bot create error: {e}")
            return False, f"Database error: {str(e)}"
    except Exception as e:
        log(f"Bot create error: {e}")
        return False, f"Database error: {str(e)}"

def update_bot_roles(bot_id, roles_list):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE bots SET roles_json = ? WHERE id = ?", (json.dumps(roles_list), bot_id))
        conn.commit()

def add_task(bot_id, role_name, command, scheduled_at=None, duration=5):
    sch = scheduled_at.isoformat() if scheduled_at else None
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (bot_id, role_name, command, status, scheduled_at, result, duration, created_at) VALUES (?,?,?,?,?,?,?,?)",
                       (bot_id, role_name, command, "scheduled" if sch else "queued", sch or None, "", duration, datetime.utcnow().isoformat()))
        conn.commit()
        task_id = cursor.lastrowid
        log(f"Task created {task_id} for bot {bot_id} role {role_name}")
        return task_id

def set_task_status(task_id, status, result=""):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET status = ?, result = ? WHERE id = ?", (status, result, task_id))
        conn.commit()

def save_internet_record(bot_id, query, source, content):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO internet_data (bot_id, query, source, content, saved_at) VALUES (?,?,?,?,?)",
                       (bot_id, query, source, content, datetime.utcnow().isoformat()))
        conn.commit()

# -----------------------------
# Task execution (background)
# -----------------------------
TASK_Q = queue.Queue()
STOP_FLAG = threading.Event()

def simulated_search(query):
    """Create simulated results across engines"""
    engines = ["Google", "Bing", "DuckDuckGo", "Yahoo"]
    results = []
    for e in engines:
        for i in range(2):
            results.append({
                "engine": e,
                "title": f"{e} result {i+1} for {query}",
                "snippet": f"Simulated snippet about {query} from {e}.",
                "url": f"https://{e.lower()}.example/search?q={quote_plus(query)}"
            })
    return results

def worker_loop(q: queue.Queue, stop_flag: threading.Event):
    while not stop_flag.is_set():
        try:
            job = q.get(timeout=1)
        except queue.Empty:
            continue
        task_id = job.get("task_id")
        bot_id = job.get("bot_id")
        role = job.get("role")
        cmd = job.get("command")
        duration = int(job.get("duration", 5))
        log(f"Worker started task {task_id} for bot {bot_id} role {role}: {cmd}")
        # Interpret command
        try:
            if cmd.lower().startswith("search"):
                # e.g. "Search Pak vs SA match"
                query = cmd.split(" ", 1)[1] if " " in cmd else cmd
                results = simulated_search(query)
                # save results to file and DB
                filename = INTERNET_DIR / f"search_{bot_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"Search: {query}\nTime: {datetime.utcnow().isoformat()}\n\n")
                    for r in results:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
                        save_internet_record(bot_id, query, r["engine"], r["snippet"])
                outcome = f"Saved {len(results)} search results to {filename.name}"
                set_task_status(task_id, "completed", outcome)
            elif "advert" in cmd.lower() or "image" in cmd.lower():
                # simulate advert/image creation - create text placeholders
                # parse number if present
                m = re.search(r"(\d+)\s*(?:images|pictures|adverts?)", cmd.lower())
                n = int(m.group(1)) if m else 1
                created = []
                for i in range(n):
                    fn = ADS_DIR / f"ad_{bot_id}_{int(time.time())}_{i+1}.txt"
                    with open(fn, "w", encoding="utf-8") as f:
                        f.write(f"Advert created by bot {bot_id}\nCommand: {cmd}\nTime:{datetime.utcnow().isoformat()}\n")
                    created.append(fn.name)
                outcome = f"Created {len(created)} adverts: {', '.join(created)}"
                set_task_status(task_id, "completed", outcome)
            elif any(br in cmd.lower() for br in ["chrome","firefox","edge","brave","browser"]):
                # open browser simulation (attempt to open actual browser command if available)
                browser_cmd = None
                if sys.platform.startswith("win"):
                    browser_cmd = "start"
                else:
                    browser_cmd = "xdg-open"
                url = None
                m = re.search(r"https?://[^\s]+", cmd)
                if m:
                    url = m.group(0)
                elif "search for" in cmd.lower():
                    q = cmd.lower().split("search for",1)[1].strip()
                    url = f"https://www.google.com/search?q={quote_plus(q)}"
                if url:
                    try:
                        subprocess.Popen([browser_cmd, url], shell=False)
                        outcome = f"Opened browser to {url}"
                    except Exception as e:
                        outcome = f"Browser open simulated. ({e})"
                else:
                    outcome = "Opened default browser (simulated)"
                set_task_status(task_id, "completed", outcome)
            elif any(app in cmd.lower() for app in ["open app", "launch app", "open photoroom", "photoroom"]):
                # simulate app action & log it
                outcome = "App action simulated. Manual login required on device before granting access."
                set_task_status(task_id, "completed", outcome)
            else:
                # default simulated work
                for s in range(duration):
                    if STOP_FLAG.is_set():
                        set_task_status(task_id, "interrupted", "Worker stopped")
                        break
                    time.sleep(1)
                else:
                    set_task_status(task_id, "completed", f"Executed: {cmd}")
        except Exception as e:
            set_task_status(task_id, "error", str(e))
        log(f"Worker finished task {task_id}")
        q.task_done()

# start worker thread
_worker_thread = threading.Thread(target=worker_loop, args=(TASK_Q, STOP_FLAG), daemon=True)
_worker_thread.start()

# -----------------------------
# UI: Authentication
# -----------------------------
with st.sidebar:
    st.markdown("## 🔐 Access")
    if "authorized" not in st.session_state:
        st.session_state.authorized = False
    pwd = st.text_input("Enter password", type="password")
    if st.button("Login"):
        if pwd == DEFAULT_PASSWORD:
            st.session_state.authorized = True
            st.success("Authorized ✅")
            log("User logged in")
        else:
            st.session_state.authorized = False
            st.error("Incorrect password")
    if st.session_state.authorized:
        if st.button("Logout"):
            st.session_state.authorized = False
            st.rerun()
    st.markdown("---")
    st.markdown("### Snapshot & Logs")
    if st.button("Export Snapshot"):
        snap = save_snapshot()
        st.success(f"Snapshot created: {snap.name}")
    if st.button("View recent logs"):
        if LOG_PATH.exists():
            st.code("\n".join(open(LOG_PATH, encoding="utf-8").read().splitlines()[-20:]))
        else:
            st.info("No logs yet")
    st.markdown("---")
    st.markdown("### Settings")
    # search provider selection (simulated primarily)
    provider = st.selectbox("Search provider", ["simulated", "serpapi", "bing"], index=0)
    st.markdown("Allowed sites (for saving/filtering):")
    site_input = st.text_input("Add allowed site (example.com)")
    if st.button("Add allowed site"):
        if site_input:
            st.session_state.setdefault("allowed_sites", []).append(site_input)
            st.success(f"Added {site_input}")
            log(f"Allowed site added: {site_input}")
    if st.session_state.get("allowed_sites"):
        st.write(st.session_state["allowed_sites"])
        if st.button("Clear allowed sites"):
            st.session_state["allowed_sites"] = []
            st.info("Cleared allowed list")

if not st.session_state.authorized:
    st.title(APP_NAME)
    st.markdown("🔒 Please login from the sidebar to access the dashboard.")
    st.stop()

# -----------------------------
# Main app header
# -----------------------------
st.markdown(f"<div class='card'><h1 class='title'>{APP_NAME}</h1><div class='muted'>Multi-bot platform — create bots, roles and tasks. Works on desktop & mobile (via Streamlit Cloud).</div></div>", unsafe_allow_html=True)

# -----------------------------
# Top-level navigation
# -----------------------------
nav = st.tabs(["Home", "Bots & Roles", "Tasks & Schedule", "Reports", "Quick Actions", "Admin"])

# --- Home ---
with nav[0]:
    st.header("Welcome")
    st.markdown("Use the left sidebar for snapshots and settings. Create bots and roles in **Bots & Roles**. Assign tasks in **Tasks & Schedule**.")
    # key stats
    bots = fetch_bots()
    roles_list = fetch_roles()
    total_bots = len(bots)
    total_roles = len(roles_list)
    total_tasks = 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        total_tasks = cursor.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Bots", total_bots)
    col2.metric("Roles", total_roles)
    col3.metric("Total Tasks", total_tasks)
    st.markdown("---")
    st.subheader("Recent activity")
    if LOG_PATH.exists():
        lines = open(LOG_PATH, encoding="utf-8").read().splitlines()[-8:]
        st.text("\n".join(lines))
    else:
        st.info("No activity yet")

# --- Bots & Roles ---
with nav[1]:
    st.header("Bots & Roles")
    st.markdown("Create and manage bots and roles. Roles are saved globally and can be assigned to each bot.")

    # left create role / bot
    c1, c2 = st.columns([1, 2])

    with c1:
        st.subheader("Create Role")
        rname = st.text_input("Role name")
        rdesc = st.text_area("Role description")
        if st.button("Create Role"):
            if rname:
                success, message = add_role(rname, rdesc)
                if success:
                    st.success(f"Role '{rname}' created")
                    st.rerun()
                else:
                    st.error(f"Role creation failed: {message}")
            else:
                st.error("Please enter a role name")
        st.markdown("---")
        st.subheader("Create Bot")
        bname = st.text_input("Bot name (unique)")
        bdesc = st.text_area("Bot description")
        available_roles = [r['name'] for r in fetch_roles()]
        broles = st.multiselect("Assign roles (optional)", options=available_roles)
        if st.button("Create Bot"):
            if bname:
                success, message = add_bot(bname, bdesc, broles)
                if success:
                    st.success(f"Bot '{bname}' added")
                    st.rerun()
                else:
                    st.error(f"Bot create error: {message}")
            else:
                st.error("Please enter a bot name")

    with c2:
        st.subheader("Existing Bots")
        bots = fetch_bots()
        if bots:
            for bot in bots:
                st.markdown(f"**{bot['name']}** — {bot['description']}")
                st.write(f"Roles: {', '.join(bot['roles']) if bot['roles'] else 'None'}")
                colx1, colx2 = st.columns([1,1])
                if colx1.button("Edit", key=f"edit_{bot['id']}"):
                    # show modal-like editing area
                    new_name = st.text_input("New name", value=bot['name'], key=f"nn_{bot['id']}")
                    new_desc = st.text_area("New desc", value=bot['description'], key=f"nd_{bot['id']}")
                    chosen = st.multiselect("Roles", options=[r['name'] for r in fetch_roles()], default=bot['roles'], key=f"cr_{bot['id']}")
                    if st.button("Save", key=f"save_{bot['id']}"):
                        update_bot_roles(bot['id'], chosen)
                        st.success("Bot updated")
                        st.rerun()
                if colx2.button("Delete", key=f"del_{bot['id']}"):
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM bots WHERE id = ?", (bot['id'],))
                        conn.commit()
                    st.warning("Bot deleted")
                    st.rerun()
        else:
            st.info("No bots yet. Create one on the left.")

# --- Tasks & Schedule ---
with nav[2]:
    st.header("Tasks & Schedule")
    st.markdown("Assign a task command to a bot + role. You can schedule for later or run now.")

    bots = fetch_bots()
    bot_names = [b['name'] for b in bots]
    if not bot_names:
        st.info("Create a bot first in Bots & Roles")
    else:
        sel_bot = st.selectbox("Select Bot", bot_names)
        bot_row = next((b for b in bots if b['name'] == sel_bot), None)
        roles_for_bot = bot_row['roles'] if bot_row else []
        sel_role = st.selectbox("Select Role (role must be assigned to bot)", roles_for_bot or ["No roles assigned"])
        cmd = st.text_area("Task Command", placeholder="e.g. Search Pak vs SA match and summarize")
        dur = st.selectbox("Simulated duration (sec)", [5,10,20,60], index=0)
        schedule = st.selectbox("Schedule", ["Run now", "4 hours", "12 hours", "24 hours"])
        if st.button("Submit Task"):
            # insert task
            with get_db_connection() as conn:
                cursor = conn.cursor()
                bot_id = cursor.execute("SELECT id FROM bots WHERE name = ?", (sel_bot,)).fetchone()[0]
                scheduled_at = None
                if schedule == "4 hours":
                    scheduled_at = datetime.utcnow() + timedelta(hours=4)
                elif schedule == "12 hours":
                    scheduled_at = datetime.utcnow() + timedelta(hours=12)
                elif schedule == "24 hours":
                    scheduled_at = datetime.utcnow() + timedelta(hours=24)
                task_id = add_task(bot_id, sel_role, cmd, scheduled_at=scheduled_at, duration=dur)
                # if run now, enqueue
                if not scheduled_at or scheduled_at <= datetime.utcnow():
                    TASK_Q.put({"task_id": task_id, "bot_id": bot_id, "role": sel_role, "command": cmd, "duration": dur})
                    set_task_status(task_id, "running", "")
                    st.success("Task queued and running")
                else:
                    st.info("Task scheduled")
                    st.success(f"Task scheduled at {scheduled_at.isoformat()}")

# --- Reports ---
with nav[3]:
    st.header("Reports & Data")
    st.markdown("View completed tasks and saved internet data files.")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        completed = cursor.execute("SELECT id, bot_id, role_name, command, result, created_at FROM tasks WHERE status = 'completed' ORDER BY id DESC LIMIT 30").fetchall()
        if completed:
            for r in completed:
                bot_name = cursor.execute("SELECT name FROM bots WHERE id = ?", (r[1],)).fetchone()
                bname = bot_name[0] if bot_name else "Unknown"
                with st.expander(f"Task {r[0]} — {bname} — {r[2]}"):
                    st.write("Command:", r[3])
                    st.write("Result:", r[4])
                    st.write("Created:", r[5])
        else:
            st.info("No completed tasks yet.")
    
    st.markdown("---")
    st.subheader("Saved Internet Files")
    files = sorted(INTERNET_DIR.glob("*.txt"), reverse=True)
    if files:
        for f in files[:10]:
            st.write(f.name)
            if st.button("Open", key=f"open_{f.name}"):
                st.code(open(f, encoding="utf-8").read()[:1000])
    else:
        st.info("No internet files saved yet.")

# --- Quick Actions ---
with nav[4]:
    st.header("Quick Actions & Launchers")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Open Browser (simulated)")
        br = st.selectbox("Browser", ["Google Chrome", "Mozilla Firefox", "Microsoft Edge", "Brave"])
        url = st.text_input("URL (optional)")
        if st.button("Open Browser"):
            st.info(f"Attempting to open {br} — simulated on server.")
            log(f"Open browser {br} to {url}")
    with c2:
        st.subheader("Open App (simulated)")
        app = st.selectbox("App", ["PhotoRoom", "Calculator", "Text Editor"])
        if st.button("Open App"):
            st.info(f"Open app {app} on device — manual login required before granting bot access.")
            log(f"Simulated open app {app}")

# --- Admin ---
with nav[5]:
    st.header("Admin")
    if st.button("Run due scheduled tasks now"):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute("SELECT id, bot_id, command FROM tasks WHERE status = 'scheduled' AND scheduled_at <= ?", (datetime.utcnow().isoformat(),)).fetchall()
            count = 0
            for r in rows:
                TASK_Q.put({"task_id": r[0], "bot_id": r[1], "role": None, "command": r[2], "duration": 5})
                set_task_status(r[0], "running", "")
                count += 1
            st.success(f"Queued {count} due tasks")
    if st.button("Clear all internet data"):
        for f in INTERNET_DIR.glob("*"):
            try:
                f.unlink()
            except Exception:
                pass
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM internet_data")
            conn.commit()
        st.success("Cleared internet data")
    if st.button("Delete all tasks"):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks")
            conn.commit()
        st.success("All tasks removed")

st.markdown("---")
st.caption("For real device automation (open browser, login, modify apps) integrate platform-specific connectors (Selenium, Playwright, ADB). This app is a secure, deployable POC for client demonstration.")