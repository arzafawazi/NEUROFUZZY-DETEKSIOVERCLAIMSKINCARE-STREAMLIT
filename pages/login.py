"""
pages/login.py
Halaman Login — Admin & User
"""
import streamlit as st
from utils.auth import login_user, set_session, log_activity
from utils.ui_helpers import inject_css, show_alert


def render_login():
    inject_css()

    # Centered layout
    col1, col2, col3 = st.columns([1, 1.6, 1])
    with col2:
        st.markdown("""
        <div style="height:3vh"></div>
        <div class="login-container">
            <div class="login-logo">
                <div class="logo-icon">🧬</div>
                <h1>IMPLEMENTASI NEUROFUZZY<br>DETEKSI OVERCLAIM SKINCARE</h1>
                <p style="color:#9E9E9E;font-size:0.8rem;margin-top:0.3rem">
                    Platform E-Commerce Analysis System
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="" style="margin-top:-1rem">', 
                        unsafe_allow_html=True)

            tab_admin, tab_user = st.tabs(["🔐 Admin", "👤 User"])

            with tab_admin:
                _render_form("admin")

            with tab_user:
                _render_form("user")

            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
        <div style="text-align:center;margin-top:1rem;color:#9E9E9E;font-size:0.75rem">
            © 2024 Neurofuzzy Skincare Overclaim Detector &nbsp;|&nbsp; v1.0.0
        </div>
        """, unsafe_allow_html=True)


def _render_form(role: str):
    prefix = role
    with st.form(key=f"form_{prefix}", clear_on_submit=False):
        st.markdown(f"""
        <p style="font-weight:600;color:#AD1457;margin-bottom:1rem">
            {'👑 Login sebagai Administrator' if role=='admin' else '🙋 Login sebagai Pengguna'}
        </p>
        """, unsafe_allow_html=True)

        username = st.text_input("Username", placeholder="Masukkan username",
                                  key=f"un_{prefix}")
        password = st.text_input("Password", type="password",
                                  placeholder="Masukkan password",
                                  key=f"pw_{prefix}")

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button(
            f"🔑 Login {'Admin' if role=='admin' else 'User'}",
            use_container_width=True,
            type="primary"
        )

        if submitted:
            if not username or not password:
                show_alert("Username dan password wajib diisi.", "warning")
                return

            with st.spinner("Memverifikasi..."):
                user = login_user(username.strip(), password)

            if user is None:
                show_alert("Username atau password salah.", "danger")
                return

            if user["role"] != role:
                show_alert(f"Akun ini bukan role '{role}'.", "danger")
                return

            set_session(user)
            log_activity(user["id"], "LOGIN", f"Role: {role}")
            st.success(f"✅ Selamat datang, {user['full_name']}!")
            st.rerun()

        # Demo hint
        st.markdown(f"""
        <p style="font-size:0.75rem;color:#BDBDBD;margin-top:0.8rem;text-align:center">
            Demo → {'admin / admin123' if role=='admin' else 'user1 / user123'}
        </p>
        """, unsafe_allow_html=True)
