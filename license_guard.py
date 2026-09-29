# license_guard.py
# ═══════════════════════════════════════════════════════════════
#  FB Lite Auto Tool — License Guard (Client Side)
#  Place this in the SAME folder as the main tool.
# ═══════════════════════════════════════════════════════════════
import os, sys, json, time, hashlib, subprocess, threading
import tkinter as tk
from tkinter import messagebox
import urllib.request

# ═══════════════════════════════════════════════════════════════
#  ⚠️  CHANGE THIS TO YOUR DEPLOYED SERVER URL
# ═══════════════════════════════════════════════════════════════
LICENSE_SERVER = "https://YOUR-SERVER-URL.onrender.com"
# ═══════════════════════════════════════════════════════════════

LICENSE_FILE = os.path.join(os.path.expanduser("~"), ".fblt_license.dat")
HEARTBEAT_INTERVAL = 300
OFFLINE_GRACE_DAYS = 3


def get_hwid():
    raw = ""
    try:
        out = subprocess.check_output(
            "wmic csproduct get uuid",
            shell=True, stderr=subprocess.DEVNULL,
            creationflags=0x08000000
        ).decode(errors="ignore")
        for line in out.splitlines():
            line = line.strip()
            if line and "UUID" not in line.upper():
                raw = line
                break
    except Exception:
        pass

    if not raw:
        try:
            import uuid
            raw = str(uuid.getnode())
        except Exception:
            raw = "unknown"

    return hashlib.sha256(raw.encode()).hexdigest()[:32].upper()


def _post(url, payload, timeout=15):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _load_saved():
    try:
        with open(LICENSE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_local(key, hwid, expires=None):
    try:
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "key": key,
                "hwid": hwid,
                "expires": expires,
                "saved_at": time.time(),
                "last_ok": time.time(),
            }, f)
    except Exception:
        pass


def _touch_last_ok():
    try:
        data = _load_saved() or {}
        data["last_ok"] = time.time()
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def _clear_local():
    try:
        os.remove(LICENSE_FILE)
    except Exception:
        pass


def _try_silent_activate():
    saved = _load_saved()
    if not saved:
        return False, "No saved license"

    hwid = get_hwid()

    if saved.get("hwid") != hwid:
        _clear_local()
        return False, "HWID mismatch"

    key = saved.get("key")
    if not key:
        _clear_local()
        return False, "Corrupt license file"

    try:
        res = _post(f"{LICENSE_SERVER}/activate",
                    {"key": key, "hwid": hwid}, timeout=15)
        if res.get("ok"):
            _save_local(key, hwid, res.get("expires"))
            _touch_last_ok()
            return True, key
        _clear_local()
        return False, res.get("msg", "Invalid license")
    except Exception:
        last_ok = saved.get("last_ok", saved.get("saved_at", 0))
        age_days = (time.time() - last_ok) / 86400.0
        if age_days <= OFFLINE_GRACE_DAYS:
            return True, key
        _clear_local()
        return False, "Server unreachable & offline grace expired"


class LicenseDialog:
    def __init__(self, root):
        self.root = root
        self.key_var = tk.StringVar()
        self.hwid = get_hwid()
        self.success = False

        root.title("License Activation")
        root.configure(bg="#0F172A")
        root.resizable(False, False)

        w, h = 540, 360
        root.update_idletasks()
        x = (root.winfo_screenwidth() - w) // 2
        y = (root.winfo_screenheight() - h) // 2
        root.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(root, text="FB Lite Auto Tool Pro",
                 bg="#0F172A", fg="#6366F1",
                 font=("Segoe UI Semibold", 18, "bold")).pack(pady=(26, 2))
        tk.Label(root, text="License Activation Required",
                 bg="#0F172A", fg="#94A3B8",
                 font=("Segoe UI", 10)).pack()

        card = tk.Frame(root, bg="#1E293B")
        card.pack(fill="x", padx=30, pady=18)

        tk.Label(card, text="License Key:",
                 bg="#1E293B", fg="#CBD5E1",
                 font=("Segoe UI Semibold", 10)
                 ).pack(anchor="w", padx=14, pady=(14, 6))

        entry = tk.Entry(card, textvariable=self.key_var,
                         bg="#0F172A", fg="#34D399",
                         insertbackground="#34D399",
                         font=("Consolas", 12, "bold"),
                         bd=0, highlightthickness=1,
                         highlightbackground="#334155",
                         highlightcolor="#6366F1")
        entry.pack(fill="x", padx=14, ipady=8)
        entry.focus_set()
        entry.bind("<Return>", lambda e: self.activate())

        tk.Label(card, text=f"System ID:  {self.hwid}",
                 bg="#1E293B", fg="#64748B",
                 font=("Consolas", 8)
                 ).pack(anchor="w", padx=14, pady=(10, 14))

        btn = tk.Button(root, text="Activate",
                        bg="#6366F1", fg="white",
                        font=("Segoe UI Semibold", 11, "bold"),
                        bd=0, padx=34, pady=10, cursor="hand2",
                        activebackground="#4F46E5",
                        activeforeground="white",
                        command=self.activate)
        btn.pack(pady=4)

        self.status = tk.Label(root, text="",
                               bg="#0F172A", fg="#94A3B8",
                               font=("Segoe UI", 9),
                               wraplength=480, justify="center")
        self.status.pack(pady=8, padx=20)

        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def activate(self):
        key = self.key_var.get().strip().upper()
        if not key:
            self.status.config(text="Enter license key", fg="#F59E0B")
            return

        self.status.config(text="Contacting server...", fg="#94A3B8")
        self.root.update()

        try:
            res = _post(f"{LICENSE_SERVER}/activate",
                        {"key": key, "hwid": self.hwid}, timeout=20)
        except Exception as e:
            self.status.config(text=f"Server unreachable: {e}", fg="#EF4444")
            return

        if res.get("ok"):
            _save_local(key, self.hwid, res.get("expires"))
            _touch_last_ok()
            self.status.config(text="Activated! Starting tool...",
                               fg="#10B981")
            self.success = True
            self.root.after(700, self.root.destroy)
        else:
            self.status.config(text=f"✗ {res.get('msg', 'Failed')}",
                               fg="#EF4444")

    def _on_close(self):
        self.success = False
        self.root.destroy()


def _start_heartbeat(key):
    hwid = get_hwid()

    def loop():
        while True:
            time.sleep(HEARTBEAT_INTERVAL)
            try:
                res = _post(f"{LICENSE_SERVER}/heartbeat",
                            {"key": key, "hwid": hwid}, timeout=15)
                if not res.get("ok"):
                    _clear_local()
                    try:
                        r = tk.Tk()
                        r.withdraw()
                        messagebox.showerror(
                            "License Error",
                            f"License invalid: {res.get('msg')}\n\nTool will close.")
                        r.destroy()
                    except Exception:
                        pass
                    os._exit(1)
                else:
                    _touch_last_ok()
            except Exception:
                pass

    threading.Thread(target=loop, daemon=True).start()


def check_license():
    ok, info = _try_silent_activate()
    if ok:
        _start_heartbeat(info)
        return True

    lic_root = tk.Tk()
    dlg = LicenseDialog(lic_root)
    lic_root.mainloop()

    if not dlg.success:
        sys.exit(0)

    _start_heartbeat(dlg.key_var.get().strip().upper())
    return True