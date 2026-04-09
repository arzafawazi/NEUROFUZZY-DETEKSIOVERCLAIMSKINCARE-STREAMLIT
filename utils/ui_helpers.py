"""
utils/ui_helpers.py
CSS tema pink, komponen UI bersama, Bootstrap injection
"""
import streamlit as st

# ─── Palet Warna ────────────────────────────────────────────
PINK_PRIMARY   = "#E91E8C"
PINK_LIGHT     = "#F8BBD9"
PINK_DARK      = "#AD1457"
PINK_SOFT      = "#FCE4EC"
WHITE          = "#FFFFFF"
GRAY_LIGHT     = "#F5F5F5"
GRAY_MID       = "#9E9E9E"
GRAY_DARK      = "#424242"
ACCENT_PURPLE  = "#9C27B0"
ACCENT_TEAL    = "#00BCD4"
SUCCESS        = "#4CAF50"
WARNING        = "#FF9800"
DANGER         = "#F44336"
INFO           = "#2196F3"


GLOBAL_CSS = f"""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

/* ── Reset & Base ── */
html, body, [class*="css"] {{
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: {GRAY_DARK};
}}

/* ── Hide default Streamlit elements ── */
#MainMenu, footer, header {{ visibility: hidden; }}
.stDeployButton {{ display: none !important; }}
section[data-testid="stSidebar"] > div:first-child {{ padding-top: 0 !important; }}

/* ── App Background ── */
.stApp {{
    background: linear-gradient(135deg, {PINK_SOFT} 0%, #f0f4ff 100%);
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {PINK_DARK} 0%, {PINK_PRIMARY} 60%, {ACCENT_PURPLE} 100%) !important;
    box-shadow: 4px 0 20px rgba(233,30,140,0.25);
}}
[data-testid="stSidebar"] * {{
    color: {WHITE} !important;
}}
[data-testid="stSidebar"] .stButton > button {{
    width: 100%;
    background: rgba(255,255,255,0.15) !important;
    color: {WHITE} !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    border-radius: 10px !important;
    padding: 0.6rem 1rem !important;
    font-weight: 600 !important;
    margin-bottom: 0.3rem !important;
    transition: all 0.25s ease !important;
    text-align: left !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255,255,255,0.3) !important;
    transform: translateX(4px) !important;
}}

/* ── Active nav button ── */
.nav-active > button {{
    background: rgba(255,255,255,0.35) !important;
    border-left: 4px solid {WHITE} !important;
}}

/* ── Cards ── */
.card {{
    background: {WHITE};
    border-radius: 16px;
    padding: 1.5rem;
    box-shadow: 0 2px 20px rgba(233,30,140,0.10);
    border: 1px solid rgba(233,30,140,0.08);
    margin-bottom: 1.2rem;
    transition: box-shadow 0.3s ease;
}}
.card:hover {{
    box-shadow: 0 6px 30px rgba(233,30,140,0.18);
}}

/* ── Stat Cards ── */
.stat-card {{
    background: linear-gradient(135deg, {PINK_PRIMARY}, {PINK_DARK});
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    color: {WHITE};
    text-align: center;
    box-shadow: 0 4px 20px rgba(233,30,140,0.3);
}}
.stat-card .stat-number {{
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: -1px;
    font-family: 'Space Grotesk', sans-serif;
}}
.stat-card .stat-label {{
    font-size: 0.82rem;
    opacity: 0.85;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.stat-card-teal {{
    background: linear-gradient(135deg, {ACCENT_TEAL}, #006064);
}}
.stat-card-purple {{
    background: linear-gradient(135deg, {ACCENT_PURPLE}, #4a148c);
}}
.stat-card-orange {{
    background: linear-gradient(135deg, {WARNING}, #e65100);
}}

/* ── Page Title ── */
.page-title {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.9rem;
    font-weight: 700;
    color: {PINK_DARK};
    margin-bottom: 0.2rem;
}}
.page-subtitle {{
    color: {GRAY_MID};
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
}}

/* ── Welcome Box ── */
.welcome-box {{
    background: linear-gradient(135deg, {PINK_PRIMARY} 0%, {ACCENT_PURPLE} 100%);
    border-radius: 20px;
    padding: 2.5rem;
    color: {WHITE};
    text-align: center;
    box-shadow: 0 8px 40px rgba(233,30,140,0.3);
    position: relative;
    overflow: hidden;
}}
.welcome-box::before {{
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 300px; height: 300px;
    background: rgba(255,255,255,0.08);
    border-radius: 50%;
}}
.welcome-box h2 {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
}}
.welcome-box p {{ opacity: 0.9; }}

/* ── Badge / Chip ── */
.badge {{
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
}}
.badge-success  {{ background:#E8F5E9; color:#2E7D32; }}
.badge-warning  {{ background:#FFF3E0; color:#E65100; }}
.badge-danger   {{ background:#FFEBEE; color:#C62828; }}
.badge-info     {{ background:#E3F2FD; color:#1565C0; }}
.badge-neutral  {{ background:#F5F5F5; color:#616161; }}

/* ── Buttons ── */
.stButton > button {{
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}}
.btn-primary {{
    background: linear-gradient(135deg, {PINK_PRIMARY}, {PINK_DARK}) !important;
    color: {WHITE} !important;
    border: none !important;
}}
.btn-primary:hover {{
    box-shadow: 0 4px 15px rgba(233,30,140,0.4) !important;
    transform: translateY(-1px) !important;
}}

/* ── Input Fields ── */
.stTextInput input, .stSelectbox select, .stTextArea textarea {{
    border-radius: 10px !important;
    border: 1.5px solid rgba(233,30,140,0.25) !important;
    transition: border 0.2s ease !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{
    border-color: {PINK_PRIMARY} !important;
    box-shadow: 0 0 0 3px rgba(233,30,140,0.12) !important;
}}

/* ── DataTable ── */
.dataframe {{
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid rgba(233,30,140,0.1) !important;
}}
.dataframe thead tr th {{
    background: {PINK_SOFT} !important;
    color: {PINK_DARK} !important;
    font-weight: 700 !important;
}}

/* ── Log Box ── */
.log-box {{
    background: #1a1a2e;
    border-radius: 12px;
    padding: 1.2rem;
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    color: #00ff88;
    max-height: 350px;
    overflow-y: auto;
    border: 1px solid rgba(0,255,136,0.2);
}}
.log-box .log-info  {{ color: #64b5f6; }}
.log-box .log-warn  {{ color: #ffcc02; }}
.log-box .log-error {{ color: #ef5350; }}
.log-box .log-ok    {{ color: #69f0ae; }}

/* ── Divider ── */
.pink-divider {{
    border: none;
    height: 2px;
    background: linear-gradient(90deg, {PINK_PRIMARY}, transparent);
    margin: 1rem 0;
    border-radius: 2px;
}}

/* ── Login Page ── */
.login-container {{
    max-width: 420px;
    margin: 0 auto;
    padding: 2.5rem;
    background: {WHITE};
    border-radius: 24px;
    box-shadow: 0 20px 60px rgba(233,30,140,0.2);
    border: 1px solid rgba(233,30,140,0.12);
}}
.login-logo {{
    text-align: center;
    margin-bottom: 1.5rem;
}}
.login-logo .logo-icon {{
    font-size: 3rem;
    background: linear-gradient(135deg, {PINK_PRIMARY}, {ACCENT_PURPLE});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}
.login-logo h1 {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: {PINK_DARK};
    margin-top: 0.5rem;
    line-height: 1.3;
}}

/* ── Sidebar logo area ── */
.sidebar-logo {{
    text-align: center;
    padding: 1.5rem 1rem 1rem;
    border-bottom: 1px solid rgba(255,255,255,0.2);
    margin-bottom: 1rem;
}}
.sidebar-logo .app-title {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.95rem;
    font-weight: 700;
    line-height: 1.3;
    color: white;
}}
.sidebar-logo .app-subtitle {{
    font-size: 0.72rem;
    opacity: 0.75;
    margin-top: 0.2rem;
}}

/* ── Progress bar ── */
.stProgress > div > div > div {{
    background: linear-gradient(90deg, {PINK_PRIMARY}, {ACCENT_PURPLE}) !important;
    border-radius: 10px !important;
}}

/* ── Alerts ── */
.alert {{
    border-radius: 12px;
    padding: 1rem 1.25rem;
    font-weight: 500;
    border-left: 4px solid;
    margin-bottom: 1rem;
}}
.alert-success {{ background:#E8F5E9; border-color:{SUCCESS}; color:#1B5E20; }}
.alert-warning {{ background:#FFF3E0; border-color:{WARNING}; color:#E65100; }}
.alert-danger  {{ background:#FFEBEE; border-color:{DANGER};  color:#B71C1C; }}
.alert-info    {{ background:#E3F2FD; border-color:{INFO};    color:#0D47A1; }}

/* ── Responsive grid ── */
@media (max-width: 768px) {{
    .stat-card .stat-number {{ font-size: 1.8rem; }}
    .page-title {{ font-size: 1.4rem; }}
    .welcome-box h2 {{ font-size: 1.4rem; }}
}}
</style>
"""

BOOTSTRAP_CDN = """
<link rel="stylesheet" 
  href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
<link rel="stylesheet"
  href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
"""


def inject_css():
    st.markdown(BOOTSTRAP_CDN + GLOBAL_CSS, unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str = "", icon: str = ""):
    st.markdown(f"""
    <div class="page-title">{icon} {title}</div>
    <div class="page-subtitle">{subtitle}</div>
    <hr class="pink-divider">
    """, unsafe_allow_html=True)


def render_metric_card(label: str, value, style: str = "", icon: str = ""):
    style_class = f"stat-card-{style}" if style else ""
    st.markdown(f"""
    <div class="stat-card {style_class}">
        <div style="font-size:1.8rem;margin-bottom:0.3rem">{icon}</div>
        <div class="stat-number">{value}</div>
        <div class="stat-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def badge_overclaim(kategori: str) -> str:
    mapping = {
        "tidak_overclaim": ("badge-success", "✅ Tidak Overclaim"),
        "rendah":          ("badge-info",    "🔵 Overclaim Rendah"),
        "sedang":          ("badge-warning", "🟡 Overclaim Sedang"),
        "tinggi":          ("badge-danger",  "🔴 Overclaim Tinggi"),
    }
    cls, label = mapping.get(kategori, ("badge-neutral", kategori))
    return f'<span class="badge {cls}">{label}</span>'


def show_alert(msg: str, kind: str = "info"):
    icons = {"success": "✅", "warning": "⚠️", "danger": "❌", "info": "ℹ️"}
    st.markdown(
        f'<div class="alert alert-{kind}">{icons.get(kind,"")} {msg}</div>',
        unsafe_allow_html=True
    )
