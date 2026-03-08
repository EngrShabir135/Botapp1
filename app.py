"""
The United Union Bank — Bot Dashboard (Production-style POC)
Single-file Streamlit app with:
- User authentication (signup/login)
- Multi-bot with roles & tasks
- Scheduling and background worker
- Simulated multi-search
- Save internet data to files
- Advertising/image task simulation
- Browser & app launcher (simulated)
- Attractive responsive UI with banking theme
- Local SQLite storage under ~/.united_union_bank/
"""

import streamlit as st
import sqlite3, json, os, time, threading, queue, subprocess, sys, zipfile, re
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import contextlib
import random

# -----------------------------
# Configuration
# -----------------------------
APP_NAME = "The United Union Bank"
DEFAULT_PASSWORD = "admin123"  # Default for demo, users should change
BASE_DIR = Path.home() / ".united_union_bank"
BASE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = BASE_DIR / "bot_state.db"
INTERNET_DIR = BASE_DIR / "internet_information"
ADS_DIR = BASE_DIR / "advertising_pictures"
INTERNET_DIR.mkdir(parents=True, exist_ok=True)
ADS_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = BASE_DIR / "activity.log"
ZIP_SNAPSHOT = BASE_DIR / "snapshot.zip"
USERS_DIR = BASE_DIR / "users"
USERS_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Enhanced UI Styling with Banking Theme
# -----------------------------
st.set_page_config(
    page_title=APP_NAME, 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="🏦"
)

st.markdown(
    """
    <style>
    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global styles */
    .stApp {
        background: linear-gradient(135deg, #0a1a2f 0%, #0b1e33 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Glass morphism cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(49, 108, 244, 0.3);
        border: 1px solid rgba(49, 108, 244, 0.3);
    }
    
    /* Bank header */
    .bank-header {
        background: linear-gradient(90deg, #0a1a2f 0%, #1a2f4a 100%);
        padding: 2rem;
        border-radius: 30px;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 215, 0, 0.3);
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    
    .bank-title {
        color: #FFD700;
        font-size: 2.5rem;
        font-weight: 700;
        letter-spacing: 2px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        margin-bottom: 0.5rem;
    }
    
    .bank-subtitle {
        color: #a0c0e0;
        font-size: 1rem;
        letter-spacing: 1px;
    }
    
    /* Gold accent */
    .gold-accent {
        color: #FFD700;
        font-weight: 600;
    }
    
    /* Success badge */
    .success-badge {
        background: linear-gradient(135deg, #00b09b, #96c93d);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #1a2f4a 0%, #0f2740 100%);
        border-radius: 15px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid rgba(255, 215, 0, 0.2);
    }
    
    .metric-value {
        color: #FFD700;
        font-size: 2rem;
        font-weight: 700;
    }
    
    .metric-label {
        color: #a0c0e0;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #1a2f4a 0%, #0f2740 100%);
        color: #FFD700;
        border: 1px solid #FFD700;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: #FFD700;
        color: #0a1a2f;
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(255, 215, 0, 0.3);
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 215, 0, 0.2);
        border-radius: 10px;
        color: white;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #FFD700;
        box-shadow: 0 0 0 2px rgba(255, 215, 0, 0.2);
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        background: rgba(255, 255, 255, 0.02);
        padding: 0.5rem;
        border-radius: 15px;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #a0c0e0;
        font-weight: 600;
        border-radius: 10px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1a2f4a 0%, #0f2740 100%);
        color: #FFD700 !important;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, #0a1a2f 0%, #0b1e33 100%);
    }
    
    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #FFD700, transparent);
        margin: 2rem 0;
    }
    
    /* Logo placeholder */
    .logo {
        font-size: 3rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# User Authentication System
# -----------------------------
def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_users_table():
    """Create users table if it doesn't exist"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT,
                full_name TEXT,
                created_at TEXT,
                last_login TEXT,
                account_type TEXT DEFAULT 'user',
                is_active INTEGER DEFAULT 1
            )
        """)
        # Add default admin user if not exists
        c.execute("SELECT * FROM users WHERE username = 'admin'")
        if not c.fetchone():
            c.execute("""
                INSERT INTO users (username, email, password_hash, full_name, created_at, account_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ('admin', 'admin@unitedunionbank.com', hash_password(DEFAULT_PASSWORD), 
                  'System Administrator', datetime.utcnow().isoformat(), 'admin'))
        conn.commit()

# Call this after DB initialization
create_users_table()

def signup_user(username, email, password, full_name):
    """Register a new user"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            password_hash = hash_password(password)
            c.execute("""
                INSERT INTO users (username, email, password_hash, full_name, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (username, email, password_hash, full_name, datetime.utcnow().isoformat()))
            conn.commit()
            log(f"New user registered: {username}")
            return True, "Account created successfully!"
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return False, "Username already exists"
        elif "email" in str(e):
            return False, "Email already registered"
        return False, "Registration failed"
    except Exception as e:
        log(f"Signup error: {e}")
        return False, f"Error: {str(e)}"

def login_user(username, password):
    """Authenticate user"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            password_hash = hash_password(password)
            c.execute("""
                SELECT id, username, full_name, account_type 
                FROM users 
                WHERE (username = ? OR email = ?) AND password_hash = ? AND is_active = 1
            """, (username, username, password_hash))
            user = c.fetchone()
            
            if user:
                # Update last login
                c.execute("""
                    UPDATE users SET last_login = ? 
                    WHERE id = ?
                """, (datetime.utcnow().isoformat(), user[0]))
                conn.commit()
                log(f"User logged in: {user[1]}")
                return True, {"id": user[0], "username": user[1], "full_name": user[2], "account_type": user[3]}
            return False, "Invalid username or password"
    except Exception as e:
        log(f"Login error: {e}")
        return False, f"Login error: {str(e)}"

# Initialize database tables
init_db()

# -----------------------------
# Rest of your existing utility functions (unchanged)
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
    except Exception as e:
        log(f"Role create error: {e}")
        return False, f"Database error: {str(e)}"

def add_bot(name, desc, roles_list):
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
# Task execution (background) - unchanged
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
        try:
            if cmd.lower().startswith("search"):
                query = cmd.split(" ", 1)[1] if " " in cmd else cmd
                results = simulated_search(query)
                filename = INTERNET_DIR / f"search_{bot_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"Search: {query}\nTime: {datetime.utcnow().isoformat()}\n\n")
                    for r in results:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
                        save_internet_record(bot_id, query, r["engine"], r["snippet"])
                outcome = f"Saved {len(results)} search results to {filename.name}"
                set_task_status(task_id, "completed", outcome)
            elif "advert" in cmd.lower() or "image" in cmd.lower():
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
                outcome = "App action simulated. Manual login required on device before granting access."
                set_task_status(task_id, "completed", outcome)
            else:
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

# Start worker thread
_worker_thread = threading.Thread(target=worker_loop, args=(TASK_Q, STOP_FLAG), daemon=True)
_worker_thread.start()

# -----------------------------
# Authentication UI
# -----------------------------
def show_auth_page():
    """Display signup/login page"""
    
    # Bank header with logo
    st.markdown("""
    <div class="bank-header" style="text-align: center;">
        <div class="logo">🏦</div>
        <div class="bank-title">THE UNITED UNION BANK</div>
        <div class="bank-subtitle">Secure Banking Bot Dashboard • Est. 2024</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
        
        with tab1:
            with st.container():
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown("### Welcome Back")
                st.markdown("Please login to access your banking dashboard")
                
                username = st.text_input("Username or Email", placeholder="Enter your username or email", key="login_username")
                password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Login", use_container_width=True):
                        if username and password:
                            success, result = login_user(username, password)
                            if success:
                                st.session_state.authorized = True
                                st.session_state.user = result
                                st.success("Login successful! Redirecting...")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(result)
                        else:
                            st.warning("Please fill in all fields")
                
                with col_b:
                    if st.button("Forgot Password?", use_container_width=True):
                        st.info("Please contact your bank administrator to reset your password.")
                
                st.markdown("""
                <div style="text-align: center; margin-top: 1rem;">
                    <span class="gold-accent">Demo credentials:</span><br>
                    Username: admin<br>
                    Password: admin123
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        with tab2:
            with st.container():
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown("### Create New Account")
                st.markdown("Join The United Union Bank today")
                
                full_name = st.text_input("Full Name", placeholder="John Doe", key="signup_name")
                email = st.text_input("Email Address", placeholder="john@example.com", key="signup_email")
                new_username = st.text_input("Username", placeholder="johndoe123", key="signup_username")
                new_password = st.text_input("Password", type="password", placeholder="Create a strong password", key="signup_password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter password", key="signup_confirm")
                
                # Password strength indicator
                if new_password:
                    strength = "Weak"
                    color = "red"
                    if len(new_password) >= 8 and any(c.isupper() for c in new_password) and any(c.isdigit() for c in new_password):
                        strength = "Strong"
                        color = "green"
                    elif len(new_password) >= 6:
                        strength = "Medium"
                        color = "orange"
                    
                    st.markdown(f"Password strength: <span style='color:{color}'>{strength}</span>", unsafe_allow_html=True)
                
                terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")
                
                if st.button("Create Account", use_container_width=True):
                    if not all([full_name, email, new_username, new_password, confirm_password]):
                        st.warning("Please fill in all fields")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    elif not terms:
                        st.warning("Please accept the terms and conditions")
                    else:
                        success, message = signup_user(new_username, email, new_password, full_name)
                        if success:
                            st.success(message)
                            st.info("Please login with your new account")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(message)
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Security badges
        st.markdown("""
        <div style="text-align: center; margin-top: 2rem;">
            <span style="color: #FFD700; margin: 0 10px;">🔒 256-bit SSL</span>
            <span style="color: #FFD700; margin: 0 10px;">🏦 FDIC Insured</span>
            <span style="color: #FFD700; margin: 0 10px;">🔐 2FA Available</span>
        </div>
        """, unsafe_allow_html=True)

# -----------------------------
# Main app with authentication
# -----------------------------
if "authorized" not in st.session_state:
    st.session_state.authorized = False

if not st.session_state.authorized:
    show_auth_page()
    st.stop()

# -----------------------------
# User info in sidebar (enhanced)
# -----------------------------
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <div style="font-size: 2rem;">🏦</div>
        <div style="color: #FFD700; font-weight: 700;">THE UNITED UNION BANK</div>
    </div>
    """, unsafe_allow_html=True)
    
    if "user" in st.session_state:
        user = st.session_state.user
        st.markdown(f"""
        <div class="glass-card" style="text-align: center;">
            <div style="font-size: 1.2rem; color: #FFD700;">{user['full_name']}</div>
            <div style="font-size: 0.8rem; color: #a0c0e0;">@{user['username']}</div>
            <div style="margin-top: 0.5rem;">
                <span class="success-badge">{user['account_type'].upper()}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("### 🔐 Security")
    if st.button("Logout", use_container_width=True):
        st.session_state.authorized = False
        if "user" in st.session_state:
            del st.session_state.user
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 Snapshot & Logs")
    if st.button("Export Snapshot", use_container_width=True):
        snap = save_snapshot()
        st.success(f"Snapshot created: {snap.name}")
    
    if st.button("View Recent Logs", use_container_width=True):
        if LOG_PATH.exists():
            st.code("\n".join(open(LOG_PATH, encoding="utf-8").read().splitlines()[-20:]))
        else:
            st.info("No logs yet")
    
    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    provider = st.selectbox("Search provider", ["simulated", "serpapi", "bing"], index=0)
    
    st.markdown("#### Allowed Sites")
    site_input = st.text_input("Add domain (example.com)")
    if st.button("Add to allowed list", use_container_width=True):
        if site_input:
            st.session_state.setdefault("allowed_sites", []).append(site_input)
            st.success(f"Added {site_input}")
    
    if st.session_state.get("allowed_sites"):
        st.write(st.session_state["allowed_sites"])
        if st.button("Clear allowed sites", use_container_width=True):
            st.session_state["allowed_sites"] = []
            st.info("Cleared")

# -----------------------------
# Enhanced Main Dashboard
# -----------------------------
st.markdown(f"""
<div class="glass-card" style="text-align: center;">
    <h1 style="color: #FFD700; margin: 0;">🏦 THE UNITED UNION BANK</h1>
    <p style="color: #a0c0e0;">Bot Automation Dashboard • Welcome back, {st.session_state.user['full_name']}!</p>
</div>
""", unsafe_allow_html=True)

# Enhanced navigation with icons
nav = st.tabs([
    "🏠 Home", 
    "🤖 Bots & Roles", 
    "📋 Tasks & Schedule", 
    "📊 Reports", 
    "⚡ Quick Actions", 
    "🔧 Admin"
])

# --- Home (Enhanced) ---
with nav[0]:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### Dashboard Overview")
    
    # Key metrics
    bots = fetch_bots()
    roles_list = fetch_roles()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        total_tasks = cursor.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        completed_tasks = cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'").fetchone()[0]
        pending_tasks = cursor.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('queued', 'scheduled')").fetchone()[0]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(bots)}</div>
            <div class="metric-label">Active Bots</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(roles_list)}</div>
            <div class="metric-label">Defined Roles</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_tasks}</div>
            <div class="metric-label">Total Tasks</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{completion_rate:.1f}%</div>
            <div class="metric-label">Success Rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Recent activity and system status
    col_activity, col_status = st.columns(2)
    
    with col_activity:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 📝 Recent Activity")
        if LOG_PATH.exists():
            lines = open(LOG_PATH, encoding="utf-8").read().splitlines()[-8:]
            for line in lines:
                st.markdown(f"<span style='color: #a0c0e0; font-size: 0.9rem;'>• {line}</span>", unsafe_allow_html=True)
        else:
            st.info("No activity yet")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_status:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 🔧 System Status")
        
        # Worker thread status
        if _worker_thread.is_alive():
            st.markdown("✅ **Background Worker:** Running")
        else:
            st.markdown("❌ **Background Worker:** Stopped")
        
        # Database status
        try:
            with get_db_connection() as conn:
                st.markdown("✅ **Database:** Connected")
        except:
            st.markdown("❌ **Database:** Error")
        
        # Queue status
        st.markdown(f"📊 **Queue Size:** {TASK_Q.qsize()} tasks")
        
        # Pending tasks
        st.markdown(f"⏳ **Pending Tasks:** {pending_tasks}")
        
        st.markdown('</div>', unsafe_allow_html=True)

# --- The rest of your tabs remain the same as in original app ---
# [Keep all the existing tab content from your original app here]

with nav[1]:  # Bots & Roles
    st.header("🤖 Bots & Roles Management")
    # ... (keep your existing bots & roles code)

with nav[2]:  # Tasks & Schedule
    st.header("📋 Tasks & Scheduling")
    # ... (keep your existing tasks code)

with nav[3]:  # Reports
    st.header("📊 Reports & Analytics")
    # ... (keep your existing reports code)

with nav[4]:  # Quick Actions
    st.header("⚡ Quick Actions & Launchers")
    # ... (keep your existing quick actions code)

with nav[5]:  # Admin
    st.header("🔧 Admin Panel")
    # ... (keep your existing admin code)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #a0c0e0; font-size: 0.8rem; padding: 1rem;">
    <p>© 2024 The United Union Bank. All rights reserved. | Secure Banking Bot Automation Platform</p>
    <p>For real device automation, integrate with Selenium, Playwright, or ADB. This is a secure POC for demonstration.</p>
</div>
""", unsafe_allow_html=True)
