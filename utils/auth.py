"""
utils/auth.py
Manajemen autentikasi: login, session, password hashing
"""
import bcrypt
import streamlit as st
from datetime import datetime
from config.database import execute_query


# ── Password ────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Login ────────────────────────────────────────────────────
def login_user(username: str, password: str):
    """
    Verifikasi kredensial.
    Kembalikan dict user jika berhasil, None jika gagal.
    """
    rows = execute_query(
        "SELECT * FROM users WHERE username=%s AND is_active=1 LIMIT 1",
        (username,),
        fetch=True
    )
    if not rows:
        return None
    user = rows[0]
    if not check_password(password, user["password"]):
        return None
    # Update last_login
    execute_query(
        "UPDATE users SET last_login=%s WHERE id=%s",
        (datetime.now(), user["id"])
    )
    return user


# ── Session ──────────────────────────────────────────────────
def init_session():
    defaults = {
        "logged_in": False,
        "user": None,
        "role": None,
        "current_page": "Dashboard",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def set_session(user: dict):
    st.session_state.logged_in = True
    st.session_state.user = user
    st.session_state.role = user["role"]


def clear_session():
    for key in ["logged_in", "user", "role", "current_page"]:
        st.session_state[key] = None if key not in ("logged_in",) else False


def is_logged_in() -> bool:
    return st.session_state.get("logged_in", False)


def require_login():
    """Guard: redirect ke login jika belum login."""
    if not is_logged_in():
        st.warning("⚠️ Silakan login terlebih dahulu.")
        st.stop()


def require_admin():
    """Guard: hanya admin yang boleh mengakses."""
    require_login()
    if st.session_state.get("role") != "admin":
        st.error("🚫 Halaman ini hanya untuk Admin.")
        st.stop()


# ── Activity Log ─────────────────────────────────────────────
def log_activity(user_id: int, action: str, detail: str = ""):
    try:
        execute_query(
            "INSERT INTO activity_log (user_id, action, detail) VALUES (%s,%s,%s)",
            (user_id, action, detail)
        )
    except Exception:
        pass  # log gagal tidak boleh crash aplikasi
