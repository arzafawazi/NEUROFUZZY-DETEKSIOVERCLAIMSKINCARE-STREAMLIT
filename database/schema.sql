-- ============================================================
-- SCHEMA DATABASE: Neurofuzzy Skincare Overclaim Detection
-- ============================================================

CREATE DATABASE IF NOT EXISTS skincare_overclaim
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE skincare_overclaim;

-- ============================================================
-- TABEL: users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(100) NOT NULL UNIQUE,
    password    VARCHAR(255) NOT NULL COMMENT 'bcrypt hashed',
    role        ENUM('admin', 'user') NOT NULL DEFAULT 'user',
    full_name   VARCHAR(150),
    email       VARCHAR(150) UNIQUE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login  DATETIME,
    is_active   TINYINT(1) DEFAULT 1
) ENGINE=InnoDB;

-- Seed: admin default (password: admin123)
INSERT INTO users (username, password, role, full_name, email)
VALUES (
    'admin',
    '$2b$12$KIX8FaLfOT5f47qIrgBpuOg7lmOJ7J77qS3iFRHvKCZy8S.FcJWJy',
    'admin',
    'Administrator',
    'admin@skincare.ac.id'
);

-- Seed: user default (password: user123)
INSERT INTO users (username, password, role, full_name, email)
VALUES (
    'user1',
    '$2b$12$3oGGdCz3yG8.5R0f6EJu8uMp5.rUvLSKqTBz7Y.a8PfD2F4mBk6Fy',
    'user',
    'Pengguna Umum',
    'user1@skincare.ac.id'
);

-- ============================================================
-- TABEL: dataset_iklan
-- ============================================================
CREATE TABLE IF NOT EXISTS dataset_iklan (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    platform        ENUM('Shopee','Tokopedia','Lazada','Bukalapak','Instagram','TikTok','Lainnya') NOT NULL,
    brand           VARCHAR(200),
    teks_iklan      TEXT NOT NULL,
    label_manual    ENUM('tidak_overclaim','rendah','sedang','tinggi') COMMENT 'Label dari anotator manusia',
    sumber_file     VARCHAR(255),
    uploaded_by     INT,
    uploaded_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_processed    TINYINT(1) DEFAULT 0,
    FOREIGN KEY (uploaded_by) REFERENCES users(id)
) ENGINE=InnoDB;

-- ============================================================
-- TABEL: preprocessing_result
-- ============================================================
CREATE TABLE IF NOT EXISTS preprocessing_result (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    iklan_id        INT NOT NULL,
    token_count     INT,
    tokens          TEXT COMMENT 'JSON array of tokens',
    after_stopword  TEXT,
    after_stemming  TEXT,
    normalized_text TEXT,
    processed_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (iklan_id) REFERENCES dataset_iklan(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- TABEL: fitur_tekstual
-- ============================================================
CREATE TABLE IF NOT EXISTS fitur_tekstual (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    iklan_id            INT NOT NULL,
    tfidf_score         FLOAT,
    hyperbolic_count    INT DEFAULT 0 COMMENT 'Jumlah kata hiperbolik',
    scientific_count    INT DEFAULT 0 COMMENT 'Jumlah klaim saintifik',
    absolute_count      INT DEFAULT 0 COMMENT 'Jumlah klaim absolut',
    intensity_score     FLOAT DEFAULT 0 COMMENT 'Skor intensitas kata',
    ngram_features      TEXT COMMENT 'JSON: top n-gram features',
    exclamation_count   INT DEFAULT 0,
    uppercase_ratio     FLOAT DEFAULT 0,
    avg_word_length     FLOAT DEFAULT 0,
    extracted_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (iklan_id) REFERENCES dataset_iklan(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- TABEL: model_config
-- ============================================================
CREATE TABLE IF NOT EXISTS model_config (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    config_name             VARCHAR(100) NOT NULL,
    num_membership_functions INT DEFAULT 3,
    membership_type         ENUM('triangular','trapezoidal','gaussian','bell') DEFAULT 'gaussian',
    num_fuzzy_rules         INT DEFAULT 9,
    learning_rate           FLOAT DEFAULT 0.01,
    epochs                  INT DEFAULT 100,
    train_split             FLOAT DEFAULT 0.8,
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active               TINYINT(1) DEFAULT 1
) ENGINE=InnoDB;

INSERT INTO model_config (config_name, num_membership_functions, membership_type, num_fuzzy_rules, learning_rate, epochs)
VALUES ('Default ANFIS Config', 3, 'gaussian', 9, 0.01, 100);

-- ============================================================
-- TABEL: detection_run
-- ============================================================
CREATE TABLE IF NOT EXISTS detection_run (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    run_name        VARCHAR(150),
    config_id       INT,
    total_data      INT,
    processed_data  INT DEFAULT 0,
    accuracy        FLOAT,
    precision_val   FLOAT,
    recall_val      FLOAT,
    f1_score        FLOAT,
    status          ENUM('running','completed','failed') DEFAULT 'running',
    run_by          INT,
    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at     DATETIME,
    log_text        TEXT,
    FOREIGN KEY (config_id) REFERENCES model_config(id),
    FOREIGN KEY (run_by) REFERENCES users(id)
) ENGINE=InnoDB;

-- ============================================================
-- TABEL: hasil_deteksi
-- ============================================================
CREATE TABLE IF NOT EXISTS hasil_deteksi (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    run_id              INT NOT NULL,
    iklan_id            INT NOT NULL,
    platform            VARCHAR(50),
    teks_iklan_snippet  VARCHAR(300),
    kategori_overclaim  ENUM('tidak_overclaim','rendah','sedang','tinggi') NOT NULL,
    confidence_score    FLOAT COMMENT '0-1 confidence dari ANFIS',
    fuzzy_output        FLOAT COMMENT 'Raw fuzzy output sebelum defuzzifikasi',
    label_asli          ENUM('tidak_overclaim','rendah','sedang','sedang','tinggi'),
    is_correct          TINYINT(1) COMMENT '1=prediksi benar, 0=salah',
    alasan_fuzzy        TEXT COMMENT 'Interpretasi aturan fuzzy aktif',
    analyzed_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES detection_run(id) ON DELETE CASCADE,
    FOREIGN KEY (iklan_id) REFERENCES dataset_iklan(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- TABEL: activity_log
-- ============================================================
CREATE TABLE IF NOT EXISTS activity_log (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT,
    action      VARCHAR(200),
    detail      TEXT,
    ip_address  VARCHAR(45),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB;
