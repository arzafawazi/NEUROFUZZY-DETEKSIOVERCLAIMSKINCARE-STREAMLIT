"""
pages/hasil_deteksi.py
Halaman Hasil Deteksi — Filter + Tabel + Visualisasi
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from config.database import execute_query
from utils.ui_helpers import (inject_css, render_page_header,
                               show_alert, badge_overclaim,
                               render_metric_card, PINK_PRIMARY, PINK_DARK)
from utils.auth import require_login


def render_hasil_deteksi():
    inject_css()
    require_login()
    render_page_header(
        "Hasil Deteksi",
        "Output klasifikasi overclaim iklan skincare dari model ANFIS",
        "📊"
    )

    # ── Pilih Run ──────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    runs = _load_runs()
    if not runs:
        show_alert("Belum ada hasil deteksi. Jalankan proses deteksi terlebih dahulu.", "info")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    run_options = {f"[ID:{r['id']}] {r['run_name']} — {r['started_at']}": r["id"]
                   for r in runs}
    selected_run_label = st.selectbox("📌 Pilih Detection Run", list(run_options.keys()))
    run_id = run_options[selected_run_label]
    run_info = next(r for r in runs if r["id"] == run_id)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Metrik Run ─────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: render_metric_card("Total Data", run_info["total_data"], icon="📋")
    with m2: render_metric_card("Akurasi", f"{(run_info['accuracy'] or 0)*100:.1f}%", icon="🎯")
    with m3: render_metric_card("Precision", f"{(run_info['precision_val'] or 0):.4f}", "teal", "🔬")
    with m4: render_metric_card("Recall", f"{(run_info['recall_val'] or 0):.4f}", "purple", "📡")
    with m5: render_metric_card("F1-Score", f"{(run_info['f1_score'] or 0):.4f}", "orange", "⚡")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Filter ─────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🔍 Filter Hasil")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        filter_platform = st.selectbox(
            "Platform",
            ["Semua","Shopee","Tokopedia","Lazada","Bukalapak",
             "Instagram","TikTok","Lainnya"],
            key="hd_platform"
        )
    with f2:
        filter_kategori = st.selectbox(
            "Kategori Overclaim",
            ["Semua","tidak_overclaim","rendah","sedang","tinggi"],
            key="hd_kategori"
        )
    with f3:
        date_from = st.date_input("Dari Tanggal",
                                  value=date.today() - timedelta(days=30),
                                  key="hd_from")
    with f4:
        date_to = st.date_input("Sampai Tanggal",
                                value=date.today(),
                                key="hd_to")
    search_q = st.text_input("🔍 Cari teks iklan...", key="hd_search")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Load Data ──────────────────────────────────────────
    df = _load_results(run_id, filter_platform, filter_kategori,
                       str(date_from), str(date_to), search_q)

    if df.empty:
        show_alert("Tidak ada data yang cocok dengan filter.", "info")
        return

    # ── Tab: Tabel | Visualisasi | Detail ─────────────────
    tab1, tab2, tab3 = st.tabs(["📋 Tabel Hasil", "📈 Visualisasi", "🔎 Detail & Ekspor"])

    with tab1:
        _render_table(df)

    with tab2:
        _render_visualisasi(df)

    with tab3:
        _render_detail_ekspor(df, run_id)


# ── Loaders ───────────────────────────────────────────────────
def _load_runs():
    try:
        return execute_query(
            """SELECT id, run_name, total_data, accuracy,
                      precision_val, recall_val, f1_score, started_at
               FROM detection_run WHERE status='completed'
               ORDER BY id DESC LIMIT 20""",
            fetch=True
        )
    except Exception:
        return []


def _load_results(run_id, platform, kategori, date_from, date_to, search):
    # Kita tambahkan LEFT JOIN ke dataset_iklan (alias d)
    # untuk mengambil brand, product_name, category, price, dll.
    sql = """
        SELECT h.id, h.iklan_id, d.brand, d.product_name, d.category, 
               d.price, d.rating, d.total_review, d.ingredients,
               h.platform, h.teks_iklan_snippet,
               h.kategori_overclaim, h.confidence_score,
               h.label_asli, h.is_correct, h.alasan_fuzzy,
               h.analyzed_at
        FROM hasil_deteksi h
        LEFT JOIN dataset_iklan d ON h.iklan_id = d.id
        WHERE h.run_id=%s
    """
    params = [run_id]
    if platform != "Semua":
        sql += " AND h.platform=%s"; params.append(platform)
    if kategori != "Semua":
        sql += " AND h.kategori_overclaim=%s"; params.append(kategori)
    sql += " AND DATE(h.analyzed_at) BETWEEN %s AND %s"
    params.extend([date_from, date_to])
    if search:
        sql += """ AND (h.teks_iklan_snippet LIKE %s 
                     OR d.brand LIKE %s 
                     OR d.product_name LIKE %s)"""
        params.extend([f"%{search}%"] * 3)
    sql += " ORDER BY h.id DESC LIMIT 500"

    try:
        rows = execute_query(sql, tuple(params), fetch=True)
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except Exception as e:
        show_alert(f"Gagal memuat hasil: {e}", "danger")
        return pd.DataFrame()


# ── Tabel ─────────────────────────────────────────────────────
def _render_table(df: pd.DataFrame):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"**{len(df)} hasil ditemukan**")

    display = df.copy()
    display["Kategori"] = display["kategori_overclaim"].apply(badge_overclaim)
    display["Confidence"] = display["confidence_score"].apply(
        lambda x: f"{x*100:.1f}%" if pd.notna(x) else "—"
    )
    display["Benar?"] = display["is_correct"].apply(
        lambda x: "✅" if x == 1 else ("❌" if x == 0 else "—")
    )
    display["Tanggal"] = pd.to_datetime(display["analyzed_at"]).dt.strftime("%d/%m/%Y %H:%M")
    
    # Format Harga
    display["Harga"] = display["price"].apply(
        lambda x: f"Rp {int(float(x)):,}".replace(",",".") if pd.notna(x) and x else "—"
    )

    # Pilih urutan kolom yang ingin ditampilkan di tabel HTML
    html = display[["id", "brand", "product_name", "category", "Harga", "rating", "platform", 
                    "teks_iklan_snippet", "Kategori", "Confidence", "Benar?", "Tanggal"]].rename(columns={
        "id":"No", "brand":"Brand", "product_name":"Nama Produk", 
        "category":"Kategori Produk", "rating":"Rating",
        "platform":"Platform", "teks_iklan_snippet":"Teks Iklan"
    }).to_html(escape=False, index=False,
               classes="table table-hover table-striped table-sm",
               border=0)
               
    # Tambahkan bungkus div agar bisa di-scroll ke samping (karena kolomnya banyak)
    st.markdown(
        f'<div style="overflow-x:auto;max-height:500px;overflow-y:auto">{html}</div>', 
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)


# ── Visualisasi ───────────────────────────────────────────────
def _render_visualisasi(df: pd.DataFrame):
    col1, col2 = st.columns(2)

    # Pie overclaim
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🥧 Distribusi Kategori Overclaim")
        vc = df["kategori_overclaim"].value_counts().reset_index()
        vc.columns = ["kategori","count"]
        colors = {"tidak_overclaim":"#4CAF50","rendah":"#2196F3",
                  "sedang":"#FF9800","tinggi":"#F44336"}
        fig = px.pie(vc, names="kategori", values="count",
                     color="kategori",
                     color_discrete_map=colors,
                     hole=0.4)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                          margin=dict(t=10,b=10,l=10,r=10), height=260)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Bar per platform & kategori
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🏪 Overclaim per Platform")
        cross = df.groupby(["platform","kategori_overclaim"]).size().reset_index(name="n")
        fig2 = px.bar(cross, x="platform", y="n", color="kategori_overclaim",
                      barmode="stack",
                      color_discrete_map={"tidak_overclaim":"#4CAF50","rendah":"#2196F3",
                                          "sedang":"#FF9800","tinggi":"#F44336"})
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)",
                           margin=dict(t=10,b=10,l=10,r=10), height=260,
                           legend=dict(orientation="h",y=-0.25))
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Confidence distribution
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 📐 Distribusi Confidence Score")
    fig3 = px.histogram(df, x="confidence_score", nbins=30,
                        color="kategori_overclaim",
                        color_discrete_map={"tidak_overclaim":"#4CAF50","rendah":"#2196F3",
                                            "sedang":"#FF9800","tinggi":"#F44336"},
                        barmode="overlay", opacity=0.75)
    fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                       plot_bgcolor="rgba(0,0,0,0)",
                       margin=dict(t=10,b=10,l=20,r=20), height=220,
                       xaxis_title="Confidence Score (0–1)",
                       yaxis_title="Jumlah Iklan")
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ── Detail & Ekspor ───────────────────────────────────────────
def _render_detail_ekspor(df: pd.DataFrame, run_id: int):
    # Confusion summary
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🎯 Ringkasan Evaluasi")
    c1, c2 = st.columns(2)
    with c1:
        correct   = df[df["is_correct"] == 1].shape[0]
        incorrect = df[df["is_correct"] == 0].shape[0]
        unlabeled = df[df["is_correct"].isna()].shape[0]
        st.markdown(f"""
        <div class="alert alert-success">✅ Prediksi Benar: <strong>{correct}</strong></div>
        <div class="alert alert-danger">❌ Prediksi Salah: <strong>{incorrect}</strong></div>
        <div class="alert alert-info">ℹ️ Tanpa Label: <strong>{unlabeled}</strong></div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("**Contoh Alasan Fuzzy (5 pertama)**")
        for _, row in df.head(5).iterrows():
            if row["alasan_fuzzy"]:
                st.markdown(f"""
                <div style="background:#FCE4EC;border-radius:8px;padding:0.5rem 0.75rem;margin-bottom:0.4rem;font-size:0.82rem">
                    <strong>[{row['kategori_overclaim'].upper()}]</strong><br>
                    {row['alasan_fuzzy']}<br>
                    <em style="color:#9E9E9E">{row['teks_iklan_snippet'][:60]}...</em>
                </div>
                """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Export
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 📥 Ekspor Hasil")
    ec1, ec2 = st.columns(2)
    with ec1:
        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Download CSV",
                           csv_bytes, f"hasil_run_{run_id}.csv", "text/csv",
                           use_container_width=True)
    with ec2:
        try:
            import io
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Hasil Deteksi")
            buf.seek(0)
            st.download_button("⬇️ Download Excel",
                               buf.read(),
                               f"hasil_run_{run_id}.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
        except Exception:
            st.info("Install openpyxl untuk ekspor Excel.")
    st.markdown('</div>', unsafe_allow_html=True)
