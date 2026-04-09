# 🧬 NeuroFuzzy Skincare Overclaim Detector

**Implementasi Neurofuzzy untuk Deteksi Dini Overclaim pada Iklan Skincare**  
dengan Memanfaatkan Fitur-Fitur Tekstual dari Platform E-Commerce

---

## 🗂️ Struktur Proyek

```
skincare_overclaim_app/
├── app.py                      ← Entry point utama
├── setup_db.py                 ← Script setup database (jalankan sekali)
├── requirements.txt            ← Dependensi Python
├── .env.example                ← Template konfigurasi environment
├── .streamlit/
│   └── config.toml             ← Konfigurasi tema Streamlit
│
├── config/
│   ├── __init__.py
│   └── database.py             ← Koneksi MySQL (connection pool)
│
├── pages/
│   ├── __init__.py
│   ├── login.py                ← Halaman Login (Admin & User)
│   ├── dashboard.py            ← Dashboard + Grafik Analitik
│   ├── data_iklan.py           ← Upload & Kelola Dataset
│   ├── proses_deteksi.py       ← Pipeline Preprocessing → ANFIS
│   └── hasil_deteksi.py        ← Output Klasifikasi + Filter
│
├── models/
│   ├── __init__.py
│   ├── preprocessor.py         ← Tokenisasi, stopword, Sastrawi stemming
│   └── anfis.py                ← Implementasi ANFIS (Neuro-Fuzzy)
│
├── utils/
│   ├── __init__.py
│   ├── auth.py                 ← Login, session, bcrypt
│   ├── ui_helpers.py           ← CSS tema pink, komponen UI
│   └── feature_extractor.py   ← TF-IDF, N-gram, fitur tekstual
│
├── database/
│   └── schema.sql              ← Schema SQL lengkap (referensi)
│
└── assets/
    └── sample_dataset.csv      ← Dataset demo 30 iklan berlabel
```

---

## ⚙️ Prasyarat Sistem

| Komponen       | Versi Minimal |
|----------------|---------------|
| Python         | 3.9+          |
| MySQL Server   | 8.0+          |
| pip            | 23+           |
| RAM            | 4 GB          |

---

## 🚀 Langkah Instalasi & Menjalankan

### LANGKAH 1 — Clone / Salin Proyek

```bash
# Salin seluruh folder ke direktori Anda
cd /path/ke/folder/kerja
```

### LANGKAH 2 — Buat Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### LANGKAH 3 — Install Dependensi

```bash
pip install -r requirements.txt
```

> ⚠️ **Catatan NLTK**: Saat pertama run, NLTK akan otomatis download
> `punkt` tokenizer. Pastikan ada koneksi internet.

> ⚠️ **Catatan PySastrawi**: Jika instalasi gagal di Windows, coba:
> ```bash
> pip install PySastrawi --no-build-isolation
> ```

### LANGKAH 4 — Konfigurasi Database MySQL

4a. Pastikan MySQL Server berjalan di komputer Anda.

4b. Salin file `.env.example` menjadi `.env`:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

4c. Edit file `.env` sesuai konfigurasi MySQL Anda:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=skincare_overclaim
DB_USER=root
DB_PASSWORD=password_mysql_anda

SECRET_KEY=ganti-dengan-string-acak-yang-kuat
```

### LANGKAH 5 — Setup Database (Jalankan Sekali)

```bash
python setup_db.py
```

Output yang diharapkan:
```
============================================================
  NeuroFuzzy Skincare App — Database Setup
============================================================
✅ Database 'skincare_overclaim' siap.
✅ Semua tabel berhasil dibuat.
   👤 User 'admin' dibuat (pass: admin123)
   👤 User 'user1' dibuat (pass: user123)
✅ Default model config dibuat.
✅ 15 data iklan demo berhasil dimasukkan.

============================================================
  ✅ SETUP SELESAI!
  Jalankan aplikasi dengan:
      streamlit run app.py
  Login: admin / admin123  |  user1 / user123
============================================================
```

### LANGKAH 6 — Jalankan Aplikasi

```bash
streamlit run app.py
```

Buka browser ke: **http://localhost:8501**

---

## 👤 Akun Default

| Role  | Username | Password |
|-------|----------|----------|
| Admin | `admin`  | `admin123` |
| User  | `user1`  | `user123`  |

> ⚠️ Segera ganti password setelah login pertama di production!

---

## 📖 Panduan Penggunaan

### Alur Kerja Sistem (untuk Admin)

```
1. Login sebagai Admin
        ↓
2. Halaman "Data Iklan"
   → Upload file CSV/Excel dataset iklan skincare
   → Atau gunakan sample_dataset.csv yang tersedia
        ↓
3. Halaman "Proses Deteksi"
   → Atur konfigurasi ANFIS (MF, learning rate, epochs)
   → Klik "Jalankan Semua" atau step-by-step
   → Monitoring via Log Area
        ↓
4. Halaman "Hasil Deteksi"
   → Lihat hasil klasifikasi overclaim
   → Filter by platform, kategori, tanggal
   → Export ke CSV / Excel
```

### Halaman User
- **Dashboard**: Statistik & grafik ringkasan
- **Hasil Deteksi**: Melihat hasil (tidak bisa jalankan proses)

---

## 🧠 Arsitektur ANFIS

### Input Features (Variabel Independen)
| Fitur | Deskripsi |
|-------|-----------|
| `intensity_score` | Skor intensitas kata (hiperbolik + seru + kapital) |
| `hyperbolic_count` | Jumlah kata hiperbolik (ajaib, terbaik, super, dst.) |
| `absolute_count` | Jumlah klaim absolut (100%, pasti, dijamin, dst.) |
| `scientific_count` | Jumlah klaim saintifik (klinis, dermatologis, dst.) |
| `tfidf_score` | Rata-rata skor TF-IDF dokumen |
| `exclamation_count` | Jumlah tanda seru |
| `uppercase_ratio` | Rasio kata huruf kapital |

### Output (Variabel Dependen)
| Kategori | Rentang Score |
|----------|--------------|
| `tidak_overclaim` | 0.00 – 0.25 |
| `rendah` | 0.25 – 0.50 |
| `sedang` | 0.50 – 0.75 |
| `tinggi` | 0.75 – 1.00 |

### Pipeline ANFIS (5 Layer)
```
Layer 1: Fuzzifikasi   → Membership Functions (Gaussian)
Layer 2: Rule Firing   → Produk antecedent per aturan
Layer 3: Normalisasi   → Normalized firing strength
Layer 4: Consequent    → TSK linear output per aturan
Layer 5: Defuzzifikasi → Weighted average → skor [0,1]
```

### Training: Hybrid Learning
- **Consequent parameters** → Least Squares Estimation (LSE)
- **Premise parameters (MF)** → Gradient Descent Backpropagation

---

## 🔧 Variabel Kontrol

| Kontrol | Nilai Default |
|---------|---------------|
| Tokenizer | NLTK word_tokenize |
| Stopword | PySastrawi + custom |
| Stemmer | PySastrawi Stemmer |
| Fitur representasi | TF-IDF (max_features=500, ngram=(1,2)) |
| Normalisasi fitur | MinMaxScaler [0,1] |
| Python versi | 3.9+ |

---

## 🐛 Troubleshooting

### ❌ Error: `Access denied for user 'root'@'localhost'`
→ Periksa `DB_USER` dan `DB_PASSWORD` di file `.env`

### ❌ Error: `ModuleNotFoundError: No module named 'Sastrawi'`
```bash
pip install PySastrawi
```

### ❌ Error: `No module named 'skfuzzy'`
```bash
pip install scikit-fuzzy
```

### ❌ Halaman blank / tidak tampil
→ Pastikan menjalankan: `streamlit run app.py`  
→ Bukan: `python app.py`

### ❌ ANFIS loss sangat besar
→ Kurangi learning rate ke `0.001`  
→ Tambah epochs ke `200`  
→ Pastikan data memiliki label manual yang bervariasi (bukan semua satu kelas)

### ❌ Sastrawi stemmer lambat
→ Normal untuk batch besar. Sastrawi memproses per kata.  
→ Untuk >1000 data, proses bisa memakan 1-3 menit.

---

## 📦 Teknologi yang Digunakan

| Komponen | Library |
|----------|---------|
| Frontend | Streamlit + Bootstrap 5 |
| Database | MySQL + mysql-connector-python |
| NLP | NLTK, PySastrawi |
| Feature Extraction | scikit-learn TF-IDF |
| Neuro-Fuzzy | Implementasi custom + scikit-fuzzy |
| Visualisasi | Plotly |
| Auth | bcrypt |
| Data | pandas, numpy |

---

## 📞 Kontak & Lisensi

Dibuat untuk keperluan penelitian skripsi/tesis.  
Silakan dikembangkan lebih lanjut sesuai kebutuhan.
