"""
pages/proses_deteksi.py
Halaman Proses Deteksi — Preprocessing → Ekstraksi Fitur → ANFIS
"""
import time
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from config.database import execute_query
from utils.ui_helpers import (inject_css, render_page_header,
                              show_alert, PINK_PRIMARY)
from utils.auth import require_admin, log_activity
from utils.feature_extractor import preprocess_batch
from models.anfis import ANFISOverclaimDetector, LABEL_MAP, prepare_Xy


def render_proses_deteksi():
    inject_css()
    require_admin()
    render_page_header(
        "Proses Deteksi",
        "Jalankan pipeline preprocessing hingga klasifikasi ANFIS",
        "⚙️"
    )

    # ── Konfigurasi Model ───────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🔧 Konfigurasi Model ANFIS")

    c1, c2, c3 = st.columns(3)
    with c1:
        num_mf = st.selectbox("Jumlah Membership Function",
                              [2, 3, 4, 5], index=1, key="cfg_mf")
        mf_type = st.selectbox("Tipe MF",
                               ["gaussian","triangular","trapezoidal","bell"],
                               key="cfg_mftype")
    with c2:
        lr = st.number_input("Learning Rate", 0.001, 0.5, 0.01,
                             step=0.001, format="%.3f", key="cfg_lr")
        epochs = st.number_input("Epochs", 10, 500, 100,
                                 step=10, key="cfg_epoch")
    with c3:
        train_split = st.slider("Train/Test Split", 0.5, 0.9, 0.8,
                                step=0.05, key="cfg_split")
        run_name = st.text_input("Nama Run",
                                 value=f"Run_{datetime.now().strftime('%Y%m%d_%H%M')}",
                                 key="cfg_name")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Tombol Pipeline ─────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🚀 Jalankan Pipeline")
    st.markdown("""
    <p style="color:#9E9E9E;font-size:0.87rem">
        Klik tombol secara berurutan untuk menjalankan tahapan proses,
        atau gunakan <strong>Jalankan Semua</strong> untuk otomatisasi penuh.
    </p>
    """, unsafe_allow_html=True)

    b1, b2, b3, b4 = st.columns(4)
    run_preprocess = b1.button("1️⃣ Preprocessing", use_container_width=True)
    run_feature    = b2.button("2️⃣ Ekstraksi Fitur", use_container_width=True,
                               disabled=not st.session_state.get("preproc_done"))
    run_anfis      = b3.button("3️⃣ Jalankan ANFIS", use_container_width=True,
                               disabled=not st.session_state.get("feature_done"))
    run_all        = b4.button("⚡ Jalankan Semua", use_container_width=True,
                               type="primary")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Area Log ────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📟 Log Proses")
    log_placeholder = st.empty()
    progress_bar    = st.empty()

    if "log_lines" not in st.session_state:
        st.session_state.log_lines = []

    def append_log(kind: str, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        css_class = {"info":"log-info","warn":"log-warn",
                     "error":"log-error","ok":"log-ok"}.get(kind,"")
        st.session_state.log_lines.append(
            f'<span class="{css_class}">[{ts}] [{kind.upper()}] {msg}</span>'
        )
        _render_log(log_placeholder)

    def _render_log(ph):
        content = "<br>".join(st.session_state.log_lines[-80:])
        ph.markdown(f'<div class="log-box">{content}</div>',
                    unsafe_allow_html=True)

    _render_log(log_placeholder)

    # ── Eksekusi ────────────────────────────────────────────
    if run_preprocess or run_all:
        _exec_preprocessing(append_log, progress_bar)

    if run_feature or run_all:
        if not st.session_state.get("preproc_done"):
            show_alert("Jalankan preprocessing terlebih dahulu.", "warning")
        else:
            _exec_feature_extraction(append_log, progress_bar)

    if run_anfis or run_all:
        if not st.session_state.get("feature_done"):
            show_alert("Jalankan ekstraksi fitur terlebih dahulu.", "warning")
        else:
            _exec_anfis(append_log, progress_bar,
                        num_mf, mf_type, lr, int(epochs),
                        train_split, run_name)

    # Clear log button
    if st.button("🗑️ Bersihkan Log"):
        st.session_state.log_lines = []
        for k in ["preproc_done","feature_done","feature_df"]:
            st.session_state.pop(k, None)
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Riwayat Run ─────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📜 Riwayat Deteksi Run")
    _render_run_history()
    st.markdown('</div>', unsafe_allow_html=True)


# ── Step 1: Preprocessing ──────────────────────────────────────
def _exec_preprocessing(log, prog):
    log("info", "=== TAHAP 1: PREPROCESSING TEKS ===")
    try:
        data = execute_query(
            """SELECT id, claim_text, ingredients,
                      review_text, review_length, claim_length, rating
               FROM dataset_iklan ORDER BY id""",
            fetch=True
        )
        if not data:
            log("warn", "Tidak ada data iklan. Upload data terlebih dahulu.")
            return

        log("info", f"Ditemukan {len(data)} data iklan.")
        log("info", "Menjalankan: tokenisasi → stopword removal → stemming (Sastrawi) → normalisasi...")

        prog.progress(0.0, "Preprocessing...")
        time.sleep(0.3)

        # Preview log 5 pertama
        for i, d in enumerate(data[:5]):
            from models.preprocessor import full_preprocess
            result = full_preprocess(str(d.get("claim_text") or ""))
            log("ok", f"[ID:{d['id']}] Tokens:{result['token_count']} | "
                      f"Normalized: {result['normalized'][:60]}...")
            prog.progress((i + 1) / max(len(data), 1), f"Preprocessing {i+1}/{len(data)}")

        if len(data) > 5:
            log("info", f"... dan {len(data)-5} data lainnya diproses.")

        prog.progress(1.0, "✅ Preprocessing selesai!")
        log("ok", f"✅ Preprocessing selesai untuk {len(data)} data.")
        st.session_state.preproc_done = True
        st.session_state.raw_data = data

    except Exception as e:
        log("error", f"Preprocessing gagal: {e}")


# ── Step 2: Ekstraksi Fitur ────────────────────────────────────
def _exec_feature_extraction(log, prog):
    log("info", "=== TAHAP 2: EKSTRAKSI FITUR TEKSTUAL ===")
    try:
        data = st.session_state.get("raw_data") or execute_query(
            """SELECT id, claim_text, ingredients,
                      review_text, review_length, claim_length, rating
               FROM dataset_iklan""",
            fetch=True
        )
        log("info", f"Mengekstrak fitur dari {len(data)} dokumen...")
        log("info", "Fitur: TF-IDF · Hyperbolic · Scientific · Absolute · "
                    "Intensity · Claim Length · Ingredient Count · Rating...")

        prog.progress(0.0, "Fitting TF-IDF...")
        df_features = preprocess_batch(data, log_callback=log)
        prog.progress(1.0, "✅ Ekstraksi fitur selesai!")

        log("ok", f"✅ Ekstraksi selesai. Shape fitur: {df_features.shape}")
        log("info", f"Kolom: {list(df_features.columns)}")

        st.session_state.feature_done = True
        st.session_state.feature_df = df_features

    except Exception as e:
        log("error", f"Ekstraksi fitur gagal: {e}")


# ── Step 3: ANFIS ──────────────────────────────────────────────
def _exec_anfis(log, prog, num_mf, mf_type, lr, epochs,
                train_split, run_name):
    log("info", "=== TAHAP 3: TRAINING & INFERENSI ANFIS ===")
    user_id = st.session_state.user["id"]

    try:
        df = st.session_state.get("feature_df")
        if df is None or df.empty:
            log("error", "Feature DataFrame kosong. Jalankan ekstraksi fitur dulu.")
            return

        # Ambil label dari DB
        ids = df["id"].tolist()
        ph  = ",".join(["%s"] * len(ids))
        label_rows = execute_query(
            f"SELECT id, label_manual FROM dataset_iklan WHERE id IN ({ph})",
            tuple(ids), fetch=True
        )
        label_map_db = {r["id"]: r["label_manual"] for r in label_rows}
        df["label_manual"] = df["id"].map(label_map_db)

        X, y = prepare_Xy(df)

        if y is None or np.all(y == 0):
            log("warn", "Label manual tidak ditemukan/semua nol. Menggunakan mode inference (tanpa training).")
            # Inference only
            model = ANFISOverclaimDetector(num_mf=num_mf, mf_type=mf_type,
                                           learning_rate=lr, epochs=10)
            model.fit(X, np.zeros(len(X), dtype=int))
            eval_metrics = {"accuracy": None, "precision": None,
                            "recall": None, "f1_score": None}
        else:
            n_train = int(len(X) * train_split)
            X_train, X_test = X[:n_train], X[n_train:]
            y_train, y_test = y[:n_train], y[n_train:]

            log("info", f"Train: {n_train} | Test: {len(X)-n_train}")
            log("info", f"Config: MF={num_mf}, Type={mf_type}, LR={lr}, Epochs={epochs}")

            prog.progress(0.1, "Inisialisasi ANFIS...")
            model = ANFISOverclaimDetector(num_mf=num_mf, mf_type=mf_type,
                                           learning_rate=lr, epochs=epochs)

            prog.progress(0.2, "Training ANFIS...")
            model.fit(X_train, y_train, log_callback=log)

            prog.progress(0.85, "Evaluasi model...")
            eval_metrics = model.evaluate(X_test, y_test)
            log("ok", f"✅ Accuracy:  {eval_metrics['accuracy']:.4f}")
            log("ok", f"✅ Precision: {eval_metrics['precision']:.4f}")
            log("ok", f"✅ Recall:    {eval_metrics['recall']:.4f}")
            log("ok", f"✅ F1-Score:  {eval_metrics['f1_score']:.4f}")

        # Simpan run ke DB
        run_id = _save_run(run_name, num_mf, lr, epochs, len(X),
                           eval_metrics, user_id)
        
        # --- PENGECEKAN ID INDUK (Mencegah Error 1452) ---
        if run_id == 0:
            log("error", "❌ Gagal menyimpan tabel induk (detection_run). Proses dibatalkan.")
            st.error("Gagal mendapat ID Run. Cek pesan error aslinya di log/terminal!")
            return
        # -------------------------------------------------

        log("info", f"Detection Run ID: {run_id}")

        # Simpan hasil per iklan
        prog.progress(0.9, "Menyimpan hasil deteksi...")
        labels, scores = model.predict_with_confidence(X)
        _save_results(run_id, df, labels, scores, model)

        prog.progress(1.0, "✅ Selesai!")
        log("ok", f"✅ ANFIS selesai! {len(X)} iklan telah diklasifikasikan.")
        log("ok", f"   Run ID: {run_id} | Cek halaman Hasil Deteksi.")

        log_activity(user_id, "ANFIS_RUN",
                     f"Run={run_name}, N={len(X)}, Acc={eval_metrics.get('accuracy')}")
        st.session_state.last_run_id = run_id
        show_alert(f"✅ Deteksi selesai! Lihat hasil di menu **Hasil Deteksi**.", "success")

    except Exception as e:
        import traceback
        log("error", f"ANFIS gagal: {e}")
        log("error", traceback.format_exc()[:500])


def _save_run(name, num_mf, lr, epochs, total, metrics, user_id) -> int:
    try:
        cfg = execute_query(
            "SELECT id FROM model_config WHERE is_active=1 LIMIT 1",
            fetch=True)
        cfg_id = cfg[0]["id"] if cfg else None

        run_id = execute_query(
            """INSERT INTO detection_run
               (run_name, config_id, total_data, processed_data,
                accuracy, precision_val, recall_val, f1_score,
                status, run_by, finished_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'completed',%s,NOW())""",
            (name, cfg_id, total, total,
             metrics.get("accuracy"), metrics.get("precision"),
             metrics.get("recall"), metrics.get("f1_score"), user_id)
        )
        return run_id
    except Exception as e:
        print(f"\n[ERROR DATABASE DI _save_run] -> {e}\n")
        st.error(f"Error query _save_run: {e}")
        return 0


def _save_results(run_id, df, labels, scores, model):
    try:
        iklan_rows = execute_query(
            """SELECT id, platform, claim_text,
                      label_manual, label_overclaim
               FROM dataset_iklan""",
            fetch=True)
        iklan_map = {r["id"]: r for r in iklan_rows}

        data_rows = []
        from models.anfis import LABEL_MAP, LABEL_MAP_INV, FEATURE_NAMES
        for i, row in df.iterrows():
            iklan_id = int(row["id"])
            iklan    = iklan_map.get(iklan_id, {})
            label    = LABEL_MAP.get(int(labels[i]), "tidak_overclaim")
            score    = float(scores[i])
            # Gunakan claim_text sebagai snippet
            snippet  = str(iklan.get("claim_text",""))[:300]
            asli     = iklan.get("label_manual")
            is_correct = (1 if asli and LABEL_MAP_INV.get(asli, 0) == int(labels[i])
                          else (0 if asli else None))
            # Ambil nilai 5 fitur ANFIS untuk explain
            feat_vals = []
            for fn in FEATURE_NAMES:
                feat_vals.append(float(df.iloc[i].get(fn, 0) or 0))
            x_row  = np.array(feat_vals)
            alasan = model.explain_prediction(x_row)
            data_rows.append((
                run_id, iklan_id,
                iklan.get("platform", "Lainnya"),
                snippet, label, score, score, asli,
                is_correct, alasan
            ))

        from config.database import execute_many
        execute_many(
            """INSERT INTO hasil_deteksi
               (run_id, iklan_id, platform, teks_iklan_snippet,
                kategori_overclaim, confidence_score, fuzzy_output,
                label_asli, is_correct, alasan_fuzzy)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            data_rows
        )
    except Exception as e:
        st.warning(f"Partial save error: {e}")


def _render_run_history():
    try:
        rows = execute_query(
            """SELECT r.id, r.run_name, r.total_data,
                      r.accuracy, r.precision_val, r.recall_val, r.f1_score,
                      r.status, r.started_at, u.full_name
               FROM detection_run r
               LEFT JOIN users u ON r.run_by=u.id
               ORDER BY r.id DESC LIMIT 10""",
            fetch=True
        )
        if not rows:
            show_alert("Belum ada riwayat deteksi.", "info")
            return

        df = pd.DataFrame(rows)
        df["accuracy"]    = df["accuracy"].apply(lambda x: f"{x*100:.1f}%" if x else "—")
        df["f1_score"]    = df["f1_score"].apply(lambda x: f"{x:.4f}" if x else "—")
        df["started_at"]  = pd.to_datetime(df["started_at"]).dt.strftime("%d/%m/%Y %H:%M")
        df["status"]      = df["status"].apply(
            lambda x: "✅ Selesai" if x=="completed" else "❌ Gagal" if x=="failed" else "⏳ Running"
        )
        st.dataframe(df.rename(columns={
            "id":"ID","run_name":"Nama Run","total_data":"Total Data",
            "accuracy":"Akurasi","precision_val":"Precision",
            "recall_val":"Recall","f1_score":"F1","status":"Status",
            "started_at":"Waktu","full_name":"Oleh"
        }), use_container_width=True, hide_index=True)
    except Exception as e:
        show_alert(f"Gagal memuat riwayat: {e}", "danger")