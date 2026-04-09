"""
pages/data_iklan.py
Halaman Data Iklan — Upload CSV/Excel + CRUD dataset
"""
import io
import streamlit as st
import pandas as pd
from datetime import datetime
from config.database import execute_query, execute_many
from utils.ui_helpers import (inject_css, render_page_header,
                               show_alert, badge_overclaim, PINK_PRIMARY)
from utils.auth import require_admin, log_activity


EXPECTED_COLUMNS = {
    "teks_iklan": ["teks_iklan", "teks", "text", "iklan", "deskripsi", "description"],
    "platform":   ["platform", "sumber", "source", "marketplace"],
    "brand":      ["brand", "merek", "merk", "nama_produk"],
    "label_manual": ["label", "label_manual", "kategori", "overclaim"],
}


def render_data_iklan():
    inject_css()
    require_admin()
    render_page_header("Data Iklan", "Kelola dataset teks iklan skincare", "📦")

    tab1, tab2, tab3 = st.tabs(["📤 Upload Data", "📋 Tabel Data", "⚙️ Manajemen"])

    with tab1:
        _render_upload_tab()

    with tab2:
        _render_table_tab()

    with tab3:
        _render_management_tab()


# ── Tab Upload ─────────────────────────────────────────────────
def _render_upload_tab():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📤 Upload File Data Iklan")
    st.markdown("""
    <p style="color:#9E9E9E;font-size:0.88rem">
        Upload file <strong>CSV</strong> atau <strong>Excel (.xlsx)</strong> berisi data iklan skincare.
        Pastikan file memiliki kolom: <code>teks_iklan</code>, <code>platform</code>
        (opsional: <code>brand</code>, <code>label_manual</code>).
    </p>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Pilih file CSV atau Excel",
        type=["csv", "xlsx", "xls"],
        help="Maksimum 200MB"
    )

    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded, encoding="utf-8-sig")
            else:
                df = pd.read_excel(uploaded)

            df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
            st.success(f"✅ File berhasil dibaca: **{len(df)} baris**, **{len(df.columns)} kolom**")

            # Preview
            st.markdown("#### 👁️ Preview Data (10 baris pertama)")
            st.dataframe(df.head(10), use_container_width=True)

            # Mapping kolom
            st.markdown("#### 🔗 Pemetaan Kolom")
            col_map = {}
            cols = st.columns(len(EXPECTED_COLUMNS))
            for idx, (field, aliases) in enumerate(EXPECTED_COLUMNS.items()):
                found = next((c for c in df.columns if c in aliases), None)
                with cols[idx]:
                    col_map[field] = st.selectbox(
                        f"Kolom → {field}",
                        options=["(skip)"] + list(df.columns),
                        index=list(df.columns).index(found) + 1 if found else 0,
                        key=f"map_{field}"
                    )

            if st.button("💾 Simpan ke Database", type="primary",
                         use_container_width=True):
                _save_to_db(df, col_map)

        except Exception as e:
            show_alert(f"Gagal membaca file: {e}", "danger")

    # Template download
    st.markdown("---")
    st.markdown("#### 📥 Download Template")
    template_df = pd.DataFrame({
        "teks_iklan": [
            "Serum ini terbukti secara klinis memutihkan kulit 100% dalam 7 hari!",
            "Pelembab alami untuk kulit kering, cocok untuk semua jenis kulit.",
        ],
        "platform":     ["Shopee", "Tokopedia"],
        "brand":        ["Brand A", "Brand B"],
        "label_manual": ["tinggi", "tidak_overclaim"],
    })
    csv_bytes = template_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Download Template CSV", csv_bytes,
                       "template_iklan.csv", "text/csv")
    st.markdown('</div>', unsafe_allow_html=True)


def _save_to_db(df: pd.DataFrame, col_map: dict):
    user_id = st.session_state.user["id"]
    rows = []
    skipped = 0

    for _, row in df.iterrows():
        teks = _get_val(row, col_map["teks_iklan"])
        if not teks or str(teks).strip() == "" or col_map["teks_iklan"] == "(skip)":
            skipped += 1
            continue

        platform = _get_val(row, col_map["platform"]) or "Lainnya"
        brand    = _get_val(row, col_map["brand"]) or ""
        label    = _get_val(row, col_map["label_manual"])

        valid_labels = {"tidak_overclaim","rendah","sedang","tinggi"}
        label = label if label in valid_labels else None

        valid_platforms = {"Shopee","Tokopedia","Lazada","Bukalapak",
                           "Instagram","TikTok","Lainnya"}
        platform = platform if platform in valid_platforms else "Lainnya"

        rows.append((platform, brand, str(teks).strip(), label, uploaded.name
                     if False else "upload", user_id))

    if not rows:
        show_alert("Tidak ada data valid untuk disimpan.", "warning")
        return

    try:
        execute_many(
            """INSERT INTO dataset_iklan
               (platform, brand, teks_iklan, label_manual, sumber_file, uploaded_by)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            rows
        )
        log_activity(user_id, "UPLOAD_DATA",
                     f"Berhasil menyimpan {len(rows)} iklan")
        show_alert(f"✅ {len(rows)} iklan berhasil disimpan."
                   + (f" ({skipped} baris dilewati)" if skipped else ""),
                   "success")
        st.rerun()
    except Exception as e:
        show_alert(f"Gagal menyimpan: {e}", "danger")


def _get_val(row, col):
    if col == "(skip)" or col not in row.index:
        return ""
    v = row[col]
    return "" if pd.isna(v) else str(v).strip()


# ── Tab Tabel ──────────────────────────────────────────────────
def _render_table_tab():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📋 Daftar Data Iklan")

    # Filter
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        filter_platform = st.selectbox(
            "Platform", ["Semua","Shopee","Tokopedia","Lazada",
                         "Bukalapak","Instagram","TikTok","Lainnya"],
            key="filter_platform_tbl"
        )
    with fc2:
        filter_status = st.selectbox(
            "Status Proses", ["Semua","Belum Diproses","Sudah Diproses"],
            key="filter_status_tbl"
        )
    with fc3:
        search_text = st.text_input("🔍 Cari teks iklan...", key="search_tbl")

    # Build query
    sql = """
        SELECT d.id, d.platform, d.brand,
               SUBSTRING(d.teks_iklan,1,120) AS teks_iklan,
               d.label_manual, d.is_processed, d.uploaded_at
        FROM dataset_iklan d
        WHERE 1=1
    """
    params = []
    if filter_platform != "Semua":
        sql += " AND d.platform=%s"
        params.append(filter_platform)
    if filter_status == "Belum Diproses":
        sql += " AND d.is_processed=0"
    elif filter_status == "Sudah Diproses":
        sql += " AND d.is_processed=1"
    if search_text:
        sql += " AND d.teks_iklan LIKE %s"
        params.append(f"%{search_text}%")
    sql += " ORDER BY d.id DESC LIMIT 200"

    try:
        rows = execute_query(sql, tuple(params) if params else None, fetch=True)
        df = pd.DataFrame(rows)
        if df.empty:
            show_alert("Belum ada data iklan. Silakan upload terlebih dahulu.", "info")
        else:
            # Render tabel HTML
            df["label_badge"] = df["label_manual"].apply(
                lambda x: badge_overclaim(x) if x else '<span class="badge badge-neutral">—</span>'
            )
            df["status_badge"] = df["is_processed"].apply(
                lambda x: '<span class="badge badge-success">✅ Selesai</span>'
                          if x else '<span class="badge badge-warning">⏳ Pending</span>'
            )
            df["uploaded_at"] = pd.to_datetime(df["uploaded_at"]).dt.strftime("%d/%m/%Y")

            display_cols = ["id","platform","brand","teks_iklan",
                            "label_badge","status_badge","uploaded_at"]
            html = df[display_cols].rename(columns={
                "id":"No","platform":"Platform","brand":"Brand",
                "teks_iklan":"Teks Iklan","label_badge":"Label",
                "status_badge":"Status","uploaded_at":"Tanggal"
            }).to_html(escape=False, index=False,
                       classes="table table-striped table-hover table-sm",
                       border=0)
            st.markdown(html, unsafe_allow_html=True)

            # Export
            csv_export = df.drop(columns=["label_badge","status_badge"]).to_csv(index=False)
            st.download_button("⬇️ Export CSV", csv_export.encode("utf-8-sig"),
                               "data_iklan_export.csv", "text/csv")
    except Exception as e:
        show_alert(f"Gagal memuat data: {e}", "danger")

    st.markdown('</div>', unsafe_allow_html=True)


# ── Tab Manajemen ──────────────────────────────────────────────
def _render_management_tab():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### ⚙️ Manajemen Data")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🗑️ Hapus Data")
        del_id = st.number_input("ID Iklan yang ingin dihapus", min_value=1, step=1)
        if st.button("🗑️ Hapus Iklan", type="secondary"):
            try:
                affected = execute_query(
                    "DELETE FROM dataset_iklan WHERE id=%s", (int(del_id),)
                )
                if affected:
                    show_alert(f"Iklan ID {del_id} berhasil dihapus.", "success")
                    st.rerun()
                else:
                    show_alert("ID tidak ditemukan.", "warning")
            except Exception as e:
                show_alert(f"Gagal menghapus: {e}", "danger")

    with col2:
        st.markdown("#### 🔄 Reset Status Proses")
        st.markdown("""
        <p style="font-size:0.85rem;color:#9E9E9E">
            Kembalikan semua data ke status 'belum diproses' 
            agar dapat dijalankan ulang.
        </p>
        """, unsafe_allow_html=True)
        if st.button("🔄 Reset Semua Status", type="secondary"):
            try:
                execute_query("UPDATE dataset_iklan SET is_processed=0")
                show_alert("Semua status berhasil di-reset.", "success")
                st.rerun()
            except Exception as e:
                show_alert(f"Gagal reset: {e}", "danger")

    st.markdown('</div>', unsafe_allow_html=True)
