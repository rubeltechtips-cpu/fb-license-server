# license_server.py
# ═══════════════════════════════════════════════════════════════
# FB Lite Auto Tool — License Server + Upgraded Admin Panel
# Based on the supplied Pasted text(10).txt
# Start: gunicorn license_server:app
# ═══════════════════════════════════════════════════════════════

from flask import (
    Flask,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    render_template_string
)

import json
import os
import secrets
import string
from datetime import datetime, timedelta
from functools import wraps


# ═══════════════════════════════════════════════════════════════
# APP CONFIG
# ═══════════════════════════════════════════════════════════════

app = Flask(__name__)

app.secret_key = os.environ.get(
    "ADMIN_SECRET_KEY",
    "FB-LITE-ADMIN-SECRET-KEY-CHANGE-THIS-2026"
)

DB_FILE = os.environ.get(
    "LICENSE_DB_FILE",
    "licenses.json"
)

ADMIN_USER = os.environ.get(
    "ADMIN_USER",
    "admin"
)

ADMIN_PASS = os.environ.get(
    "ADMIN_PASS",
    "Rubel2026"
)

# Last heartbeat কত সেকেন্ডের মধ্যে হলে ONLINE দেখাবে
ONLINE_SECONDS = int(
    os.environ.get("ONLINE_SECONDS", "75")
)


# ═══════════════════════════════════════════════════════════════
# TIME HELPERS
# ═══════════════════════════════════════════════════════════════

def now():
    return datetime.now()


def iso_now():
    return now().isoformat(timespec="seconds")


def parse_datetime(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, encoding="utf-8") as f:
                data = json.load(f)

                if isinstance(data, dict):
                    return data

        except Exception:
            return {}

    return {}


def save_db(db):
    temp_file = DB_FILE + ".tmp"

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                db,
                f,
                indent=2,
                ensure_ascii=False
            )

        os.replace(temp_file, DB_FILE)

    except Exception:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# LICENSE HELPERS
# ═══════════════════════════════════════════════════════════════

def is_expired(entry):
    expires = parse_datetime(entry.get("expires"))

    if not expires:
        return False

    return now() > expires


def is_online(entry):
    last_seen = parse_datetime(entry.get("last_seen"))

    if not last_seen:
        return False

    diff = (now() - last_seen).total_seconds()

    return diff <= ONLINE_SECONDS


def license_status(entry):
    if entry.get("banned"):
        return "banned"

    if is_expired(entry):
        return "expired"

    if entry.get("hwid"):
        return "active"

    return "pending"


def generate_license_key():
    alphabet = string.ascii_uppercase + string.digits

    while True:
        parts = [
            "".join(
                secrets.choice(alphabet)
                for _ in range(5)
            )
            for _ in range(4)
        ]

        key = "FBLT-" + "-".join(parts)

        db = load_db()

        if key not in db:
            return key


def short_hwid(hwid):
    if not hwid:
        return ""

    if len(hwid) <= 16:
        return hwid

    return hwid[:8] + "…" + hwid[-6:]


def format_last_seen(value):
    if not value:
        return "Never"

    dt = parse_datetime(value)

    if not dt:
        return str(value)[:19]

    diff = (now() - dt).total_seconds()

    if diff < 60:
        return "Just now"

    if diff < 3600:
        return f"{int(diff / 60)}m ago"

    if diff < 86400:
        return f"{int(diff / 3600)}h ago"

    if diff < 604800:
        return f"{int(diff / 86400)}d ago"

    return dt.strftime("%d %b %Y %H:%M")


def format_expiry(value):
    if not value:
        return "—"

    dt = parse_datetime(value)

    if not dt:
        return str(value)[:19]

    diff = dt - now()
    days = diff.days

    text = dt.strftime("%d %b %Y")

    if diff.total_seconds() >= 0:
        text += f" ({max(days, 0)}d)"

    else:
        text += " (expired)"

    return text


# ═══════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════

def login_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if not session.get("logged_in"):
            return redirect(
                url_for("login_page")
            )

        return func(*args, **kwargs)

    return wrapper


LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>

<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width,initial-scale=1">

<title>License Admin Login</title>

<style>

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;

    font-family:
        Segoe UI,
        Arial,
        sans-serif;

    background:
        radial-gradient(
            circle at top left,
            #312e81,
            transparent 35%
        ),
        linear-gradient(
            135deg,
            #020617,
            #111827,
            #1e1b4b
        );

    color: #e2e8f0;
}

.card {
    width: 100%;
    max-width: 420px;

    padding: 34px;

    background:
        rgba(15, 23, 42, .94);

    border:
        1px solid
        rgba(148, 163, 184, .15);

    border-radius: 22px;

    box-shadow:
        0 30px 80px
        rgba(0,0,0,.55);

    backdrop-filter: blur(16px);
}

.logo {
    width: 74px;
    height: 74px;

    display: flex;
    align-items: center;
    justify-content: center;

    margin: 0 auto 18px;

    border-radius: 22px;

    background:
        linear-gradient(
            135deg,
            #6366f1,
            #8b5cf6
        );

    font-size: 35px;

    box-shadow:
        0 15px 35px
        rgba(99,102,241,.35);
}

h1 {
    text-align: center;
    font-size: 23px;
    margin-bottom: 7px;
}

.sub {
    text-align: center;
    color: #94a3b8;
    font-size: 13px;
    margin-bottom: 28px;
}

label {
    display: block;
    margin-bottom: 7px;

    font-size: 12px;
    font-weight: 700;

    color: #cbd5e1;
}

input {
    width: 100%;

    padding: 14px;

    margin-bottom: 17px;

    background: #020617;

    color: white;

    border:
        1px solid
        #334155;

    border-radius: 12px;

    outline: none;

    font-size: 14px;
}

input:focus {
    border-color: #6366f1;

    box-shadow:
        0 0 0 3px
        rgba(99,102,241,.15);
}

button {
    width: 100%;

    padding: 14px;

    border: 0;

    border-radius: 12px;

    background:
        linear-gradient(
            135deg,
            #6366f1,
            #8b5cf6
        );

    color: white;

    font-weight: 800;

    cursor: pointer;

    font-size: 14px;
}

.error {
    margin-bottom: 16px;

    padding: 11px;

    border-radius: 10px;

    background: #450a0a;

    color: #fca5a5;

    text-align: center;

    font-size: 13px;
}

</style>

</head>

<body>

<div class="card">

    <div class="logo">🔐</div>

    <h1>License Admin Panel</h1>

    <div class="sub">
        FB Lite Auto Tool
    </div>

    {% if error %}
    <div class="error">
        {{ error }}
    </div>
    {% endif %}

    <form method="POST">

        <label>Username</label>

        <input
            name="username"
            autocomplete="username"
            required
        >

        <label>Password</label>

        <input
            name="password"
            type="password"
            autocomplete="current-password"
            required
        >

        <button type="submit">
            🔓 Login
        </button>

    </form>

</div>

</body>
</html>
"""


@app.route("/login", methods=["GET", "POST"])
def login_page():

    error = ""

    if request.method == "POST":

        username = (
            request.form.get("username") or ""
        )

        password = (
            request.form.get("password") or ""
        )

        if (
            username == ADMIN_USER
            and
            password == ADMIN_PASS
        ):

            session["logged_in"] = True

            return redirect(
                url_for("admin_panel")
            )

        error = "Invalid username or password"

    return render_template_string(
        LOGIN_HTML,
        error=error
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login_page")
    )


# ═══════════════════════════════════════════════════════════════
# CLIENT API — ACTIVATE
# ═══════════════════════════════════════════════════════════════

@app.route("/activate", methods=["POST"])
def activate():

    data = request.get_json(
        force=True
    ) or {}

    key = (
        data.get("key") or ""
    ).strip().upper()

    hwid = (
        data.get("hwid") or ""
    ).strip()

    pc_name = (
        data.get("pc_name") or ""
    ).strip()[:80]

    if not key or not hwid:

        return jsonify({
            "ok": False,
            "msg": "Missing key or hwid"
        })

    db = load_db()

    if key not in db:

        return jsonify({
            "ok": False,
            "msg": "Invalid license key"
        })

    entry = db[key]

    if entry.get("banned"):

        return jsonify({
            "ok": False,
            "msg": "License blocked"
        })

    if is_expired(entry):

        return jsonify({
            "ok": False,
            "msg": "License expired"
        })

    bound = entry.get("hwid")

    current_time = iso_now()

    # প্রথম activation
    if not bound:

        entry["hwid"] = hwid
        entry["pc_name"] = pc_name
        entry["activated_at"] = current_time
        entry["last_seen"] = current_time

        db[key] = entry

        save_db(db)

        return jsonify({
            "ok": True,
            "msg": "Activated",
            "key": key,
            "name": entry.get("name", ""),
            "expires": entry.get("expires"),
            "online": True
        })

    # একই computer
    if bound == hwid:

        entry["last_seen"] = current_time

        if pc_name:
            entry["pc_name"] = pc_name

        db[key] = entry

        save_db(db)

        return jsonify({
            "ok": True,
            "msg": "OK",
            "key": key,
            "name": entry.get("name", ""),
            "expires": entry.get("expires"),
            "online": True
        })

    return jsonify({
        "ok": False,
        "msg": "This license is already activated on another system!"
    })


# ═══════════════════════════════════════════════════════════════
# CLIENT API — HEARTBEAT
# ═══════════════════════════════════════════════════════════════

@app.route("/heartbeat", methods=["POST"])
def heartbeat():

    data = request.get_json(
        force=True
    ) or {}

    key = (
        data.get("key") or ""
    ).strip().upper()

    hwid = (
        data.get("hwid") or ""
    ).strip()

    pc_name = (
        data.get("pc_name") or ""
    ).strip()[:80]

    if not key or not hwid:

        return jsonify({
            "ok": False,
            "msg": "Missing key or hwid"
        })

    db = load_db()

    entry = db.get(key)

    if not entry:

        return jsonify({
            "ok": False,
            "msg": "License not found"
        })

    if entry.get("hwid") != hwid:

        return jsonify({
            "ok": False,
            "msg": "HWID mismatch"
        })

    if entry.get("banned"):

        return jsonify({
            "ok": False,
            "msg": "License blocked"
        })

    if is_expired(entry):

        return jsonify({
            "ok": False,
            "msg": "License expired"
        })

    entry["last_seen"] = iso_now()

    if pc_name:
        entry["pc_name"] = pc_name

    db[key] = entry

    save_db(db)

    return jsonify({
        "ok": True,
        "online": True,
        "expires": entry.get("expires"),
        "name": entry.get("name", "")
    })


# ═══════════════════════════════════════════════════════════════
# CLIENT API — STATUS
# ═══════════════════════════════════════════════════════════════

@app.route("/license/status", methods=["POST"])
def license_status_api():

    data = request.get_json(
        force=True
    ) or {}

    key = (
        data.get("key") or ""
    ).strip().upper()

    hwid = (
        data.get("hwid") or ""
    ).strip()

    db = load_db()

    entry = db.get(key)

    if not entry:

        return jsonify({
            "ok": False,
            "msg": "License not found"
        })

    if entry.get("banned"):

        return jsonify({
            "ok": False,
            "msg": "License blocked"
        })

    if is_expired(entry):

        return jsonify({
            "ok": False,
            "msg": "License expired"
        })

    if hwid and entry.get("hwid") != hwid:

        return jsonify({
            "ok": False,
            "msg": "HWID mismatch"
        })

    return jsonify({
        "ok": True,
        "key": key,
        "name": entry.get("name", ""),
        "expires": entry.get("expires"),
        "online": is_online(entry),
        "last_seen": entry.get("last_seen")
    })


# ═══════════════════════════════════════════════════════════════
# ADMIN PANEL HTML
# ═══════════════════════════════════════════════════════════════

PANEL_HTML = """
<!DOCTYPE html>
<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width,initial-scale=1"
>

<title>License Control Center</title>

<style>

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    background:
        radial-gradient(
            circle at 10% 0%,
            rgba(79,70,229,.18),
            transparent 30%
        ),
        #020617;

    color: #e2e8f0;

    font-family:
        Segoe UI,
        Arial,
        sans-serif;

    min-height: 100vh;
}

/* HEADER */

.header {
    position: sticky;
    top: 0;
    z-index: 20;

    display: flex;
    align-items: center;
    justify-content: space-between;

    padding: 16px 22px;

    background:
        rgba(2,6,23,.88);

    border-bottom:
        1px solid
        #1e293b;

    backdrop-filter: blur(14px);
}

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

.brand-icon {
    width: 42px;
    height: 42px;

    display: flex;
    align-items: center;
    justify-content: center;

    border-radius: 12px;

    background:
        linear-gradient(
            135deg,
            #6366f1,
            #8b5cf6
        );

    font-size: 21px;
}

.brand h1 {
    font-size: 17px;
}

.brand small {
    display: block;
    margin-top: 3px;

    color: #64748b;
    font-size: 11px;
}

.header-right {
    display: flex;
    align-items: center;
    gap: 9px;
}

.live-pill {
    padding: 7px 11px;

    border-radius: 20px;

    background: #052e1b;
    color: #34d399;

    font-size: 11px;
    font-weight: 800;
}

.logout {
    padding: 8px 12px;

    border:
        1px solid
        #334155;

    border-radius: 9px;

    color: #cbd5e1;

    text-decoration: none;

    font-size: 12px;
}

/* WRAPPER */

.wrap {
    max-width: 1450px;

    margin: auto;

    padding: 22px;
}

/* STATS */

.stats {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(150px,1fr)
        );

    gap: 12px;

    margin-bottom: 20px;
}

.stat {
    position: relative;

    padding: 18px;

    background:
        linear-gradient(
            145deg,
            #0f172a,
            #111827
        );

    border:
        1px solid
        #1e293b;

    border-radius: 16px;

    overflow: hidden;
}

.stat::before {
    content: "";

    position: absolute;

    left: 0;
    right: 0;
    top: 0;

    height: 3px;

    background: #6366f1;
}

.stat.live::before {
    background: #10b981;
}

.stat.expired::before {
    background: #f59e0b;
}

.stat.blocked::before {
    background: #ef4444;
}

.stat.pending::before {
    background: #38bdf8;
}

.stat-number {
    font-size: 28px;

    font-weight: 900;

    margin-bottom: 5px;
}

.stat-label {
    color: #64748b;

    font-size: 10px;

    font-weight: 800;

    letter-spacing: .7px;

    text-transform: uppercase;
}

.blue {
    color: #60a5fa;
}

.green {
    color: #34d399;
}

.yellow {
    color: #fbbf24;
}

.red {
    color: #f87171;
}

.cyan {
    color: #22d3ee;
}

/* GENERATOR */

.generator {
    padding: 20px;

    background:
        linear-gradient(
            145deg,
            #111827,
            #0f172a
        );

    border:
        1px solid
        #1e293b;

    border-radius: 16px;

    margin-bottom: 18px;
}

.generator-title {
    margin-bottom: 15px;

    font-size: 14px;

    font-weight: 800;

    color: #cbd5e1;
}

.generator-grid {
    display: grid;

    grid-template-columns:
        1.3fr
        110px
        150px
        auto;

    gap: 10px;
}

input,
select {
    width: 100%;

    padding: 12px 13px;

    background: #020617;

    color: #e2e8f0;

    border:
        1px solid
        #334155;

    border-radius: 10px;

    outline: none;

    font-size: 13px;
}

input:focus,
select:focus {
    border-color: #6366f1;

    box-shadow:
        0 0 0 3px
        rgba(99,102,241,.12);
}

button {
    border: 0;

    border-radius: 10px;

    padding: 12px 15px;

    cursor: pointer;

    font-weight: 800;

    color: white;

    transition: .15s;
}

.btn-generate {
    background:
        linear-gradient(
            135deg,
            #10b981,
            #059669
        );
}

.btn-generate:hover {
    transform: translateY(-1px);
}

.btn-refresh {
    background: #334155;
}

.btn-blue {
    background: #4f46e5;
}

/* TOOLBAR */

.toolbar {
    display: flex;

    gap: 10px;

    margin-bottom: 15px;

    flex-wrap: wrap;
}

.search {
    flex: 1;

    min-width: 230px;
}

/* TABLE */

.table-box {
    background: #0f172a;

    border:
        1px solid
        #1e293b;

    border-radius: 16px;

    overflow: hidden;
}

.table-scroll {
    overflow-x: auto;
}

table {
    width: 100%;

    min-width: 1120px;

    border-collapse: collapse;
}

th {
    padding: 13px;

    text-align: left;

    background: #1e293b;

    color: #94a3b8;

    font-size: 10px;

    letter-spacing: .6px;

    text-transform: uppercase;

    white-space: nowrap;
}

td {
    padding: 13px;

    border-top:
        1px solid
        #1e293b;

    font-size: 12px;

    color: #cbd5e1;

    vertical-align: middle;
}

tr:hover td {
    background: #111c30;
}

.key {
    font-family: Consolas, monospace;

    color: #34d399;

    font-weight: 800;

    white-space: nowrap;
}

.name {
    color: #f1f5f9;

    font-weight: 700;
}

.pc {
    color: #cbd5e1;

    font-weight: 600;
}

.hwid {
    font-family: Consolas, monospace;

    color: #64748b;

    font-size: 10px;
}

/* BADGES */

.badge {
    display: inline-flex;

    align-items: center;

    gap: 5px;

    padding: 5px 9px;

    border-radius: 20px;

    font-size: 9px;

    font-weight: 900;

    text-transform: uppercase;

    white-space: nowrap;
}

.active {
    background: #064e3b;
    color: #34d399;
}

.pending {
    background: #172554;
    color: #93c5fd;
}

.expired {
    background: #78350f;
    color: #fbbf24;
}

.blocked {
    background: #7f1d1d;
    color: #fca5a5;
}

.online {
    background: #052e1b;
    color: #34d399;
}

.offline {
    background: #1e293b;
    color: #94a3b8;
}

/* ACTIONS */

.actions {
    display: flex;

    gap: 5px;

    flex-wrap: wrap;
}

.action {
    padding: 6px 9px;

    border-radius: 7px;

    font-size: 10px;
}

.action-name {
    background: #4f46e5;
}

.action-reset {
    background: #d97706;
}

.action-block {
    background: #dc2626;
}

.action-unblock {
    background: #059669;
}

.action-delete {
    background: #334155;
}

.action:hover {
    filter: brightness(1.15);
}

/* MODAL */

.modal {
    position: fixed;

    inset: 0;

    display: none;

    align-items: center;
    justify-content: center;

    padding: 20px;

    background:
        rgba(0,0,0,.78);

    z-index: 100;
}

.modal.show {
    display: flex;
}

.modal-card {
    width: 100%;

    max-width: 470px;

    padding: 25px;

    background: #1e293b;

    border:
        1px solid
        #334155;

    border-radius: 18px;

    box-shadow:
        0 30px 90px
        rgba(0,0,0,.6);
}

.modal-card h2 {
    font-size: 18px;

    margin-bottom: 15px;
}

.modal-card p {
    color: #94a3b8;

    font-size: 13px;

    margin-bottom: 15px;
}

.key-result {
    padding: 18px;

    margin-bottom: 15px;

    text-align: center;

    background: #020617;

    border:
        1px solid
        #10b981;

    border-radius: 12px;
}

.key-result strong {
    display: block;

    color: #34d399;

    font-family: Consolas, monospace;

    font-size: 17px;

    word-break: break-word;
}

.key-result span {
    display: block;

    margin-top: 8px;

    color: #64748b;

    font-size: 11px;
}

.modal-buttons {
    display: flex;

    gap: 8px;
}

.modal-buttons button {
    flex: 1;
}

/* TOAST */

.toast {
    position: fixed;

    right: 22px;
    bottom: 22px;

    z-index: 200;

    padding: 13px 18px;

    background: #10b981;

    color: white;

    border-radius: 10px;

    font-size: 13px;

    font-weight: 800;

    opacity: 0;

    transform: translateY(20px);

    pointer-events: none;

    transition: .25s;
}

.toast.show {
    opacity: 1;

    transform: translateY(0);
}

.toast.error {
    background: #ef4444;
}

/* RESPONSIVE */

@media(max-width:900px) {

    .generator-grid {
        grid-template-columns:
            1fr 1fr;
    }

}

@media(max-width:600px) {

    .header {
        padding: 13px;
    }

    .wrap {
        padding: 12px;
    }

    .brand h1 {
        font-size: 14px;
    }

    .live-pill {
        display: none;
    }

    .generator-grid {
        grid-template-columns: 1fr;
    }

}

</style>

</head>

<body>

<!-- HEADER -->

<header class="header">

    <div class="brand">

        <div class="brand-icon">
            🔐
        </div>

        <div>
            <h1>License Control Center</h1>

            <small>
                FB Lite Auto Tool
            </small>
        </div>

    </div>

    <div class="header-right">

        <span class="live-pill">
            🟢 LIVE MONITOR
        </span>

        <a
            class="logout"
            href="/logout"
        >
            Logout
        </a>

    </div>

</header>


<div class="wrap">

    <!-- STATS -->

    <section class="stats">

        <div class="stat">

            <div class="stat-number blue">
                {{ stats.total }}
            </div>

            <div class="stat-label">
                Total Keys
            </div>

        </div>


        <div class="stat live">

            <div class="stat-number green">
                {{ stats.live }}
            </div>

            <div class="stat-label">
                Live Now
            </div>

        </div>


        <div class="stat">

            <div class="stat-number cyan">
                {{ stats.activated }}
            </div>

            <div class="stat-label">
                Activated
            </div>

        </div>


        <div class="stat pending">

            <div class="stat-number cyan">
                {{ stats.pending }}
            </div>

            <div class="stat-label">
                Not Activated
            </div>

        </div>


        <div class="stat expired">

            <div class="stat-number yellow">
                {{ stats.expired }}
            </div>

            <div class="stat-label">
                Expired
            </div>

        </div>


        <div class="stat blocked">

            <div class="stat-number red">
                {{ stats.banned }}
            </div>

            <div class="stat-label">
                Blocked
            </div>

        </div>

    </section>


    <!-- GENERATOR -->

    <section class="generator">

        <div class="generator-title">
            ⚡ Generate New License
        </div>

        <div class="generator-grid">

            <input
                id="customerName"
                placeholder="Customer name"
                maxlength="80"
            >

            <input
                id="days"
                type="number"
                value="30"
                min="1"
                max="3650"
                placeholder="Days"
            >

            <input
                id="customKey"
                placeholder="Optional key"
                maxlength="40"
            >

            <button
                class="btn-generate"
                onclick="generateKey()"
            >
                + Generate Key
            </button>

        </div>

    </section>


    <!-- TOOLBAR -->

    <div class="toolbar">

        <input
            class="search"
            id="search"
            placeholder="🔍 Search name, key, HWID, PC..."
            oninput="filterTable()"
        >

        <select
            id="filter"
            onchange="filterTable()"
        >

            <option value="all">
                All
            </option>

            <option value="online">
                🟢 Online
            </option>

            <option value="offline">
                ⚫ Offline
            </option>

            <option value="active">
                Active
            </option>

            <option value="pending">
                Not Activated
            </option>

            <option value="expired">
                Expired
            </option>

            <option value="banned">
                Blocked
            </option>

        </select>

        <button
            class="btn-refresh"
            onclick="location.reload()"
        >
            ⟳ Refresh
        </button>

    </div>


    <!-- TABLE -->

    <div class="table-box">

        <div class="table-scroll">

            <table id="licenseTable">

                <thead>

                <tr>

                    <th>Customer</th>
                    <th>License Key</th>
                    <th>Status</th>
                    <th>Live</th>
                    <th>PC Name</th>
                    <th>HWID</th>
                    <th>Expires</th>
                    <th>Last Seen</th>
                    <th>Actions</th>

                </tr>

                </thead>

                <tbody id="tbody">

                {% for item in keys %}

                <tr
                    data-status="{{ item.status }}"
                    data-online="{{ 'online' if item.online else 'offline' }}"
                >

                    <td>
                        <div class="name">
                            {{ item.name or 'Unnamed Customer' }}
                        </div>
                    </td>

                    <td>

                        <span class="key">
                            {{ item.key }}
                        </span>

                        <button
                            class="action"
                            onclick="copyText('{{ item.key }}')"
                            title="Copy"
                        >
                            📋
                        </button>

                    </td>

                    <td>

                        {% if item.status == "active" %}

                        <span class="badge active">
                            ● Active
                        </span>

                        {% elif item.status == "pending" %}

                        <span class="badge pending">
                            ● Pending
                        </span>

                        {% elif item.status == "expired" %}

                        <span class="badge expired">
                            ● Expired
                        </span>

                        {% else %}

                        <span class="badge blocked">
                            ● Blocked
                        </span>

                        {% endif %}

                    </td>

                    <td>

                        {% if item.online %}

                        <span class="badge online">
                            ● ONLINE
                        </span>

                        {% else %}

                        <span class="badge offline">
                            ● OFFLINE
                        </span>

                        {% endif %}

                    </td>

                    <td class="pc">
                        {{ item.pc_name or "—" }}
                    </td>

                    <td class="hwid">
                        {{ item.hwid_short or "—" }}
                    </td>

                    <td>
                        {{ item.expires }}
                    </td>

                    <td>
                        {{ item.last_seen }}
                    </td>

                    <td>

                        <div class="actions">

                            <button
                                class="action action-name"
                                onclick="editName('{{ item.key }}','{{ item.name|e }}')"
                            >
                                Name
                            </button>

                            {% if item.hwid %}

                            <button
                                class="action action-reset"
                                onclick="rowAction('reset','{{ item.key }}')"
                            >
                                Reset
                            </button>

                            {% endif %}

                            {% if item.banned %}

                            <button
                                class="action action-unblock"
                                onclick="rowAction('unban','{{ item.key }}')"
                            >
                                Unblock
                            </button>

                            {% else %}

                            <button
                                class="action action-block"
                                onclick="rowAction('ban','{{ item.key }}')"
                            >
                                Block
                            </button>

                            {% endif %}

                            <button
                                class="action action-delete"
                                onclick="rowAction('delete','{{ item.key }}')"
                            >
                                Delete
                            </button>

                        </div>

                    </td>

                </tr>

                {% endfor %}

                </tbody>

            </table>

        </div>

    </div>

</div>


<!-- GENERATE MODAL -->

<div
    class="modal"
    id="generateModal"
>

    <div class="modal-card">

        <h2>
            ✅ License Created
        </h2>

        <p>
            এই key-টি customer-কে দিতে পারবেন।
        </p>

        <div class="key-result">

            <strong id="resultKey">
                —
            </strong>

            <span id="resultInfo">
                —
            </span>

        </div>

        <div class="modal-buttons">

            <button
                class="btn-blue"
                onclick="copyResultKey()"
            >
                📋 Copy Key
            </button>

            <button
                class="btn-refresh"
                onclick="closeModal()"
            >
                Close
            </button>

        </div>

    </div>

</div>


<!-- TOAST -->

<div
    class="toast"
    id="toast"
>
    Done
</div>


<script>

function toast(message, error=false) {

    const element =
        document.getElementById("toast");

    element.textContent = message;

    element.className =
        "toast show" +
        (error ? " error" : "");

    clearTimeout(
        element._timer
    );

    element._timer =
        setTimeout(() => {

            element.className =
                "toast" +
                (error ? " error" : "");

        }, 2500);
}


function copyText(text) {

    navigator.clipboard
        .writeText(text)
        .then(() => {

            toast("✓ Copied");

        })
        .catch(() => {

            toast(
                "Copy failed",
                true
            );

        });

}


function copyResultKey() {

    const key =
        document.getElementById(
            "resultKey"
        ).textContent;

    copyText(key);
}


function closeModal() {

    document
        .getElementById(
            "generateModal"
        )
        .classList.remove("show");

}


async function generateKey() {

    const name =
        document
            .getElementById(
                "customerName"
            )
            .value
            .trim();

    const days =
        parseInt(
            document
                .getElementById("days")
                .value
        ) || 30;

    const customKey =
        document
            .getElementById(
                "customKey"
            )
            .value
            .trim()
            .toUpperCase();


    if (!name) {

        toast(
            "Customer name দিন",
            true
        );

        return;
    }


    if (
        days < 1 ||
        days > 3650
    ) {

        toast(
            "Days must be 1-3650",
            true
        );

        return;
    }


    try {

        const response =
            await fetch(
                "/admin/api/new",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        name,
                        days,
                        custom_key:
                            customKey
                    })
                }
            );


        const result =
            await response.json();


        if (!result.ok) {

            toast(
                result.msg ||
                "Failed",
                true
            );

            return;
        }


        document
            .getElementById(
                "resultKey"
            )
            .textContent =
                result.key;


        document
            .getElementById(
                "resultInfo"
            )
            .textContent =
                name +
                " • Expires: " +
                result.expires;


        document
            .getElementById(
                "generateModal"
            )
            .classList.add("show");


        document
            .getElementById(
                "customerName"
            )
            .value = "";


        document
            .getElementById(
                "customKey"
            )
            .value = "";


        toast(
            "✓ License created"
        );


        setTimeout(
            () => location.reload(),
            5000
        );

    }

    catch (error) {

        toast(
            "Error: " + error,
            true
        );

    }

}


async function editName(
    key,
    oldName
) {

    const name =
        prompt(
            "Customer name:",
            oldName || ""
        );


    if (
        name === null
    ) {
        return;
    }


    const cleanName =
        name.trim();


    if (!cleanName) {

        toast(
            "Name cannot be empty",
            true
        );

        return;
    }


    try {

        const response =
            await fetch(
                "/admin/api/name",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        key,
                        name:
                            cleanName
                    })
                }
            );


        const result =
            await response.json();


        if (result.ok) {

            toast(
                "✓ Name updated"
            );

            setTimeout(
                () => location.reload(),
                500
            );

        } else {

            toast(
                result.msg ||
                "Failed",
                true
            );

        }

    }

    catch (error) {

        toast(
            "Error: " + error,
            true
        );

    }

}


async function rowAction(
    action,
    key
) {

    const labels = {

        reset:
            "Reset HWID",

        ban:
            "Block",

        unban:
            "Unblock",

        delete:
            "Delete"

    };


    const label =
        labels[action] ||
        action;


    if (
        !confirm(
            label +
            " — " +
            key +
            " ?"
        )
    ) {
        return;
    }


    try {

        const response =
            await fetch(
                "/admin/api/" +
                action,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        key
                    })
                }
            );


        const result =
            await response.json();


        if (result.ok) {

            toast(
                "✓ " +
                label +
                " done"
            );

            setTimeout(
                () => location.reload(),
                500
            );

        } else {

            toast(
                result.msg ||
                "Failed",
                true
            );

        }

    }

    catch (error) {

        toast(
            "Error: " + error,
            true
        );

    }

}


function filterTable() {

    const search =
        document
            .getElementById(
                "search"
            )
            .value
            .toLowerCase()
            .trim();


    const filter =
        document
            .getElementById(
                "filter"
            )
            .value;


    let visible = 0;


    document
        .querySelectorAll(
            "#tbody tr"
        )
        .forEach(row => {

            const text =
                row.textContent
                    .toLowerCase();


            const status =
                row.dataset.status;


            const online =
                row.dataset.online;


            const searchMatch =
                !search ||
                text.includes(search);


            let filterMatch = true;


            if (
                filter === "online"
            ) {

                filterMatch =
                    online === "online";

            }

            else if (
                filter === "offline"
            ) {

                filterMatch =
                    online === "offline";

            }

            else if (
                [
                    "active",
                    "pending",
                    "expired",
                    "banned"
                ].includes(filter)
            ) {

                filterMatch =
                    status === filter;

            }


            const show =
                searchMatch &&
                filterMatch;


            row.style.display =
                show ? "" : "none";


            if (show) {
                visible++;
            }

        });

}


document.addEventListener(
    "DOMContentLoaded",
    filterTable
);


/*
 * Auto refresh:
 * প্রতি 15 সেকেন্ডে page reload হবে।
 * ফলে heartbeat-এর নতুন ONLINE/OFFLINE
 * status দেখা যাবে।
 */

setInterval(
    () => location.reload(),
    15000
);

</script>

</body>

</html>
"""


# ═══════════════════════════════════════════════════════════════
# ADMIN PANEL
# ═══════════════════════════════════════════════════════════════

@app.route("/")
def index():

    if not session.get("logged_in"):

        return redirect(
            url_for("login_page")
        )

    return redirect(
        url_for("admin_panel")
    )


@app.route("/admin")
@login_required
def admin_panel():

    db = load_db()

    keys = []

    stats = {
        "total": 0,
        "live": 0,
        "activated": 0,
        "pending": 0,
        "expired": 0,
        "banned": 0
    }


    for key, entry in db.items():

        status =
            license_status(entry)

        online =
            is_online(entry)


        if status == "active":
            stats["activated"] += 1

        elif status == "pending":
            stats["pending"] += 1

        elif status == "expired":
            stats["expired"] += 1

        elif status == "banned":
            stats["banned"] += 1


        if online:
            stats["live"] += 1


        keys.append({

            "key":
                key,

            "name":
                entry.get(
                    "name",
                    ""
                ),

            "status":
                status,

            "online":
                online,

            "banned":
                bool(
                    entry.get(
                        "banned"
                    )
                ),

            "hwid":
                entry.get(
                    "hwid"
                ),

            "hwid_short":
                short_hwid(
                    entry.get(
                        "hwid"
                    )
                ),

            "pc_name":
                entry.get(
                    "pc_name",
                    ""
                ),

            "expires":
                format_expiry(
                    entry.get(
                        "expires"
                    )
                ),

            "last_seen":
                format_last_seen(
                    entry.get(
                        "last_seen"
                    )
                ),

            "created_at":
                entry.get(
                    "created_at",
                    ""
                )

        })


    stats["total"] =
        len(db)


    # নতুন key আগে দেখাবে
    keys.sort(
        key=lambda x:
            x.get(
                "created_at",
                ""
            ),
        reverse=True
    )


    return render_template_string(
        PANEL_HTML,
        keys=keys,
        stats=stats
    )


# ═══════════════════════════════════════════════════════════════
# ADMIN API — CREATE
# ═══════════════════════════════════════════════════════════════

@app.route(
    "/admin/api/new",
    methods=["POST"]
)
@login_required
def api_new():

    data =
        request.get_json(
            force=True
        ) or {}


    name =
        (
            data.get("name")
            or ""
        ).strip()[:80]


    if not name:

        return jsonify({
            "ok": False,
            "msg":
                "Customer name is required"
        })


    try:

        days =
            int(
                data.get(
                    "days",
                    30
                )
            )

    except Exception:

        days = 30


    if days < 1 or days > 3650:

        return jsonify({
            "ok": False,
            "msg":
                "Days must be 1-3650"
        })


    custom_key =
        (
            data.get(
                "custom_key"
            )
            or ""
        ).strip().upper()


    db = load_db()


    if custom_key:

        new_key =
            custom_key

        if new_key in db:

            return jsonify({
                "ok": False,
                "msg":
                    "This key already exists"
            })

    else:

        new_key =
            generate_license_key()


    created =
        now()


    expires =
        created +
        timedelta(
            days=days
        )


    db[new_key] = {

        "name":
            name,

        "hwid":
            None,

        "pc_name":
            "",

        "expires":
            expires.isoformat(
                timespec="seconds"
            ),

        "banned":
            False,

        "created_at":
            created.isoformat(
                timespec="seconds"
            ),

        "activated_at":
            None,

        "last_seen":
            None,

        "reset_at":
            None

    }


    save_db(db)


    return jsonify({

        "ok":
            True,

        "key":
            new_key,

        "name":
            name,

        "expires":
            expires.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

    })


# ═══════════════════════════════════════════════════════════════
# ADMIN API — UPDATE NAME
# ═══════════════════════════════════════════════════════════════

@app.route(
    "/admin/api/name",
    methods=["POST"]
)
@login_required
def api_name():

    data =
        request.get_json(
            force=True
        ) or {}


    key =
        (
            data.get("key")
            or ""
        ).strip().upper()


    name =
        (
            data.get("name")
            or ""
        ).strip()[:80]


    if not name:

        return jsonify({
            "ok": False,
            "msg":
                "Name is required"
        })


    db = load_db()


    if key not in db:

        return jsonify({
            "ok": False,
            "msg":
                "License not found"
        })


    db[key]["name"] =
        name


    db[key]["updated_at"] =
        iso_now()


    save_db(db)


    return jsonify({
        "ok": True
    })


# ═══════════════════════════════════════════════════════════════
# ADMIN API — RESET HWID
# ═══════════════════════════════════════════════════════════════

@app.route(
    "/admin/api/reset",
    methods=["POST"]
)
@login_required
def api_reset():

    data =
        request.get_json(
            force=True
        ) or {}


    key =
        (
            data.get("key")
            or ""
        ).strip().upper()


    db = load_db()


    if key not in db:

        return jsonify({
            "ok": False,
            "msg":
                "License not found"
        })


    db[key]["hwid"] =
        None

    db[key]["pc_name"] =
        ""

    db[key]["last_seen"] =
        None

    db[key]["reset_at"] =
        iso_now()


    save_db(db)


    return jsonify({
        "ok": True
    })


# ═══════════════════════════════════════════════════════════════
# ADMIN API — BLOCK
# ═══════════════════════════════════════════════════════════════

@app.route(
    "/admin/api/ban",
    methods=["POST"]
)
@login_required
def api_ban():

    data =
        request.get_json(
            force=True
        ) or {}


    key =
        (
            data.get("key")
            or ""
        ).strip().upper()


    db = load_db()


    if key not in db:

        return jsonify({
            "ok": False,
            "msg":
                "License not found"
        })


    db[key]["banned"] =
        True

    db[key]["blocked_at"] =
        iso_now()


    save_db(db)


    return jsonify({
        "ok": True
    })


# ═══════════════════════════════════════════════════════════════
# ADMIN API — UNBLOCK
# ═══════════════════════════════════════════════════════════════

@app.route(
    "/admin/api/unban",
    methods=["POST"]
)
@login_required
def api_unban():

    data =
        request.get_json(
            force=True
        ) or {}


    key =
        (
            data.get("key")
            or ""
        ).strip().upper()


    db = load_db()


    if key not in db:

        return jsonify({
            "ok": False,
            "msg":
                "License not found"
        })


    db[key]["banned"] =
        False

    db[key]["unblocked_at"] =
        iso_now()


    save_db(db)


    return jsonify({
        "ok": True
    })


# ═══════════════════════════════════════════════════════════════
# ADMIN API — DELETE
# ═══════════════════════════════════════════════════════════════

@app.route(
    "/admin/api/delete",
    methods=["POST"]
)
@login_required
def api_delete():

    data =
        request.get_json(
            force=True
        ) or {}


    key =
        (
            data.get("key")
            or ""
        ).strip().upper()


    db = load_db()


    if key not in db:

        return jsonify({
            "ok": False,
            "msg":
                "License not found"
        })


    del db[key]


    save_db(db)


    return jsonify({
        "ok": True
    })


# ═══════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":

    port =
        int(
            os.environ.get(
                "PORT",
                5000
            )
        )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
