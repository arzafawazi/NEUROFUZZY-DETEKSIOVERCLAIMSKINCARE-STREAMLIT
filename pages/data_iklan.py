"""
pages/data_iklan.py
Halaman Data Iklan — Upload CSV/Excel + CRUD dataset
Mendukung skema kolom baru:
  product_id, brand, product_name, category, price, rating,
  total_review, claim_text, ingredients, review_text,
  review_length, claim_length, label_overclaim
"""
import io
import streamlit as st
import pandas as pd
from typing import Union
from config.database import execute_query, execute_many
from utils.ui_helpers import (inject_css, render_page_header,
                               show_alert, badge_overclaim, PINK_PRIMARY)
from utils.auth import require_admin, log_activity

# ── Mapping nama kolom CSV → field DB ────────────────────────
# Format: field_db: [alias-alias yang diterima di CSV]
COLUMN_ALIASES = {
    "product_id":    ["product_id", "id_produk", "id", "productid"],
    "brand":         ["brand", "merek", "merk", "nama_brand"],
    "product_name":  ["product_name", "nama_produk", "produk", "name"],
    "category":      ["category", "kategori", "jenis"],
    "platform":      ["platform", "sumber", "source", "marketplace", "toko"],
    "price":         ["price", "harga", "harga_produk"],
    "rating":        ["rating", "bintang", "skor"],
    "total_review":  ["total_review", "jumlah_review", "review_count", "ulasan"],
    "claim_text":    ["claim_text", "teks_iklan", "teks", "klaim", "claim",
                      "deskripsi", "description", "iklan"],
    "ingredients":   ["ingredients", "bahan", "kandungan", "komposisi"],
    "review_text":   ["review_text", "ulasan", "review", "teks_ulasan", "komentar"],
    "review_length": ["review_length", "panjang_ulasan", "len_review"],
    "claim_length":  ["claim_length", "panjang_klaim", "len_claim"],
    "label_overclaim": ["label_overclaim", "label", "overclaim", "kelas",
                        "label_manual", "kategori_overclaim"],
}

# Konversi label_overclaim: int (0-3) atau string → enum 4-kelas
LABEL_INT_MAP = {
    0: "tidak_overclaim",
    1: "rendah",
    2: "sedang",
    3: "tinggi",
}
LABEL_STR_MAP = {
    "tidak_overclaim": "tidak_overclaim",
    "rendah":          "rendah",
    "sedang":          "sedang",
    "tinggi":          "tinggi",
    "0": "tidak_overclaim",
    "1": "rendah",
    "2": "sedang",
    "3": "tinggi",
}

VALID_PLATFORMS = {
    "Shopee","Tokopedia","Lazada","Bukalapak","Instagram","TikTok","Lainnya"
}


# ── Entry point ───────────────────────────────────────────────
def render_data_iklan():
    inject_css()
    require_admin()
    render_page_header("Data Iklan",
                       "Kelola dataset teks iklan skincare untuk analisis overclaim",
                       "📦")

    tab1, tab2, tab3 = st.tabs(["📤 Upload Data", "📋 Tabel Data", "⚙️ Manajemen"])
    with tab1:
        _render_upload_tab()
    with tab2:
        _render_table_tab()
    with tab3:
        _render_management_tab()


# ═══════════════════════════════════════════════════════════════
# TAB 1 — UPLOAD
# ═══════════════════════════════════════════════════════════════
def _render_upload_tab():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📤 Upload File Data Iklan")
    st.markdown("""
    <p style="color:#9E9E9E;font-size:0.88rem">
        Upload file <strong>CSV</strong> atau <strong>Excel (.xlsx)</strong>.
        Kolom <strong>wajib</strong>: <code>claim_text</code>.
        Kolom lain bersifat opsional — sistem akan mendeteksi otomatis berdasarkan nama kolom.
    </p>
    """, unsafe_allow_html=True)

    # ── Panduan kolom ─────────────────────────────────────────
    with st.expander("📖 Lihat daftar kolom yang didukung"):
        st.markdown("""
| Kolom DB | Alias yang Diterima | Tipe | Keterangan |
|---|---|---|---|
| `product_id` | product_id, id_produk, id | String | ID unik produk |
| `brand` | brand, merek, merk | String | Nama brand/merek |
| `product_name` | product_name, nama_produk | String | Nama produk |
| `category` | category, kategori | String | Kategori produk |
| `platform` | platform, sumber, marketplace | Enum | Shopee/Tokopedia/dll |
| `price` | price, harga | Angka | Harga produk (Rp) |
| `rating` | rating, bintang | Float | Rating 0.0–5.0 |
| `total_review` | total_review, jumlah_review | Int | Jumlah ulasan |
| `claim_text` ⚠️ | claim_text, teks_iklan, klaim | Teks | **Wajib** — teks klaim iklan |
| `ingredients` | ingredients, bahan, kandungan | Teks | Komposisi bahan produk |
| `review_text` | review_text, ulasan, review | Teks | Teks ulasan pembeli |
| `review_length` | review_length, panjang_ulasan | Int | Panjang review (kata) |
| `claim_length` | claim_length, panjang_klaim | Int | Panjang klaim (kata) |
| `label_overclaim` | label_overclaim, label | 0/1/2/3 atau string | 0=tidak, 1=rendah, 2=sedang, 3=tinggi |
        """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Pilih file CSV atau Excel",
        type=["csv", "xlsx", "xls"],
        help="Maksimum 200MB. Gunakan encoding UTF-8 untuk CSV."
    )

    if not uploaded:
        _render_template_download()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # ── Baca file ─────────────────────────────────────────────
    try:
        if uploaded.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded, encoding="utf-8-sig", dtype=str)
        else:
            df = pd.read_excel(uploaded, dtype=str)
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    except Exception as e:
        show_alert(f"Gagal membaca file: {e}", "danger")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    st.success(f"✅ File dibaca: **{len(df)} baris**, **{len(df.columns)} kolom**")

    # ── Auto-detect mapping ───────────────────────────────────
    auto_map = _auto_detect_columns(df.columns.tolist())

    st.markdown("#### 🔗 Pemetaan Kolom Otomatis")
    st.markdown("""
    <p style="color:#9E9E9E;font-size:0.83rem">
        Sistem mendeteksi kolom secara otomatis. Koreksi jika ada yang tidak tepat.
    </p>
    """, unsafe_allow_html=True)

    col_opts = ["(skip)"] + df.columns.tolist()

    # Tampilkan mapping dalam grid 4 kolom
    field_list = list(COLUMN_ALIASES.keys())
    final_map  = {}

    for row_start in range(0, len(field_list), 4):
        cols = st.columns(4)
        for i, field in enumerate(field_list[row_start:row_start+4]):
            detected = auto_map.get(field, "(skip)")
            default_idx = col_opts.index(detected) if detected in col_opts else 0
            with cols[i]:
                required = "⚠️ " if field == "claim_text" else ""
                final_map[field] = st.selectbox(
                    f"{required}{field}",
                    options=col_opts,
                    index=default_idx,
                    key=f"map_{field}"
                )

    # ── Preview ───────────────────────────────────────────────
    st.markdown("#### 👁️ Preview Data (5 baris pertama)")
    st.dataframe(df.head(5), use_container_width=True)

    # ── Tombol Simpan ─────────────────────────────────────────
    if st.button("💾 Simpan ke Database", type="primary", use_container_width=True):
        if final_map.get("claim_text") == "(skip)":
            show_alert("Kolom `claim_text` wajib dipetakan!", "danger")
        else:
            _save_to_db(df, final_map, uploaded.name)

    _render_template_download()
    st.markdown('</div>', unsafe_allow_html=True)


def _auto_detect_columns(csv_cols: list) -> dict:
    """Cocokkan nama kolom CSV dengan alias yang diketahui."""
    result = {}
    for field, aliases in COLUMN_ALIASES.items():
        for col in csv_cols:
            if col in aliases:
                result[field] = col
                break
    return result


def _render_template_download():
    st.markdown("---")
    st.markdown("#### 📥 Download Template CSV")
    st.markdown("""
    <p style="color:#9E9E9E;font-size:0.83rem">
        Gunakan template ini sebagai acuan format kolom yang benar.
    </p>
    """, unsafe_allow_html=True)
    template = pd.DataFrame([{
        "product_id": "501",
        "brand": "Scarlett",
        "product_name": "Scarlett Sunscreen Series 8",
        "category": "Sunscreen",
        "platform": "Shopee",
        "price": "106150",
        "rating": "4.8",
        "total_review": "2070",
        "claim_text": "secara bertahap mencerahkan dan menyamarkan noda hitam",
        "ingredients": "Tea Tree, Vitamin C, Centella Asiatica, Hyaluronic Acid",
        "review_text": "Efeknya biasa saja.",
        "review_length": "3",
        "claim_length": "10",
        "label_overclaim": "0",
    }])
    csv_bytes = template.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Download Template CSV",
        csv_bytes, "template_iklan_skincare.csv", "text/csv",
        use_container_width=True
    )


def _save_to_db(df: pd.DataFrame, col_map: dict, filename: str):
    """Simpan baris-baris DataFrame ke tabel dataset_iklan."""
    user_id = st.session_state.user["id"]
    rows, skipped, errors = [], 0, []

    for idx, row in df.iterrows():
        # claim_text wajib
        claim = _val(row, col_map["claim_text"])
        if not claim:
            skipped += 1
            continue

        # Platform
        platform = _val(row, col_map.get("platform", "(skip)")) or "Lainnya"
        platform = platform.strip().title()
        if platform not in VALID_PLATFORMS:
            platform = "Lainnya"

        # label_overclaim → enum 4 kelas
        raw_label = _val(row, col_map.get("label_overclaim", "(skip)"))
        label_manual = _parse_label(raw_label)

        # Numerik
        price        = _safe_float(_val(row, col_map.get("price")))
        rating       = _safe_float(_val(row, col_map.get("rating")))
        total_review = _safe_int(_val(row, col_map.get("total_review")))
        review_len   = _safe_int(_val(row, col_map.get("review_length")))
        claim_len    = _safe_int(_val(row, col_map.get("claim_length")))

        rows.append((
            _val(row, col_map.get("product_id"))   or None,
            _val(row, col_map.get("brand"))         or None,
            _val(row, col_map.get("product_name"))  or None,
            _val(row, col_map.get("category"))      or None,
            platform,
            price, rating, total_review,
            claim,
            _val(row, col_map.get("ingredients"))  or None,
            _val(row, col_map.get("review_text"))   or None,
            review_len, claim_len,
            raw_label if raw_label and raw_label.isdigit() else
                {"tidak_overclaim":0,"rendah":1,"sedang":2,"tinggi":3}.get(
                    label_manual, None),
            label_manual,
            filename, user_id
        ))

    if not rows:
        show_alert("Tidak ada data valid untuk disimpan. Periksa kolom `claim_text`.",
                   "warning")
        return

    try:
        execute_many(
            """INSERT INTO dataset_iklan
               (product_id, brand, product_name, category, platform,
                price, rating, total_review, claim_text, ingredients,
                review_text, review_length, claim_length,
                label_overclaim, label_manual, sumber_file, uploaded_by)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            rows
        )
        log_activity(user_id, "UPLOAD_DATA",
                     f"Simpan {len(rows)} iklan dari {filename}")
        show_alert(
            f"✅ **{len(rows)}** iklan berhasil disimpan."
            + (f" ({skipped} baris dilewati — claim_text kosong)" if skipped else ""),
            "success"
        )
        st.rerun()
    except Exception as e:
        show_alert(f"Gagal menyimpan ke database: {e}", "danger")


# ── Helpers ────────────────────────────────────────────────────
def _val(row, col) -> str:
    if not col or col == "(skip)" or col not in row.index:
        return ""
    v = row[col]
    return "" if pd.isna(v) else str(v).strip()


def _safe_float(s) -> Union[float, None]:
    try:
        return float(str(s).replace(",", ".")) if s else None
    except Exception:
        return None


def _safe_int(s) -> Union[int, None]:
    try:
        return int(float(str(s))) if s else None
    except Exception:
        return None


def _parse_label(raw: str) -> Union[str, None]:
    """Ubah raw label (int 0-3 atau string) → enum label_manual."""
    if not raw:
        return None
    raw = raw.strip().lower()
    # coba int
    try:
        v = int(float(raw))
        return LABEL_INT_MAP.get(v)
    except Exception:
        pass
    return LABEL_STR_MAP.get(raw)


# ═══════════════════════════════════════════════════════════════
# TAB 2 — TABEL DATA
# ═══════════════════════════════════════════════════════════════
def _render_table_tab():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📋 Daftar Data Iklan")

    # ── Filter ────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        filter_platform = st.selectbox(
            "Platform",
            ["Semua","Shopee","Tokopedia","Lazada","Bukalapak",
             "Instagram","TikTok","Lainnya"],
            key="fp_tbl"
        )
    with fc2:
        filter_status = st.selectbox(
            "Status Proses",
            ["Semua","Belum Diproses","Sudah Diproses"],
            key="fs_tbl"
        )
    with fc3:
        filter_label = st.selectbox(
            "Label Overclaim",
            ["Semua","tidak_overclaim","rendah","sedang","tinggi"],
            key="fl_tbl"
        )
    with fc4:
        filter_category = st.text_input("Kategori Produk", key="fc_tbl",
                                        placeholder="Serum, Sunscreen, …")
    search_text = st.text_input("🔍 Cari brand / nama produk / teks klaim…",
                                key="search_tbl")

    # ── Query ─────────────────────────────────────────────────
    sql = """
        SELECT d.id,
               d.product_id,
               d.brand,
               d.product_name,
               d.category,
               d.platform,
               d.price,
               d.rating,
               d.total_review,
               SUBSTRING(d.claim_text, 1, 100) AS claim_text,
               d.review_length,
               d.claim_length,
               d.label_overclaim,
               d.label_manual,
               d.is_processed,
               d.uploaded_at
        FROM dataset_iklan d
        WHERE 1=1
    """
    params = []
    if filter_platform != "Semua":
        sql += " AND d.platform=%s";      params.append(filter_platform)
    if filter_status == "Belum Diproses":
        sql += " AND d.is_processed=0"
    elif filter_status == "Sudah Diproses":
        sql += " AND d.is_processed=1"
    if filter_label != "Semua":
        sql += " AND d.label_manual=%s";  params.append(filter_label)
    if filter_category:
        sql += " AND d.category LIKE %s"; params.append(f"%{filter_category}%")
    if search_text:
        sql += """ AND (d.brand LIKE %s
                     OR d.product_name LIKE %s
                     OR d.claim_text   LIKE %s)"""
        params.extend([f"%{search_text}%"] * 3)
    sql += " ORDER BY d.id DESC LIMIT 300"

    try:
        rows = execute_query(sql, tuple(params) if params else None, fetch=True)
    except Exception as e:
        show_alert(f"Gagal memuat data: {e}", "danger")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    if not rows:
        show_alert("Belum ada data iklan atau tidak ada yang cocok dengan filter.", "info")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    df = pd.DataFrame(rows)
    total = len(df)

    # ── Ringkasan cepat ───────────────────────────────────────
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Total Baris", total)
    sc2.metric("Sudah Diproses",
               int(df["is_processed"].sum()))
    sc3.metric("Berlabel",
               int(df["label_manual"].notna().sum()))
    sc4.metric("Rata-rata Rating",
               f"{pd.to_numeric(df['rating'], errors='coerce').mean():.2f}"
               if "rating" in df.columns else "—")

    # ── Badge helper ──────────────────────────────────────────
    df["Label"] = df["label_manual"].apply(
        lambda x: badge_overclaim(x) if x else
                  '<span class="badge badge-neutral">—</span>'
    )
    df["Status"] = df["is_processed"].apply(
        lambda x: '<span class="badge badge-success">✅ Selesai</span>'
                  if x else '<span class="badge badge-warning">⏳ Pending</span>'
    )
    df["Tanggal"] = pd.to_datetime(df["uploaded_at"]).dt.strftime("%d/%m/%Y")
    df["Harga"] = df["price"].apply(
        lambda x: f"Rp {int(float(x)):,}".replace(",",".") if x else "—"
    )

    # ── Render tabel HTML ─────────────────────────────────────
    display = df[[
        "id","brand","product_name","category","platform",
        "Harga","rating","total_review",
        "claim_text","review_length","claim_length",
        "Label","Status","Tanggal"
    ]].rename(columns={
        "id":"No","brand":"Brand","product_name":"Nama Produk",
        "category":"Kategori","platform":"Platform",
        "rating":"Rating","total_review":"Total Review",
        "claim_text":"Teks Klaim","review_length":"Len Review",
        "claim_length":"Len Klaim",
    })

    html = display.to_html(
        escape=False, index=False,
        classes="table table-striped table-hover table-sm",
        border=0
    )
    st.markdown(
        f'<div style="overflow-x:auto;max-height:500px;overflow-y:auto">'
        f'{html}</div>',
        unsafe_allow_html=True
    )

    # ── Export ────────────────────────────────────────────────
    export_df = df.drop(columns=["Label","Status"], errors="ignore")
    st.download_button(
        "⬇️ Export CSV",
        export_df.to_csv(index=False).encode("utf-8-sig"),
        "data_iklan_export.csv", "text/csv"
    )

    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# TAB 3 — MANAJEMEN
# ═══════════════════════════════════════════════════════════════
def _render_management_tab():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### ⚙️ Manajemen Data")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🗑️ Hapus Data Berdasarkan ID")
        del_id = st.number_input("ID Iklan", min_value=1, step=1, key="del_id")
        if st.button("🗑️ Hapus", type="secondary", key="btn_del"):
            try:
                n = execute_query(
                    "DELETE FROM dataset_iklan WHERE id=%s", (int(del_id),))
                show_alert(f"Iklan ID {del_id} berhasil dihapus." if n
                           else "ID tidak ditemukan.", "success" if n else "warning")
                if n:
                    st.rerun()
            except Exception as e:
                show_alert(f"Gagal: {e}", "danger")

    with col2:
        st.markdown("#### 🔄 Reset Status Proses")
        st.markdown("""
        <p style="font-size:0.85rem;color:#9E9E9E">
            Tandai semua data sebagai <em>belum diproses</em>
            agar pipeline ANFIS bisa dijalankan ulang dari awal.
        </p>
        """, unsafe_allow_html=True)
        if st.button("🔄 Reset Semua Status", type="secondary", key="btn_reset"):
            try:
                execute_query("UPDATE dataset_iklan SET is_processed=0")
                show_alert("Semua status berhasil di-reset.", "success")
                st.rerun()
            except Exception as e:
                show_alert(f"Gagal: {e}", "danger")

    # ── Statistik distribusi ──────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📊 Distribusi Label dalam Dataset")
    try:
        dist = execute_query(
            """SELECT label_manual, COUNT(*) as n
               FROM dataset_iklan
               WHERE label_manual IS NOT NULL
               GROUP BY label_manual ORDER BY FIELD(label_manual,
               'tidak_overclaim','rendah','sedang','tinggi')""",
            fetch=True
        )
        if dist:
            import plotly.graph_objects as go
            labels = [r["label_manual"].replace("_"," ").title() for r in dist]
            values = [r["n"] for r in dist]
            colors = ["#4CAF50","#2196F3","#FF9800","#F44336"]
            fig = go.Figure(go.Bar(
                x=labels, y=values,
                marker_color=colors[:len(labels)],
                text=values, textposition="outside"
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=250,
                margin=dict(t=10,b=10,l=10,r=10),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)")
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            show_alert("Belum ada data berlabel.", "info")
    except Exception:
        pass

    st.markdown('</div>', unsafe_allow_html=True)
