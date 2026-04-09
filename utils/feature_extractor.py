"""
utils/feature_extractor.py
Ekstraksi fitur TF-IDF, n-gram, dan kompilasi fitur untuk ANFIS
"""
import json
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler
from models.preprocessor import full_preprocess, count_feature_words
from config.database import execute_query, execute_many


# ── TF-IDF global (difit saat preprocessing batch) ───────────
_tfidf_vectorizer = None
_scaler           = None


def fit_tfidf(corpus: list) -> TfidfVectorizer:
    global _tfidf_vectorizer
    _tfidf_vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=500,
        sublinear_tf=True,
        min_df=1,
    )
    _tfidf_vectorizer.fit(corpus)
    return _tfidf_vectorizer


def get_tfidf_score(text: str) -> float:
    """Rata-rata TF-IDF skor seluruh token dalam teks."""
    if _tfidf_vectorizer is None:
        return 0.0
    vec = _tfidf_vectorizer.transform([text])
    arr = vec.toarray()[0]
    nonzero = arr[arr > 0]
    return float(np.mean(nonzero)) if len(nonzero) > 0 else 0.0


def get_top_ngrams(text: str, top_n: int = 5) -> list:
    """Ambil top-N n-gram berdasarkan TF-IDF dari satu dokumen."""
    if _tfidf_vectorizer is None:
        return []
    vec = _tfidf_vectorizer.transform([text])
    feature_names = _tfidf_vectorizer.get_feature_names_out()
    scores = vec.toarray()[0]
    top_idx = scores.argsort()[::-1][:top_n]
    return [{"ngram": feature_names[i], "score": round(float(scores[i]), 4)}
            for i in top_idx if scores[i] > 0]


def extract_all_features(iklan_id: int, teks: str) -> dict:
    """
    Ekstrak semua fitur tekstual untuk satu iklan.
    Kembalikan dict siap insert ke tabel fitur_tekstual.
    """
    preprocessed = full_preprocess(teks)
    text_for_tfidf = preprocessed["after_stemming"] or preprocessed["normalized"]
    word_features  = count_feature_words(teks)
    tfidf_score    = get_tfidf_score(text_for_tfidf)
    ngrams         = get_top_ngrams(text_for_tfidf)

    return {
        "iklan_id":         iklan_id,
        "tfidf_score":      round(tfidf_score, 6),
        "hyperbolic_count": word_features["hyperbolic_count"],
        "scientific_count": word_features["scientific_count"],
        "absolute_count":   word_features["absolute_count"],
        "intensity_score":  word_features["intensity_score"],
        "ngram_features":   json.dumps(ngrams, ensure_ascii=False),
        "exclamation_count":word_features["exclamation_count"],
        "uppercase_ratio":  word_features["uppercase_ratio"],
        "avg_word_length":  word_features["avg_word_length"],
    }


def preprocess_batch(iklan_list: list, log_callback=None) -> pd.DataFrame:
    """
    Jalankan preprocessing untuk semua iklan.
    iklan_list: list of dict dengan keys 'id', 'teks_iklan'
    Kembalikan DataFrame fitur.
    """
    records    = []
    prep_rows  = []
    fitur_rows = []

    # Kumpulkan teks bersih untuk fit TF-IDF
    clean_texts = []
    for iklan in iklan_list:
        p = full_preprocess(iklan["teks_iklan"])
        clean_texts.append(p["after_stemming"] or p["normalized"])
        prep_rows.append({
            "iklan_id":       iklan["id"],
            "token_count":    p["token_count"],
            "tokens":         p["tokens"],
            "after_stopword": p["after_stopword"],
            "after_stemming": p["after_stemming"],
            "normalized_text":p["normalized"],
        })

    if log_callback:
        log_callback("info", f"Fitting TF-IDF pada {len(clean_texts)} dokumen...")

    fit_tfidf(clean_texts)

    # Insert preprocessing
    try:
        execute_many(
            """INSERT INTO preprocessing_result
               (iklan_id, token_count, tokens, after_stopword, after_stemming, normalized_text)
               VALUES (%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
               token_count=VALUES(token_count), tokens=VALUES(tokens)""",
            [(r["iklan_id"], r["token_count"], r["tokens"],
              r["after_stopword"], r["after_stemming"], r["normalized_text"])
             for r in prep_rows]
        )
    except Exception as e:
        if log_callback:
            log_callback("warn", f"Insert preprocessing (diabaikan): {e}")

    if log_callback:
        log_callback("info", "Mengekstrak fitur tekstual...")

    # Ekstrak fitur per iklan
    for iklan, clean in zip(iklan_list, clean_texts):
        f = extract_all_features(iklan["id"], iklan["teks_iklan"])
        fitur_rows.append(f)
        records.append({
            "id":               iklan["id"],
            "teks_iklan":       iklan["teks_iklan"],
            "tfidf_score":      f["tfidf_score"],
            "hyperbolic_count": f["hyperbolic_count"],
            "scientific_count": f["scientific_count"],
            "absolute_count":   f["absolute_count"],
            "intensity_score":  f["intensity_score"],
            "exclamation_count":f["exclamation_count"],
            "uppercase_ratio":  f["uppercase_ratio"],
            "avg_word_length":  f["avg_word_length"],
        })

    # Insert fitur
    try:
        execute_many(
            """INSERT INTO fitur_tekstual
               (iklan_id, tfidf_score, hyperbolic_count, scientific_count,
                absolute_count, intensity_score, ngram_features,
                exclamation_count, uppercase_ratio, avg_word_length)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE tfidf_score=VALUES(tfidf_score)""",
            [(r["iklan_id"], r["tfidf_score"], r["hyperbolic_count"],
              r["scientific_count"], r["absolute_count"], r["intensity_score"],
              r["ngram_features"], r["exclamation_count"],
              r["uppercase_ratio"], r["avg_word_length"])
             for r in fitur_rows]
        )
    except Exception as e:
        if log_callback:
            log_callback("warn", f"Insert fitur (diabaikan): {e}")

    # Update is_processed
    try:
        ids = [i["id"] for i in iklan_list]
        placeholders = ",".join(["%s"] * len(ids))
        execute_query(
            f"UPDATE dataset_iklan SET is_processed=1 WHERE id IN ({placeholders})",
            tuple(ids)
        )
    except Exception:
        pass

    df = pd.DataFrame(records)

    # Normalisasi fitur numerik ke [0,1]
    num_cols = ["tfidf_score", "hyperbolic_count", "scientific_count",
                "absolute_count", "intensity_score", "exclamation_count",
                "uppercase_ratio", "avg_word_length"]
    global _scaler
    _scaler = MinMaxScaler()
    df[num_cols] = _scaler.fit_transform(df[num_cols])

    return df
