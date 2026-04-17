"""
setup_db.py
Script setup awal: buat database, tabel, dan seed data demo.
Jalankan sekali sebelum menjalankan aplikasi:
    python setup_db.py
"""
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

    db_name = os.getenv("DB_NAME", "skincare_overclaim")
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute(f"USE `{db_name}`")
    print(f"✅ Database '{db_name}' siap.")

    # ── Tabel users ───────────────────────────────────────────
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

    # ── Tabel dataset_iklan (skema lengkap baru) ──────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dataset_iklan (
        id              INT AUTO_INCREMENT PRIMARY KEY,

        product_id      VARCHAR(100)    COMMENT 'ID produk dari sumber data',
        brand           VARCHAR(200),
        product_name    VARCHAR(300),
        category        VARCHAR(150),

        platform        ENUM('Shopee','Tokopedia','Lazada','Bukalapak',
                             'Instagram','TikTok','Lainnya')
                        NOT NULL DEFAULT 'Lainnya',
        price           DECIMAL(15,2),
        rating          FLOAT,
        total_review    INT,

        claim_text      TEXT        NOT NULL COMMENT 'Teks klaim iklan utama',
        ingredients     TEXT        COMMENT 'Daftar bahan/kandungan produk',
        review_text     TEXT        COMMENT 'Teks ulasan pembeli',

        review_length   INT         COMMENT 'Panjang karakter review_text',
        claim_length    INT         COMMENT 'Panjang karakter claim_text',

        label_overclaim TINYINT(1)  COMMENT '0=tidak overclaim, 1=overclaim',
        label_manual    ENUM('tidak_overclaim','rendah','sedang','tinggi')
                        COMMENT 'Label 4-kelas ANFIS (diturunkan otomatis jika kosong)',

        sumber_file     VARCHAR(255),
        uploaded_by     INT,
        uploaded_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_processed    TINYINT(1) DEFAULT 0,

        FOREIGN KEY (uploaded_by) REFERENCES users(id)
    ) ENGINE=InnoDB
    """)

    # ── Tabel preprocessing_result ────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS preprocessing_result (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        iklan_id        INT NOT NULL,
        token_count     INT,
        tokens          TEXT,
        after_stopword  TEXT,
        after_stemming  TEXT,
        normalized_text TEXT,
        processed_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (iklan_id) REFERENCES dataset_iklan(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """)

    # ── Tabel fitur_tekstual (diperluas) ──────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fitur_tekstual (
        id                   INT AUTO_INCREMENT PRIMARY KEY,
        iklan_id             INT NOT NULL,
        tfidf_score          FLOAT,
        ngram_features       TEXT,
        hyperbolic_count     INT   DEFAULT 0,
        scientific_count     INT   DEFAULT 0,
        absolute_count       INT   DEFAULT 0,
        intensity_score      FLOAT DEFAULT 0,
        exclamation_count    INT   DEFAULT 0,
        uppercase_ratio      FLOAT DEFAULT 0,
        avg_word_length      FLOAT DEFAULT 0,
        claim_length_norm    FLOAT DEFAULT 0,
        review_length_norm   FLOAT DEFAULT 0,
        rating_norm          FLOAT DEFAULT 0,
        ingredient_count     INT   DEFAULT 0,
        ingredient_scientific INT  DEFAULT 0,
        extracted_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (iklan_id) REFERENCES dataset_iklan(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """)

    # ── Tabel model_config ────────────────────────────────────
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

    # ── Tabel detection_run ───────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS detection_run (
        id             INT AUTO_INCREMENT PRIMARY KEY,
        run_name       VARCHAR(150),
        config_id      INT,
        total_data     INT,
        processed_data INT DEFAULT 0,
        accuracy       FLOAT,
        precision_val  FLOAT,
        recall_val     FLOAT,
        f1_score       FLOAT,
        status         ENUM('running','completed','failed') DEFAULT 'running',
        run_by         INT,
        started_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
        finished_at    DATETIME,
        log_text       TEXT,
        FOREIGN KEY (config_id) REFERENCES model_config(id),
        FOREIGN KEY (run_by)    REFERENCES users(id)
    ) ENGINE=InnoDB
    """)

    # ── Tabel hasil_deteksi ───────────────────────────────────
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

    # ── Tabel activity_log ────────────────────────────────────
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
    for uname, pw_plain, role, fname, email in [
        ("admin", "admin123", "admin", "Administrator", "admin@skincare.ac.id"),
        ("user1", "user123",  "user",  "Pengguna Umum", "user1@skincare.ac.id"),
    ]:
        cur.execute("SELECT id FROM users WHERE username=%s", (uname,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users (username,password,role,full_name,email) VALUES (%s,%s,%s,%s,%s)",
                (uname, hash_pw(pw_plain), role, fname, email)
            )
            print(f"   👤 User '{uname}' dibuat (pass: {pw_plain})")
        else:
            print(f"   ℹ️  User '{uname}' sudah ada, dilewati.")

    # ── Seed model_config ─────────────────────────────────────
    cur.execute("SELECT id FROM model_config LIMIT 1")
    if not cur.fetchone():
        cur.execute("INSERT INTO model_config (config_name) VALUES ('Default ANFIS Config')")
        print("✅ Default model config dibuat.")

    # ── Seed Data Demo Iklan ──────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM dataset_iklan")
    count = cur.fetchone()[0]

    if count == 0:
        # urutan: product_id, brand, product_name, category, platform,
        #         price, rating, total_review, claim_text, ingredients,
        #         review_text, review_length, claim_length, label_overclaim, uploaded_by
        demo_data = [
            ("501","Scarlett","Scarlett Sunscreen Series 8","Sunscreen","Shopee",
             106150,4.8,2070,
             "secara bertahap mencerahkan dan menyamarkan noda hitam hasil dapat berbeda",
             "Tea Tree, Vitamin C, Centella Asiatica, Hyaluronic Acid",
             "Efeknya biasa saja.",3,10,0,1),

            ("502","Somethinc","Somethinc Niacinamide 10% Serum","Serum","Tokopedia",
             129000,4.7,5430,
             "100% terbukti memutihkan kulit dalam 7 hari dijamin atau uang kembali!",
             "Niacinamide 10%, Zinc PCA, Aqua",
             "Kulit terasa lebih cerah setelah 2 minggu.",19,8,1,1),

            ("503","Wardah","Wardah Lightening Series Moisturizer","Moisturizer","Shopee",
             45000,4.5,8900,
             "melembapkan dan merawat kulit wajah untuk tampilan lebih sehat",
             "Vitamin E, Aloe Vera Extract, Glycerin",
             "Bagus untuk kulit kering, tidak lengket.",5,8,0,1),

            ("504","Ms Glow","Ms Glow Whitening Cream","Whitening","Instagram",
             250000,4.2,12000,
             "putih permanen dalam 3 hari pemakaian rutin! ampuh 100% dijamin!",
             "Mercury (trace), Hydroquinone, Tretinoin",
             "Cepat putih tapi kulit jadi tipis.",6,10,1,1),

            ("505","COSRX","COSRX Advanced Snail 96 Mucin Power Essence","Essence","Tokopedia",
             215000,4.9,3200,
             "membantu memperbaiki skin barrier dan melembapkan kulit secara intensif",
             "Snail Secretion Filtrate 96%, Sodium Hyaluronate, Allantoin",
             "Tekstur lengket tapi kulit jadi lembap banget.",8,11,0,1),

            ("506","Emina","Emina Sun Protection SPF 30","Sunscreen","Shopee",
             38000,4.3,6700,
             "lindungi kulit dari paparan sinar matahari setiap hari",
             "Titanium Dioxide, Zinc Oxide, Aloe Vera",
             "Ringan dan tidak membekas di kulit.",3,7,0,1),

            ("507","Hanasui","Hanasui Tinted Lip Serum","Lip Care","TikTok",
             25000,4.6,9800,
             "bibir merah muda alami selamanya! hasilkan bibir sempurna abadi!",
             "Collagen, Vitamin E, Sweet Almond Oil",
             "Warnanya natural, tapi tidak permanen.",9,10,1,1),

            ("508","The Originote","The Originote Ceramide Moisturizer","Moisturizer","Tokopedia",
             55000,4.7,4100,
             "memperkuat skin barrier dan mencegah kehilangan kelembapan kulit",
             "Ceramide NP, Ceramide AP, Ceramide EOP, Hyaluronic Acid",
             "Sangat cocok untuk kulit sensitif saya.",6,9,0,1),

            ("509","Natasha","Natasha Whitening Serum","Whitening","Shopee",
             320000,3.8,1500,
             "cerahkan kulit gelap jadi putih bersih sempurna dalam 5 hari!",
             "Arbutin, Kojic Acid, Vitamin C",
             "Lumayan tapi hasilnya tidak secepat klaim.",12,11,1,1),

            ("510","Bioderma","Bioderma Sensibio H2O Micellar Water","Cleanser","Lazada",
             185000,4.8,2800,
             "membersihkan makeup dan kotoran dengan lembut tanpa perlu dibilas",
             "Aqua, PEG-6 Caprylic/Capric Glycerides, Cucurbit Pepo Extract",
             "Terbaik untuk kulit sensitif, tidak perih.",4,9,0,1),

            ("511","Azarine","Azarine Hydrasoothe Sunscreen Gel SPF 45","Sunscreen","Shopee",
             59000,4.8,15600,
             "sunscreen gel ringan anti-lengket cocok untuk kulit berminyak dan berjerawat",
             "Centella Asiatica, Niacinamide, Hyaluronic Acid, SPF 45 PA++++",
             "Favorit! Tidak bikin kulit makin berminyak.",5,11,0,1),

            ("512","Scarlett","Scarlett Brightly Ever After Serum","Serum","Tokopedia",
             100000,4.5,7800,
             "kulit langsung cerah bersinar total merata hanya dalam 1x pakai!",
             "Niacinamide, Vitamin C, Alpha Arbutin",
             "Perlu waktu setidaknya 2 minggu untuk melihat perubahan.",11,10,1,1),

            ("513","Cetaphil","Cetaphil Gentle Skin Cleanser","Cleanser","Tokopedia",
             120000,4.9,4500,
             "formula lembut tidak mengiritasi cocok untuk kulit sensitif dan bermasalah",
             "Aqua, Cetyl Alcohol, Propylene Glycol, Butylene Glycol",
             "Sudah pakai bertahun-tahun, kulit tetap aman.",5,9,0,1),

            ("514","Y.O.U","Y.O.U Whitening Day Cream SPF 30","Whitening","Shopee",
             49000,4.1,3200,
             "hilangkan flek hitam noda jerawat secara maksimal permanen terbukti 100%!",
             "Vitamin C, Niacinamide, SPF 30 Filter",
             "Ada perubahan sedikit tapi tidak seperti yang diklaim.",12,9,1,1),

            ("515","Garnier","Garnier Bright Complete Vitamin C Serum","Serum","Lazada",
             75000,4.4,9100,
             "mencerahkan kulit kusam dengan kandungan Vitamin C aktif diformulasikan oleh dermatologis",
             "Ascorbic Acid 30x, Salicylic Acid, Lemon Extract",
             "Kulit terasa lebih cerah setelah 1 bulan.",5,10,0,1),

            ("516","Revlon","Revlon Photoready Primer","Primer","Instagram",
             180000,4.0,890,
             "hilangkan semua pori-pori wajah seketika tampak mulus total sempurna!",
             "Dimethicone, Cyclopentasiloxane, Niacinamide",
             "Menutupi pori sementara, bukan menghilangkan.",11,10,1,1),

            ("517","La Roche-Posay","La Roche-Posay Toleriane Double Repair Moisturizer","Moisturizer","Tokopedia",
             390000,4.9,2100,
             "memperbaiki skin barrier dalam 1 jam terbukti secara dermatologis uji klinis",
             "Ceramide 3, Niacinamide, Prebiotic Thermal Water",
             "Mahal tapi worth it untuk kulit sensitif.",5,9,0,1),

            ("518","Kahf","Kahf Beyond Your Limits Face Wash","Cleanser","Shopee",
             35000,4.6,11200,
             "bersihkan wajah dari kotoran dan minyak berlebih untuk kulit segar",
             "Charcoal, Salicylic Acid, Menthol",
             "Segar banget di wajah, cocok untuk pria aktif.",4,8,0,1),

            ("519","Clio","Clio Kill Lash Superproof Mascara","Makeup","TikTok",
             165000,4.5,4300,
             "bulu mata lentik panjang abadi sempurna 24 jam anti air 100% tahan segala kondisi!",
             "Aqua, Beeswax, Carnauba Wax, Iron Oxides",
             "Tahan lama, tapi tidak 100% anti air.",12,9,1,1),

            ("520","Vaseline","Vaseline Intensive Care Body Lotion","Body Care","Tokopedia",
             45000,4.7,18900,
             "melembapkan kulit tubuh kering dengan perlindungan kelembapan lebih baik",
             "Water, Glycerin, Stearic Acid, Petrolatum",
             "Kulit jadi lembap, harga terjangkau.",4,8,0,1),
        ]

        cur.executemany(
            """INSERT INTO dataset_iklan
               (product_id, brand, product_name, category, platform,
                price, rating, total_review, claim_text, ingredients,
                review_text, review_length, claim_length, label_overclaim, uploaded_by)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            demo_data
        )
        print(f"✅ {len(demo_data)} data iklan demo berhasil dimasukkan.")
    else:
        print(f"ℹ️  Data iklan sudah ada ({count} baris), seed demo dilewati.")

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print("  ✅ SETUP SELESAI!")
    print("  Jalankan: streamlit run app.py")
    print("  Login: admin / admin123  |  user1 / user123")
    print("=" * 60)


if __name__ == "__main__":
    run_setup()
