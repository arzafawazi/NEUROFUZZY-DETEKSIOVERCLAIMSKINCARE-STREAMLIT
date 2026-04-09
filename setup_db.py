"""
setup_db.py
Script setup awal: buat database, tabel, dan seed data demo.
Jalankan sekali sebelum menjalankan aplikasi:
    python setup_db.py
"""
import sys
import os
import bcrypt
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_raw_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        charset="utf8mb4",
        autocommit=True,
    )


def hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def run_setup():
    print("=" * 60)
    print("  NeuroFuzzy Skincare App — Database Setup")
    print("=" * 60)

    conn = get_raw_connection()
    cur  = conn.cursor()

    # 1. Buat database
    db_name = os.getenv("DB_NAME", "skincare_overclaim")
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute(f"USE `{db_name}`")
    print(f"✅ Database '{db_name}' siap.")

    # 2. Buat tabel users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        username    VARCHAR(100) NOT NULL UNIQUE,
        password    VARCHAR(255) NOT NULL,
        role        ENUM('admin','user') NOT NULL DEFAULT 'user',
        full_name   VARCHAR(150),
        email       VARCHAR(150) UNIQUE,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_login  DATETIME,
        is_active   TINYINT(1) DEFAULT 1
    ) ENGINE=InnoDB
    """)

    # 3. Tabel dataset_iklan
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dataset_iklan (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        platform     ENUM('Shopee','Tokopedia','Lazada','Bukalapak',
                          'Instagram','TikTok','Lainnya') NOT NULL DEFAULT 'Lainnya',
        brand        VARCHAR(200),
        teks_iklan   TEXT NOT NULL,
        label_manual ENUM('tidak_overclaim','rendah','sedang','tinggi'),
        sumber_file  VARCHAR(255),
        uploaded_by  INT,
        uploaded_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_processed TINYINT(1) DEFAULT 0,
        FOREIGN KEY (uploaded_by) REFERENCES users(id)
    ) ENGINE=InnoDB
    """)

    # 4. Tabel preprocessing_result
    cur.execute("""
    CREATE TABLE IF NOT EXISTS preprocessing_result (
        id             INT AUTO_INCREMENT PRIMARY KEY,
        iklan_id       INT NOT NULL,
        token_count    INT,
        tokens         TEXT,
        after_stopword TEXT,
        after_stemming TEXT,
        normalized_text TEXT,
        processed_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (iklan_id) REFERENCES dataset_iklan(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """)

    # 5. Tabel fitur_tekstual
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fitur_tekstual (
        id                INT AUTO_INCREMENT PRIMARY KEY,
        iklan_id          INT NOT NULL,
        tfidf_score       FLOAT,
        hyperbolic_count  INT DEFAULT 0,
        scientific_count  INT DEFAULT 0,
        absolute_count    INT DEFAULT 0,
        intensity_score   FLOAT DEFAULT 0,
        ngram_features    TEXT,
        exclamation_count INT DEFAULT 0,
        uppercase_ratio   FLOAT DEFAULT 0,
        avg_word_length   FLOAT DEFAULT 0,
        extracted_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (iklan_id) REFERENCES dataset_iklan(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """)

    # 6. Tabel model_config
    cur.execute("""
    CREATE TABLE IF NOT EXISTS model_config (
        id                       INT AUTO_INCREMENT PRIMARY KEY,
        config_name              VARCHAR(100) NOT NULL,
        num_membership_functions INT DEFAULT 3,
        membership_type          ENUM('triangular','trapezoidal','gaussian','bell')
                                 DEFAULT 'gaussian',
        num_fuzzy_rules          INT DEFAULT 9,
        learning_rate            FLOAT DEFAULT 0.01,
        epochs                   INT DEFAULT 100,
        train_split              FLOAT DEFAULT 0.8,
        created_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_active                TINYINT(1) DEFAULT 1
    ) ENGINE=InnoDB
    """)

    # 7. Tabel detection_run
    cur.execute("""
    CREATE TABLE IF NOT EXISTS detection_run (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        run_name      VARCHAR(150),
        config_id     INT,
        total_data    INT,
        processed_data INT DEFAULT 0,
        accuracy      FLOAT,
        precision_val FLOAT,
        recall_val    FLOAT,
        f1_score      FLOAT,
        status        ENUM('running','completed','failed') DEFAULT 'running',
        run_by        INT,
        started_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
        finished_at   DATETIME,
        log_text      TEXT,
        FOREIGN KEY (config_id) REFERENCES model_config(id),
        FOREIGN KEY (run_by)    REFERENCES users(id)
    ) ENGINE=InnoDB
    """)

    # 8. Tabel hasil_deteksi
    cur.execute("""
    CREATE TABLE IF NOT EXISTS hasil_deteksi (
        id                  INT AUTO_INCREMENT PRIMARY KEY,
        run_id              INT NOT NULL,
        iklan_id            INT NOT NULL,
        platform            VARCHAR(50),
        teks_iklan_snippet  VARCHAR(300),
        kategori_overclaim  ENUM('tidak_overclaim','rendah','sedang','tinggi') NOT NULL,
        confidence_score    FLOAT,
        fuzzy_output        FLOAT,
        label_asli          ENUM('tidak_overclaim','rendah','sedang','tinggi'),
        is_correct          TINYINT(1),
        alasan_fuzzy        TEXT,
        analyzed_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (run_id)   REFERENCES detection_run(id) ON DELETE CASCADE,
        FOREIGN KEY (iklan_id) REFERENCES dataset_iklan(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """)

    # 9. Tabel activity_log
    cur.execute("""
    CREATE TABLE IF NOT EXISTS activity_log (
        id         INT AUTO_INCREMENT PRIMARY KEY,
        user_id    INT,
        action     VARCHAR(200),
        detail     TEXT,
        ip_address VARCHAR(45),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    ) ENGINE=InnoDB
    """)

    print("✅ Semua tabel berhasil dibuat.")

    # ── Seed Users ────────────────────────────────────────────
    admin_pw = hash_pw("admin123")
    user_pw  = hash_pw("user123")

    for uname, pw, role, fname, email in [
        ("admin", admin_pw, "admin", "Administrator",  "admin@skincare.ac.id"),
        ("user1", user_pw,  "user",  "Pengguna Umum",  "user1@skincare.ac.id"),
    ]:
        cur.execute(
            "SELECT id FROM users WHERE username=%s", (uname,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users (username,password,role,full_name,email) "
                "VALUES (%s,%s,%s,%s,%s)",
                (uname, pw, role, fname, email))
            print(f"   👤 User '{uname}' dibuat (pass: {uname.replace('user1','user')}123)")
        else:
            print(f"   ℹ️  User '{uname}' sudah ada, dilewati.")

    # ── Seed model_config ─────────────────────────────────────
    cur.execute("SELECT id FROM model_config LIMIT 1")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO model_config (config_name) VALUES ('Default ANFIS Config')")
        print("✅ Default model config dibuat.")

    # ── Seed Data Demo Iklan ──────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM dataset_iklan")
    count = cur.fetchone()[0]
    if count == 0:
        demo_data = [
            ("Shopee", "Brand A",
             "Serum ini terbukti secara klinis memutihkan kulit 100% hanya dalam 7 hari! Dijamin ampuh!",
             "tinggi"),
            ("Tokopedia", "Brand B",
             "Pelembab wajah dengan kandungan hyaluronic acid, cocok untuk kulit kering dan kombinasi.",
             "tidak_overclaim"),
            ("Shopee", "Brand C",
             "Krim ajaib! Hilangkan jerawat selamanya tanpa efek samping, formula revolusioner!",
             "tinggi"),
            ("Instagram", "Brand D",
             "Sunscreen SPF 50 PA++++ melindungi dari sinar UVA dan UVB, ringan di kulit.",
             "tidak_overclaim"),
            ("Tokopedia", "Brand E",
             "Toner terbaik! Pori-pori mengecil dramatis, kulit langsung cerah maksimal!",
             "sedang"),
            ("TikTok", "Brand F",
             "Masker wajah alami dari bahan pilihan, cocok untuk semua jenis kulit.",
             "tidak_overclaim"),
            ("Lazada", "Brand G",
             "Eye cream super ampuh! Hapus kantung mata seketika, terlihat 10 tahun lebih muda!",
             "tinggi"),
            ("Shopee", "Brand H",
             "Essence brightening dengan niacinamide 10%, bantu meratakan warna kulit.",
             "rendah"),
            ("Bukalapak", "Brand I",
             "Sabun muka anti-aging permanen! Kulit awet muda abadi! Nomor 1 Indonesia!",
             "tinggi"),
            ("Tokopedia", "Brand J",
             "Body lotion dengan vitamin E dan C untuk kelembapan kulit sepanjang hari.",
             "tidak_overclaim"),
            ("Instagram", "Brand K",
             "Serum vitamin C 20% membantu mencerahkan kulit kusam dan mengurangi hiperpigmentasi.",
             "rendah"),
            ("Shopee", "Brand L",
             "Krim whitening instan! Putih sempurna dalam 3 hari, 100% dijamin atau uang kembali!",
             "tinggi"),
            ("TikTok", "Brand M",
             "Tinted moisturizer ringan untuk tampilan natural sehari-hari, SPF 30.",
             "tidak_overclaim"),
            ("Tokopedia", "Brand N",
             "Facial wash dengan AHA BHA membersihkan pori secara menyeluruh.",
             "rendah"),
            ("Shopee", "Brand O",
             "Retinol serum terdermis! Hapus kerutan wajah total permanen selamanya!",
             "tinggi"),
        ]
        cur.executemany(
            "INSERT INTO dataset_iklan (platform,brand,teks_iklan,label_manual,"
            "uploaded_by) VALUES (%s,%s,%s,%s,1)",
            demo_data
        )
        print(f"✅ {len(demo_data)} data iklan demo berhasil dimasukkan.")
    else:
        print(f"ℹ️  Data iklan sudah ada ({count} baris), seed demo dilewati.")

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print("  ✅ SETUP SELESAI!")
    print("  Jalankan aplikasi dengan:")
    print("      streamlit run app.py")
    print("  Login: admin / admin123  |  user1 / user123")
    print("=" * 60)


if __name__ == "__main__":
    run_setup()
