# license_server.py
# ═══════════════════════════════════════════════════════════════
#  FB Lite Auto Tool — License Server
#  Deploy on: Render / VPS / PythonAnywhere
#  Run: python license_server.py
# ═══════════════════════════════════════════════════════════════
from flask import Flask, request, jsonify
import json, os, secrets, string
from datetime import datetime, timedelta

app = Flask(__name__)
DB_FILE = "licenses.json"

# ═══════════════════════════════════════════════════════════════
#  ⚠️  CHANGE THIS ADMIN SECRET BEFORE DEPLOYING!
#  এই লাইনটা নিজের একটা শক্তিশালী secret দিয়ে পরিবর্তন করুন
# ═══════════════════════════════════════════════════════════════
ADMIN_SECRET = "Rubel2026@"
# ═══════════════════════════════════════════════════════════════


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


def _is_expired(entry):
    exp = entry.get("expires")
    if not exp:
        return False
    try:
        return datetime.now() > datetime.fromisoformat(exp)
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
#  ACTIVATE  (first time binds HWID to key)
# ═══════════════════════════════════════════════════════════════
@app.route("/activate", methods=["POST"])
def activate():
    data = request.get_json(force=True) or {}
    key  = (data.get("key") or "").strip().upper()
    hwid = (data.get("hwid") or "").strip()

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
        entry["activated_at"] = datetime.now().isoformat()
        db[key] = entry
        save_db(db)
        return jsonify({
            "ok": True,
            "msg": "Activated successfully",
            "expires": entry.get("expires"),
        })

    if bound == hwid:
        return jsonify({
            "ok": True,
            "msg": "OK",
            "expires": entry.get("expires"),
        })

    return jsonify({
        "ok": False,
        "msg": "This license is already activated on another system! "
               "Contact admin to reset.",
    })


# ═══════════════════════════════════════════════════════════════
#  HEARTBEAT  (every 5 min)
# ═══════════════════════════════════════════════════════════════
@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    data = request.get_json(force=True) or {}
    key  = (data.get("key") or "").strip().upper()
    hwid = (data.get("hwid") or "").strip()

    db = load_db()
    entry = db.get(key)

    if not entry:
        return jsonify({"ok": False, "msg": "License not found"})
    if entry.get("hwid") != hwid:
        return jsonify({"ok": False, "msg": "HWID mismatch"})
    if entry.get("banned"):
        return jsonify({"ok": False, "msg": "License banned"})
    if _is_expired(entry):
        return jsonify({"ok": False, "msg": "License expired"})

    return jsonify({"ok": True, "expires": entry.get("expires")})


# ═══════════════════════════════════════════════════════════════
#  ADMIN — Generate new key
#  curl -X POST http://SERVER/admin/new -H "Content-Type: application/json"
#       -d "{\"admin\":\"SECRET\",\"days\":30}"
# ═══════════════════════════════════════════════════════════════
@app.route("/admin/new", methods=["POST"])
def admin_new():
    data = request.get_json(force=True) or {}
    if data.get("admin") != ADMIN_SECRET:
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401

    alphabet = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(alphabet) for _ in range(5)) for _ in range(4)]
    new_key = "FBLT-" + "-".join(parts)

    days = int(data.get("days", 30))
    expires = (datetime.now() + timedelta(days=days)).isoformat()

    db = load_db()
    db[new_key] = {
        "hwid": None,
        "expires": expires,
        "banned": False,
        "created_at": datetime.now().isoformat(),
    }
    save_db(db)
    return jsonify({"ok": True, "key": new_key, "expires": expires})


# ═══════════════════════════════════════════════════════════════
#  ADMIN — Reset HWID (transfer license to new PC)
# ═══════════════════════════════════════════════════════════════
@app.route("/admin/reset", methods=["POST"])
def admin_reset():
    data = request.get_json(force=True) or {}
    if data.get("admin") != ADMIN_SECRET:
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401

    key = (data.get("key") or "").strip().upper()
    db = load_db()
    if key in db:
        db[key]["hwid"] = None
        db[key]["reset_at"] = datetime.now().isoformat()
        save_db(db)
        return jsonify({"ok": True, "msg": "HWID reset — can be activated on new PC"})
    return jsonify({"ok": False, "msg": "Key not found"})


# ═══════════════════════════════════════════════════════════════
#  ADMIN — Ban / Unban
# ═══════════════════════════════════════════════════════════════
@app.route("/admin/ban", methods=["POST"])
def admin_ban():
    data = request.get_json(force=True) or {}
    if data.get("admin") != ADMIN_SECRET:
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    key = (data.get("key") or "").strip().upper()
    ban = bool(data.get("ban", True))
    db = load_db()
    if key in db:
        db[key]["banned"] = ban
        save_db(db)
        return jsonify({"ok": True, "banned": ban})
    return jsonify({"ok": False, "msg": "Key not found"})


# ═══════════════════════════════════════════════════════════════
#  ADMIN — List all keys
# ═══════════════════════════════════════════════════════════════
@app.route("/admin/list", methods=["POST"])
def admin_list():
    data = request.get_json(force=True) or {}
    if data.get("admin") != ADMIN_SECRET:
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    return jsonify({"ok": True, "keys": load_db()})


# ═══════════════════════════════════════════════════════════════
@app.route("/", methods=["GET"])
def index():
    return jsonify({"ok": True, "service": "FB Lite License Server", "status": "online"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)