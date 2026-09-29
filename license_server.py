# license_server.py
# ═══════════════════════════════════════════════════════════════
#  FB Lite Auto Tool — License Server + Full Admin Panel
#  Deploy on: Render / VPS
#  Start Command: gunicorn license_server:app
# ═══════════════════════════════════════════════════════════════
from flask import (Flask, request, jsonify, session, redirect,
                   url_for, render_template_string)
import json, os, secrets, string
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "FB-LITE-ADMIN-SECRET-KEY-CHANGE-THIS-2026-XYZ-ABC123"

DB_FILE = "licenses.json"
ONLINE_SECONDS = 75

# ═══════════════════════════════════════════════════════════════
#  ⚠️  ADMIN LOGIN CREDENTIALS — পরিবর্তন করুন!
# ═══════════════════════════════════════════════════════════════
ADMIN_USER = "admin"
ADMIN_PASS = "Rubel2026"
# ═══════════════════════════════════════════════════════════════


# ─────────────── Database ───────────────
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_db(db):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
    except Exception:
        pass


def _is_online(entry):
    last_seen = entry.get("last_seen")
    if not last_seen:
        return False
    try:
        diff = (datetime.now() - datetime.fromisoformat(last_seen)).total_seconds()
        return diff <= ONLINE_SECONDS
    except Exception:
        return False


def _is_expired(entry):
    exp = entry.get("expires")
    if not exp:
        return False
    try:
        return datetime.now() > datetime.fromisoformat(exp)
    except Exception:
        return False


def login_required(f):
    @wraps(f)
    def deco(*a, **kw):
        if not session.get("logged_in"):
            return redirect(url_for("login_page"))
        return f(*a, **kw)
    return deco


# ═══════════════════════════════════════════════════════════════
#  CLIENT API
# ═══════════════════════════════════════════════════════════════
@app.route("/activate", methods=["POST"])
def activate():
    data = request.get_json(force=True) or {}
    key  = (data.get("key") or "").strip().upper()
    hwid = (data.get("hwid") or "").strip()
    pc_name = (data.get("pc_name") or "")[:60]

    if not key or not hwid:
        return jsonify({"ok": False, "msg": "Missing key or hwid"})

    db = load_db()
    if key not in db:
        return jsonify({"ok": False, "msg": "Invalid license key"})

    entry = db[key]

    if entry.get("banned"):
        return jsonify({"ok": False, "msg": "License banned"})
    if _is_expired(entry):
        return jsonify({"ok": False, "msg": "License expired"})

    bound = entry.get("hwid")

    if not bound:
        entry["hwid"] = hwid
        entry["pc_name"] = pc_name
        entry["activated_at"] = datetime.now().isoformat()
        entry["last_seen"] = datetime.now().isoformat()
        db[key] = entry
        save_db(db)
        return jsonify({"ok": True, "msg": "Activated",
                        "expires": entry.get("expires")})

    if bound == hwid:
        entry["last_seen"] = datetime.now().isoformat()
        if pc_name:
            entry["pc_name"] = pc_name
        db[key] = entry
        save_db(db)
        return jsonify({"ok": True, "msg": "OK",
                        "expires": entry.get("expires")})

    return jsonify({"ok": False,
                    "msg": "This license is already activated on another system!"})


@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    data = request.get_json(force=True) or {}
    key  = (data.get("key") or "").strip().upper()
    hwid = (data.get("hwid") or "").strip()

    db = load_db()
    entry = db.get(key)
    if not entry:
        return jsonify({"ok": False, "msg": "Not found"})
    if entry.get("hwid") != hwid:
        return jsonify({"ok": False, "msg": "HWID mismatch"})
    if entry.get("banned"):
        return jsonify({"ok": False, "msg": "Banned"})
    if _is_expired(entry):
        return jsonify({"ok": False, "msg": "Expired"})

    entry["last_seen"] = datetime.now().isoformat()
    db[key] = entry
    save_db(db)
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════
#  LOGIN PAGE
# ═══════════════════════════════════════════════════════════════
LOGIN_HTML = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>License Admin — Login</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
     background:linear-gradient(135deg,#0F172A 0%,#1E1B4B 100%);
     min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.card{background:#1E293B;border-radius:18px;padding:40px 32px;width:100%;max-width:400px;
      box-shadow:0 20px 60px rgba(0,0,0,.5);border:1px solid #334155}
h1{color:#A5B4FC;text-align:center;font-size:22px;margin-bottom:6px}
p{color:#94A3B8;text-align:center;font-size:13px;margin-bottom:26px}
label{display:block;color:#CBD5E1;font-size:12px;font-weight:600;margin-bottom:6px;letter-spacing:.3px}
input{width:100%;padding:13px 14px;background:#0F172A;border:1.5px solid #334155;border-radius:10px;
      color:#E2E8F0;font-size:15px;margin-bottom:16px;outline:none;transition:.2s}
input:focus{border-color:#6366F1;box-shadow:0 0 0 3px rgba(99,102,241,.15)}
button{width:100%;padding:14px;background:#6366F1;color:#fff;border:none;border-radius:10px;
       font-size:15px;font-weight:600;cursor:pointer;transition:.2s}
button:hover{background:#4F46E5}
.err{background:#7F1D1D;color:#FCA5A5;padding:10px 14px;border-radius:8px;
     font-size:13px;margin-bottom:16px;text-align:center}
.brand{text-align:center;font-size:38px;margin-bottom:8px}
</style></head><body>
<div class="card">
  <div class="brand">🔐</div>
  <h1>License Admin Panel</h1>
  <p>FB Lite Auto Tool Pro</p>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form method="POST">
    <label>Username</label>
    <input name="username" autocomplete="username" required>
    <label>Password</label>
    <input name="password" type="password" autocomplete="current-password" required>
    <button type="submit">Login</button>
  </form>
</div></body></html>"""


@app.route("/login", methods=["GET", "POST"])
def login_page():
    err = ""
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USER and \
           request.form.get("password") == ADMIN_PASS:
            session["logged_in"] = True
            return redirect(url_for("admin_panel"))
        err = "Invalid username or password"
    return render_template_string(LOGIN_HTML, error=err)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


# ═══════════════════════════════════════════════════════════════
#  ADMIN PANEL (FULL USER LIST)
# ═══════════════════════════════════════════════════════════════
PANEL_HTML = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>License Admin Dashboard</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
     background:#0B1220;color:#E2E8F0;min-height:100vh}

.hdr{background:#111827;padding:14px 20px;display:flex;justify-content:space-between;
     align-items:center;border-bottom:1px solid #1F2937;position:sticky;top:0;z-index:10}
.hdr h1{font-size:17px;color:#A5B4FC;font-weight:700}
.hdr .right{display:flex;gap:10px;align-items:center}
.hdr a{color:#94A3B8;text-decoration:none;font-size:13px;padding:7px 14px;
       border:1px solid #334155;border-radius:8px;transition:.2s}
.hdr a:hover{background:#1E293B;color:#E2E8F0}

.wrap{max-width:1400px;margin:0 auto;padding:22px 18px}

/* Stats Grid */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:22px}
.stat{background:#111827;padding:18px;border-radius:14px;border:1px solid #1F2937;
      text-align:center;position:relative;overflow:hidden}
.stat::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.stat.s-total::before{background:#60A5FA}
.stat.s-active::before{background:#34D399}
.stat.s-activated::before{background:#A78BFA}
.stat.s-expired::before{background:#F59E0B}
.stat.s-banned::before{background:#F87171}
.stat .n{font-size:28px;font-weight:800;margin-bottom:4px;line-height:1}
.stat .l{font-size:11px;color:#64748B;letter-spacing:.6px;text-transform:uppercase;font-weight:700}
.n-tot{color:#60A5FA}.n-act{color:#34D399}.n-actv{color:#A78BFA}
.n-exp{color:#F59E0B}.n-ban{color:#F87171}

/* Generator */
.gen{background:#111827;padding:20px;border-radius:14px;border:1px solid #1F2937;margin-bottom:18px}
.gen h2{font-size:14px;color:#CBD5E1;margin-bottom:14px;letter-spacing:.3px;
        display:flex;align-items:center;gap:8px}
.gen-row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.gen input{padding:12px 14px;background:#0B1220;border:1.5px solid #334155;border-radius:9px;
           color:#E2E8F0;font-size:14px;outline:none;width:130px;font-weight:600}
.gen input:focus{border-color:#6366F1;box-shadow:0 0 0 3px rgba(99,102,241,.15)}
.gen button{padding:12px 22px;background:#10B981;color:#fff;border:none;border-radius:9px;
            font-size:14px;font-weight:700;cursor:pointer;transition:.2s}
.gen button:hover{background:#059669}
.gen button.blue{background:#6366F1}
.gen button.blue:hover{background:#4F46E5}

/* Tools */
.tools{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;align-items:center}
.tools .search-box{flex:1;min-width:220px;position:relative}
.tools input[type=text]{width:100%;padding:12px 14px 12px 40px;background:#111827;
                        border:1.5px solid #1F2937;border-radius:10px;color:#E2E8F0;
                        font-size:14px;outline:none;transition:.2s}
.tools input[type=text]:focus{border-color:#6366F1}
.tools .search-box::before{content:'🔍';position:absolute;left:14px;top:50%;
                            transform:translateY(-50%);font-size:15px;opacity:.6}
.tools select{padding:12px 14px;background:#111827;border:1.5px solid #1F2937;border-radius:10px;
              color:#E2E8F0;font-size:14px;outline:none;cursor:pointer;font-weight:600}
.tools .cnt{color:#64748B;font-size:13px;font-weight:600;padding:0 4px}

/* Table */
.tbl-wrap{background:#111827;border-radius:14px;border:1px solid #1F2937;overflow:hidden}
table{width:100%;border-collapse:collapse}
th{background:#1E293B;padding:13px 12px;text-align:left;font-size:11px;color:#94A3B8;
   letter-spacing:.6px;text-transform:uppercase;font-weight:700;white-space:nowrap}
td{padding:12px;border-top:1px solid #1F2937;font-size:13px;color:#CBD5E1;vertical-align:middle}
tr.row:hover td{background:#0F172A}
.key{font-family:Consolas,'Courier New',monospace;color:#34D399;font-weight:700;font-size:12.5px;
     white-space:nowrap}
.badge{display:inline-block;padding:4px 10px;border-radius:20px;font-size:10.5px;
       font-weight:700;letter-spacing:.4px;text-transform:uppercase;white-space:nowrap}
.b-act{background:#064E3B;color:#34D399}
.b-pen{background:#1E3A8A;color:#93C5FD}
.b-exp{background:#78350F;color:#FBBF24}
.b-ban{background:#7F1D1D;color:#FCA5A5}
.actions{display:flex;gap:5px;flex-wrap:wrap}
.actions button{padding:6px 11px;border:none;border-radius:7px;font-size:11px;font-weight:700;
                cursor:pointer;transition:.15s;color:#fff;white-space:nowrap}
.act-reset{background:#F59E0B}.act-reset:hover{background:#D97706}
.act-ban{background:#EF4444}.act-ban:hover{background:#DC2626}
.act-unban{background:#10B981}.act-unban:hover{background:#059669}
.act-del{background:#374151}.act-del:hover{background:#1F2937}
.copy-btn{background:transparent;border:none;color:#64748B;cursor:pointer;
          font-size:11px;padding:2px 4px;margin-left:2px}
.copy-btn:hover{color:#34D399}
.empty{padding:60px 20px;text-align:center;color:#64748B;font-size:14px}
.mono{font-family:Consolas,monospace;font-size:11.5px;color:#94A3B8}
.pcname{color:#CBD5E1;font-size:12.5px;font-weight:600}

/* Modal */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:100;
               align-items:center;justify-content:center;padding:20px}
.modal-overlay.show{display:flex}
.modal{background:#1E293B;border-radius:16px;padding:26px;max-width:440px;width:100%;
       border:1px solid #334155;box-shadow:0 20px 60px rgba(0,0,0,.6)}
.modal h3{color:#A5B4FC;font-size:16px;margin-bottom:10px;display:flex;align-items:center;gap:8px}
.modal p{color:#94A3B8;font-size:13.5px;margin-bottom:16px;line-height:1.5}
.modal .key-box{background:#0B1220;border:1.5px solid #10B981;border-radius:10px;
                padding:16px;text-align:center;margin-bottom:16px}
.modal .key-box .k{font-family:Consolas,monospace;font-size:16px;color:#34D399;
                   font-weight:800;word-break:break-all;letter-spacing:.5px}
.modal .key-box .exp{font-size:11px;color:#64748B;margin-top:8px}
.modal .btns{display:flex;gap:8px}
.modal button{flex:1;padding:12px;border:none;border-radius:9px;font-size:13.5px;
              font-weight:700;cursor:pointer;color:#fff;transition:.2s}
.modal .ok{background:#6366F1}.modal .ok:hover{background:#4F46E5}
.modal .close{background:#334155}.modal .close:hover{background:#475569}

/* Toast */
.toast{position:fixed;bottom:24px;right:24px;background:#10B981;color:#fff;padding:14px 22px;
       border-radius:11px;font-size:14px;font-weight:700;box-shadow:0 10px 30px rgba(0,0,0,.4);
       opacity:0;transform:translateY(20px);transition:.3s;pointer-events:none;z-index:200;
       max-width:340px}
.toast.show{opacity:1;transform:translateY(0)}
.toast.err{background:#EF4444}

@media(max-width:768px){
  .hdr h1{font-size:14px}
  .hdr a{padding:6px 10px;font-size:12px}
  .stat .n{font-size:22px}
  .stat .l{font-size:9.5px}
  .stat{padding:14px 10px}
  .wrap{padding:14px 10px}
  .tbl-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
  table{min-width:850px}
  th,td{padding:10px 8px;font-size:12px}
  .key{font-size:11px}
  .actions button{padding:5px 8px;font-size:10px}
  .gen input{width:100px}
  .gen button{padding:11px 16px;font-size:13px}
}
</style></head><body>

<!-- HEADER -->
<div class="hdr">
  <h1>🔐 License Admin Panel</h1>
  <div class="right">
    <a href="/logout">Logout</a>
  </div>
</div>

<div class="wrap">

  <!-- STATS -->
  <div class="stats">
    <div class="stat s-total"><div class="n n-tot">{{ stats.total }}</div><div class="l">Total Keys</div></div>
    <div class="stat s-activated"><div class="n n-actv">{{ stats.activated }}</div><div class="l">Activated</div></div>
    <div class="stat s-active"><div class="n n-act">{{ stats.active }}</div><div class="l">Activated</div></div>
    <div class="stat s-activated"><div class="n n-actv">{{ stats.live }}</div><div class="l">Live Now</div></div>
    <div class="stat s-expired"><div class="n n-exp">{{ stats.expired }}</div><div class="l">Expired</div></div>
    <div class="stat s-banned"><div class="n n-ban">{{ stats.banned }}</div><div class="l">Blocked</div></div>
  </div>

  <!-- GENERATE -->
  <div class="gen">
    <h2>⚡ Generate New License Key</h2>
    <div class="gen-row">
      <input type="text" id="customerName" maxlength="80" placeholder="Customer Name">
      <input type="number" id="days" value="30" min="1" max="3650" placeholder="Days">
      <button onclick="generateKey()">+ Generate Key</button>
      <button class="blue" onclick="location.reload()">⟳ Refresh</button>
    </div>
  </div>

  <!-- SEARCH / FILTER -->
  <div class="tools">
    <div class="search-box">
      <input type="text" id="search" placeholder="Search by key, HWID, PC name..." oninput="filterTable()">
    </div>
    <select id="filter" onchange="filterTable()">
      <option value="all">All Status</option>
      <option value="online">🟢 Online</option>
      <option value="offline">⚫ Offline</option>
      <option value="active">Active</option>
      <option value="pending">Not Activated</option>
      <option value="expired">Expired</option>
      <option value="banned">Blocked</option>
    </select>
    <span class="cnt" id="visibleCount"></span>
  </div>

  <!-- TABLE -->
  <div class="tbl-wrap">
    <table id="tbl">
      <thead><tr>
        <th>Customer</th>
        <th>License Key</th>
        <th>Status</th>
        <th>HWID</th>
        <th>PC Name</th>
        <th>Expires</th>
        <th>Last Seen</th>
        <th>Live</th>
        <th>Actions</th>
      </tr></thead>
      <tbody id="tbody">
      {% for k, v in keys %}
        <tr class="row" data-status="{{ v.status }}">
          <td class="pcname">{{ v.name or "Unnamed" }}</td>
          <td>
            <span class="key">{{ k }}</span>
            <button class="copy-btn" onclick="copyKey('{{ k }}')" title="Copy key">📋</button>
          </td>
          <td>
            {% if v.status == 'active' %}<span class="badge b-act">Active</span>
            {% elif v.status == 'pending' %}<span class="badge b-pen">Not Activated</span>
            {% elif v.status == 'expired' %}<span class="badge b-exp">Expired</span>
            {% elif v.status == 'banned' %}<span class="badge b-ban">Blocked</span>
            {% endif %}
          </td>
          <td class="mono">{{ v.hwid_short or '—' }}</td>
          <td class="pcname">{{ v.pc_name or '—' }}</td>
          <td>{{ v.expires_short or '—' }}</td>
          <td>{{ v.last_seen or '—' }}</td>
          <td class="live-cell">{% if v.online %}<span class="badge b-act">● ONLINE</span>{% else %}<span class="badge b-ban">● OFFLINE</span>{% endif %}</td>
          <td>
            <div class="actions">
              {% if v.hwid %}
                <button class="act-reset" onclick="rowAction('reset','{{ k }}')">Reset</button>
              {% endif %}
              {% if v.banned %}
                <button class="act-unban" onclick="rowAction('unban','{{ k }}')">Unban</button>
              {% else %}
                <button class="act-ban" onclick="rowAction('ban','{{ k }}')">Block</button>
              {% endif %}
              <button class="act-del" onclick="rowAction('delete','{{ k }}')">Del</button>
            </div>
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    {% if not keys %}
      <div class="empty">No license keys yet.<br><br>Click "Generate Key" to create one.</div>
    {% endif %}
  </div>

</div>

<!-- MODAL -->
<div class="modal-overlay" id="modal">
  <div class="modal">
    <h3>✅ License Key Generated</h3>
    <p>এই key টা কপি করে customer কে পাঠান:</p>
    <div class="key-box">
      <div class="k" id="newKey">—</div>
      <div class="exp" id="newExp">—</div>
    </div>
    <div class="btns">
      <button class="ok" onclick="copyNewKey()">📋 Copy Key</button>
      <button class="close" onclick="closeModal()">Close</button>
    </div>
  </div>
</div>

<div class="toast" id="toast">Done</div>

<script>
function toast(msg, err){
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (err ? ' err' : '');
  clearTimeout(t._tid);
  t._tid = setTimeout(()=>{ t.className = 'toast' + (err ? ' err' : ''); }, 2400);
}
function copyKey(k){
  navigator.clipboard.writeText(k)
    .then(()=>toast('✓ Key copied!'))
    .catch(()=>toast('Copy failed', true));
}
function copyNewKey(){
  const k = document.getElementById('newKey').textContent;
  navigator.clipboard.writeText(k)
    .then(()=>toast('✓ Key copied!'))
    .catch(()=>toast('Copy failed', true));
}
function closeModal(){
  document.getElementById('modal').classList.remove('show');
}
async function generateKey(){
  const days = parseInt(document.getElementById('days').value) || 30;
  const name = document.getElementById('customerName').value.trim();
  if(!name){ toast('Customer name required', true); return; }
  if(days < 1 || days > 3650){ toast('Days must be 1-3650', true); return; }
  try{
    const r = await fetch('/admin/api/new', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({days, name})
    });
    const res = await r.json();
    if(res.ok){
      document.getElementById('newKey').textContent = res.key;
      document.getElementById('newExp').textContent = 'Expires: ' + res.expires;
      document.getElementById('modal').classList.add('show');
      toast('✓ Key generated!');
      setTimeout(()=>location.reload(), 5000);
    } else {
      toast(res.msg || 'Failed', true);
    }
  }catch(e){ toast('Error: '+e, true); }
}
async function rowAction(action, key){
  const label = {reset:'Reset HWID', ban:'Block', unban:'Unban', delete:'Delete'}[action];
  if(!confirm(label + ' — ' + key + ' ?')) return;
  try{
    const r = await fetch('/admin/api/' + action, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({key})
    });
    const res = await r.json();
    if(res.ok){
      toast('✓ ' + label + ' done');
      setTimeout(()=>location.reload(), 700);
    } else {
      toast(res.msg || 'Failed', true);
    }
  }catch(e){ toast('Error: '+e, true); }
}
function filterTable(){
  const q = document.getElementById('search').value.toLowerCase().trim();
  const f = document.getElementById('filter').value;
  let visible = 0;
  document.querySelectorAll('#tbody tr.row').forEach(tr=>{
    const txt = tr.textContent.toLowerCase();
    const st  = tr.dataset.status;
    const matchQ = !q || txt.includes(q);
    const online = tr.querySelector('.live-cell')?.textContent.toLowerCase().includes('online');
     const matchF = f === 'all' || st === f || (f === 'online' && online) || (f === 'offline' && !online);
    const show = matchQ && matchF;
    tr.style.display = show ? '' : 'none';
    if(show) visible++;
  });
  document.getElementById('visibleCount').textContent = visible + ' shown';
}
document.addEventListener('DOMContentLoaded', filterTable);
setInterval(()=>location.reload(), 15000);
document.getElementById('search').addEventListener('keydown', e=>{
  if(e.key === 'Escape'){ e.target.value=''; filterTable(); }
});
</script>
</body></html>"""


@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login_page"))
    return redirect(url_for("admin_panel"))


@app.route("/admin")
@login_required
def admin_panel():
    db = load_db()
    now = datetime.now()

    keys = []
    stats = {"total": 0, "active": 0, "expired": 0, "banned": 0, "activated": 0, "live": 0}

    for k, v in db.items():
        exp = v.get("expires")
        banned = bool(v.get("banned"))
        hwid = v.get("hwid")
        is_exp = _is_expired(v)

        online = _is_online(v)
        if online:
            stats["live"] += 1

        if banned:
            status = "banned"
            stats["banned"] += 1
        elif is_exp:
            status = "expired"
            stats["expired"] += 1
        elif hwid:
            status = "active"
            stats["active"] += 1
            stats["activated"] += 1
        else:
            status = "pending"

        exp_short = ""
        if exp:
            try:
                dt = datetime.fromisoformat(exp)
                days_left = (dt - now).days
                exp_short = dt.strftime("%d %b %Y")
                if days_left >= 0:
                    exp_short += f" ({days_left}d)"
                else:
                    exp_short += " (past)"
            except Exception:
                exp_short = str(exp)[:10]

        last_seen = ""
        if v.get("last_seen"):
            try:
                dt = datetime.fromisoformat(v["last_seen"])
                diff = (now - dt).total_seconds()
                if diff < 60: last_seen = "just now"
                elif diff < 3600: last_seen = f"{int(diff/60)}m ago"
                elif diff < 86400: last_seen = f"{int(diff/3600)}h ago"
                elif diff < 604800: last_seen = f"{int(diff/86400)}d ago"
                else: last_seen = dt.strftime("%d %b")
            except Exception:
                last_seen = str(v["last_seen"])[:16]

        keys.append((k, {
            "status": status,
            "name": v.get("name", ""),
            "online": online,
            "hwid": hwid,
            "hwid_short": (hwid[:8] + "…" + hwid[-6:]) if hwid and len(hwid) > 16 else (hwid or ""),
            "pc_name": v.get("pc_name", ""),
            "expires_short": exp_short,
            "last_seen": last_seen,
            "banned": banned,
        }))

    stats["total"] = len(db)
    keys.sort(key=lambda x: db[x[0]].get("created_at", ""), reverse=True)

    return render_template_string(PANEL_HTML, keys=keys, stats=stats)


# ═══════════════════════════════════════════════════════════════
#  ADMIN API
# ═══════════════════════════════════════════════════════════════
@app.route("/admin/api/new", methods=["POST"])
@login_required
def api_new():
    data = request.get_json(force=True) or {}
    days = int(data.get("days", 30))
    name = (data.get("name") or "").strip()[:80]
    if not name:
        return jsonify({"ok": False, "msg": "Customer name required"})

    alphabet = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(alphabet) for _ in range(5)) for _ in range(4)]
    new_key = "FBLT-" + "-".join(parts)

    expires = (datetime.now() + timedelta(days=days)).isoformat()

    db = load_db()
    db[new_key] = {
        "name": name,
        "hwid": None,
        "expires": expires,
        "banned": False,
        "created_at": datetime.now().isoformat(),
    }
    save_db(db)
    return jsonify({"ok": True, "key": new_key, "expires": expires, "name": name})


@app.route("/admin/api/name", methods=["POST"])
@login_required
def api_name():
    data = request.get_json(force=True) or {}
    key = (data.get("key") or "").strip().upper()
    name = (data.get("name") or "").strip()[:80]
    db = load_db()
    if key in db and name:
        db[key]["name"] = name
        save_db(db)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "msg": "Key or name invalid"})


@app.route("/admin/api/reset", methods=["POST"])
@login_required
def api_reset():
    data = request.get_json(force=True) or {}
    key = (data.get("key") or "").strip().upper()
    db = load_db()
    if key in db:
        db[key]["hwid"] = None
        db[key]["pc_name"] = ""
        db[key]["reset_at"] = datetime.now().isoformat()
        save_db(db)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "msg": "Not found"})


@app.route("/admin/api/ban", methods=["POST"])
@login_required
def api_ban():
    data = request.get_json(force=True) or {}
    key = (data.get("key") or "").strip().upper()
    db = load_db()
    if key in db:
        db[key]["banned"] = True
        save_db(db)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "msg": "Not found"})


@app.route("/admin/api/unban", methods=["POST"])
@login_required
def api_unban():
    data = request.get_json(force=True) or {}
    key = (data.get("key") or "").strip().upper()
    db = load_db()
    if key in db:
        db[key]["banned"] = False
        save_db(db)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "msg": "Not found"})


@app.route("/admin/api/delete", methods=["POST"])
@login_required
def api_delete():
    data = request.get_json(force=True) or {}
    key = (data.get("key") or "").strip().upper()
    db = load_db()
    if key in db:
        del db[key]
        save_db(db)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "msg": "Not found"})


# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
