"""
app.py
Entry point utama aplikasi NeuroFuzzy Skincare Overclaim Detector
Jalankan dengan: streamlit run app.py
"""
import streamlit as st

# ── Konfigurasi halaman (HARUS di baris pertama Streamlit) ────
st.set_page_config(
    page_title="NeuroFuzzy Skincare Overclaim Detector",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Import setelah set_page_config ────────────────────────────
from utils.auth import init_session, is_logged_in, clear_session, log_activity
from utils.ui_helpers import inject_css, PINK_PRIMARY, PINK_DARK
from pages.login import render_login
from pages.dashboard import render_dashboard
from pages.data_iklan import render_data_iklan
from pages.proses_deteksi import render_proses_deteksi
from pages.hasil_deteksi import render_hasil_deteksi


# ── Inisialisasi session ───────────────────────────────────────
init_session()

# ══════════════════════════════════════════════════════════════
#  BELUM LOGIN  →  Tampilkan halaman login
# ══════════════════════════════════════════════════════════════
if not is_logged_in():
    render_login()
    st.stop()


# ══════════════════════════════════════════════════════════════
#  SUDAH LOGIN  →  Tampilkan sidebar + navigasi
# ══════════════════════════════════════════════════════════════
inject_css()
user = st.session_state.user
role = st.session_state.role


# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    # Logo & judul
    st.markdown("""
    <div class="sidebar-logo">
        <div style="font-size:2.2rem">🧬</div>
        <div class="app-title">NeuroFuzzy<br>Overclaim Detector</div>
        <div class="app-subtitle">Skincare E-Commerce Analysis</div>
    </div>
    """, unsafe_allow_html=True)

    # Info user
    # Info user
    if user is not None:
        st.markdown(f"""
        <div style="padding:0.75rem 1rem;margin-bottom:0.5rem;
                    background:rgba(255,255,255,0.12);border-radius:10px;
                    font-size:0.85rem">
            <div style="font-weight:700">{user.get('full_name', 'Nama Tidak Ditemukan')}</div>
            <div style="opacity:0.75;font-size:0.75rem">
                {'👑 Administrator' if role=='admin' else '👤 Pengguna'} &nbsp;|&nbsp;
                @{user.get('username', 'user')}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Data pengguna gagal dimuat. Cek koneksi database.")

    st.markdown("---")

    # ── Menu Navigasi ─────────────────────────────────────
    NAV_ITEMS = [
        ("🏠", "Dashboard",       True),           # semua role
        ("📦", "Data Iklan",      role == "admin"),
        ("⚙️", "Proses Deteksi",  role == "admin"),
        ("📊", "Hasil Deteksi",   True),
    ]

    current = st.session_state.get("current_page", "Dashboard")

    for icon, page_name, visible in NAV_ITEMS:
        if not visible:
            continue
        is_active = (current == page_name)
        # Tambahkan class active via container
        btn_key = f"nav_{page_name}"
        if is_active:
            st.markdown('<div class="nav-active">', unsafe_allow_html=True)
        if st.button(f"{icon}  {page_name}", key=btn_key,
                     use_container_width=True):
            st.session_state.current_page = page_name
            st.rerun()
        if is_active:
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Tombol Logout ────────────────────────────────────
    if st.button("🚪  Logout", use_container_width=True, key="btn_logout"):
        log_activity(user["id"], "LOGOUT")
        clear_session()
        st.rerun()



# ══════════════════════════════════════════════════════════════
#  ROUTING — render halaman sesuai navigasi
# ══════════════════════════════════════════════════════════════
page = st.session_state.get("current_page", "Dashboard")

if page == "Dashboard":
    render_dashboard()

elif page == "Data Iklan":
    if role == "admin":
        render_data_iklan()
    else:
        st.error("🚫 Akses ditolak. Halaman ini hanya untuk Admin.")

elif page == "Proses Deteksi":
    if role == "admin":
        render_proses_deteksi()
    else:
        st.error("🚫 Akses ditolak. Halaman ini hanya untuk Admin.")

elif page == "Hasil Deteksi":
    render_hasil_deteksi()

else:
    render_dashboard()
