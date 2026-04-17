"""
utils/feature_extractor.py
Ekstraksi fitur tekstual untuk tabel skema baru.

Kolom sumber dari dataset_iklan:
  claim_text, ingredients, review_text,
  review_length, claim_length, rating

Fitur yang diekstrak → tabel fitur_tekstual:
  tfidf_score, hyperbolic_count, scientific_count,
  absolute_count, intensity_score, exclamation_count,
  uppercase_ratio, avg_word_length, ngram_features,
  ingredient_count, ingredient_scientific,
  claim_length_norm, review_length_norm, rating_norm
"""
import json
import numpy as np
import pandas as pd
from typing import Union
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler
from models.preprocessor import full_preprocess, count_feature_words
from config.database import execute_query, execute_many

# ── Bahan/ingredient yang termasuk "scientific claim" ─────────
SCIENTIFIC_INGREDIENTS = {
    "retinol", "niacinamide", "hyaluronic acid", "vitamin c", "vitamin e",
    "ascorbic acid", "peptide", "ceramide", "aha", "bha", "pha",
    "salicylic acid", "glycolic acid", "lactic acid", "kojic acid",
    "alpha arbutin", "tranexamic acid", "centella asiatica", "zinc oxide",
    "titanium dioxide", "spf", "uva", "uvb", "collagen", "snail secretion",
    "benzoyl peroxide", "azelaic acid", "ferulic acid", "squalane",
}

# ── Global state ───────────────────────────────────────────────
_tfidf_vectorizer: Union[TfidfVectorizer, None] = None
_scaler: Union[MinMaxScaler, None] = None


# ── TF-IDF ─────────────────────────────────────────────────────
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
    if _tfidf_vectorizer is None or not text:
        return 0.0
    vec = _tfidf_vectorizer.transform([text])
    arr = vec.toarray()[0]
    nonzero = arr[arr > 0]
    return float(np.mean(nonzero)) if len(nonzero) > 0 else 0.0


def get_top_ngrams(text: str, top_n: int = 5) -> list:
    if _tfidf_vectorizer is None or not text:
        return []
    vec   = _tfidf_vectorizer.transform([text])
    names = _tfidf_vectorizer.get_feature_names_out()
    scores = vec.toarray()[0]
    top_idx = scores.argsort()[::-1][:top_n]
    return [{"ngram": names[i], "score": round(float(scores[i]), 4)}
            for i in top_idx if scores[i] > 0]


# ── Fitur dari ingredients ─────────────────────────────────────
def analyze_ingredients(ingredients: str) -> dict:
    """
    Hitung jumlah bahan dan jumlah bahan yang termasuk
    scientific / active ingredient.
    """
    if not ingredients:
        return {"ingredient_count": 0, "ingredient_scientific": 0}
    parts   = [p.strip().lower() for p in ingredients.split(",") if p.strip()]
    sci_cnt = sum(1 for p in parts
                  if any(s in p for s in SCIENTIFIC_INGREDIENTS))
    return {
        "ingredient_count":      len(parts),
        "ingredient_scientific": sci_cnt,
    }


# ── Ekstraksi semua fitur untuk satu iklan ─────────────────────
def extract_all_features(row: dict) -> dict:
    """
    row harus memiliki key:
      id, claim_text, ingredients (optional),
      review_length (optional), claim_length (optional),
      rating (optional)
    """
    iklan_id    = row["id"]
    claim_text  = str(row.get("claim_text") or "")
    ingredients = str(row.get("ingredients") or "")
    rating      = row.get("rating")

    # Preprocessing claim_text
    preprocessed   = full_preprocess(claim_text)
    clean_for_tfidf = preprocessed["after_stemming"] or preprocessed["normalized"]

    # Fitur kata
    word_feats = count_feature_words(claim_text)

    # TF-IDF
    tfidf_score = get_tfidf_score(clean_for_tfidf)
    ngrams      = get_top_ngrams(clean_for_tfidf)

    # Fitur ingredients
    ing_feats = analyze_ingredients(ingredients)

    # Normalisasi panjang (raw value; MinMaxScaler diterapkan di batch)
    claim_len_raw  = row.get("claim_length") or len(claim_text.split())
    review_len_raw = row.get("review_length") or 0
    rating_val     = float(rating) if rating else 0.0

    return {
        "iklan_id":             iklan_id,
        "tfidf_score":          round(tfidf_score, 6),
        "hyperbolic_count":     word_feats["hyperbolic_count"],
        "scientific_count":     word_feats["scientific_count"],
        "absolute_count":       word_feats["absolute_count"],
        "intensity_score":      word_feats["intensity_score"],
        "exclamation_count":    word_feats["exclamation_count"],
        "uppercase_ratio":      word_feats["uppercase_ratio"],
        "avg_word_length":      word_feats["avg_word_length"],
        "ngram_features":       json.dumps(ngrams, ensure_ascii=False),
        "ingredient_count":     ing_feats["ingredient_count"],
        "ingredient_scientific":ing_feats["ingredient_scientific"],
        # raw — akan dinormalisasi di batch
        "_claim_length_raw":    claim_len_raw,
        "_review_length_raw":   review_len_raw,
        "_rating_raw":          rating_val,
    }


# ── Batch processing ───────────────────────────────────────────
def preprocess_batch(iklan_list: list, log_callback=None) -> pd.DataFrame:
    """
    Jalankan preprocessing + ekstraksi fitur untuk semua iklan.

    iklan_list: list of dict dengan minimal key:
        id, claim_text
        (opsional: ingredients, review_length, claim_length, rating)

    Return: DataFrame fitur ternormalisasi [0,1].
    """
    records   = []
    prep_rows = []

    # ── Kumpulkan teks bersih untuk fit TF-IDF ────────────────
    clean_texts = []
    for iklan in iklan_list:
        p = full_preprocess(str(iklan.get("claim_text") or ""))
        clean_texts.append(p["after_stemming"] or p["normalized"])
        prep_rows.append({
            "iklan_id":        iklan["id"],
            "token_count":     p["token_count"],
            "tokens":          p["tokens"],
            "after_stopword":  p["after_stopword"],
            "after_stemming":  p["after_stemming"],
            "normalized_text": p["normalized"],
        })

    if log_callback:
        log_callback("info",
            f"Fitting TF-IDF pada {len(clean_texts)} dokumen (claim_text)...")

    fit_tfidf(clean_texts)

    # ── Insert preprocessing_result ───────────────────────────
    try:
        execute_many(
            """INSERT INTO preprocessing_result
               (iklan_id, token_count, tokens,
                after_stopword, after_stemming, normalized_text)
               VALUES (%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
                 token_count=VALUES(token_count),
                 tokens=VALUES(tokens)""",
            [(r["iklan_id"], r["token_count"], r["tokens"],
              r["after_stopword"], r["after_stemming"], r["normalized_text"])
             for r in prep_rows]
        )
    except Exception as e:
        if log_callback:
            log_callback("warn", f"Insert preprocessing (diabaikan): {e}")

    if log_callback:
        log_callback("info",
            "Mengekstrak fitur tekstual + bahan + numerik...")

    # ── Ekstrak fitur per iklan ───────────────────────────────
    fitur_rows = []
    for iklan, clean in zip(iklan_list, clean_texts):
        f = extract_all_features(iklan)
        fitur_rows.append(f)
        records.append({
            "id":                 iklan["id"],
            "claim_text":         str(iklan.get("claim_text") or ""),
            "tfidf_score":        f["tfidf_score"],
            "hyperbolic_count":   f["hyperbolic_count"],
            "scientific_count":   f["scientific_count"],
            "absolute_count":     f["absolute_count"],
            "intensity_score":    f["intensity_score"],
            "exclamation_count":  f["exclamation_count"],
            "uppercase_ratio":    f["uppercase_ratio"],
            "avg_word_length":    f["avg_word_length"],
            "ingredient_count":   f["ingredient_count"],
            "ingredient_scientific": f["ingredient_scientific"],
            "_claim_length_raw":  f["_claim_length_raw"],
            "_review_length_raw": f["_review_length_raw"],
            "_rating_raw":        f["_rating_raw"],
        })

    # ── Normalisasi fitur numerik ke [0,1] ────────────────────
    df = pd.DataFrame(records)

    num_cols_minmax = [
        "tfidf_score", "hyperbolic_count", "scientific_count",
        "absolute_count", "intensity_score", "exclamation_count",
        "uppercase_ratio", "avg_word_length",
        "ingredient_count", "ingredient_scientific",
        "_claim_length_raw", "_review_length_raw", "_rating_raw",
    ]
    global _scaler
    _scaler = MinMaxScaler()
    norm_vals = _scaler.fit_transform(df[num_cols_minmax])
    df[num_cols_minmax] = norm_vals

    # Rename kolom raw → norm
    df.rename(columns={
        "_claim_length_raw":  "claim_length_norm",
        "_review_length_raw": "review_length_norm",
        "_rating_raw":        "rating_norm",
    }, inplace=True)

    # ── Insert fitur_tekstual ─────────────────────────────────
    try:
        execute_many(
            """INSERT INTO fitur_tekstual
               (iklan_id,
                tfidf_score, hyperbolic_count, scientific_count,
                absolute_count, intensity_score,
                exclamation_count, uppercase_ratio, avg_word_length,
                ngram_features,
                ingredient_count, ingredient_scientific,
                claim_length_norm, review_length_norm, rating_norm)
               VALUES
               (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE tfidf_score=VALUES(tfidf_score)""",
            [(
                int(row["id"]),
                float(row["tfidf_score"]),
                int(row["hyperbolic_count"]),
                int(row["scientific_count"]),
                int(row["absolute_count"]),
                float(row["intensity_score"]),
                int(row["exclamation_count"]),
                float(row["uppercase_ratio"]),
                float(row["avg_word_length"]),
                fitur_rows[i]["ngram_features"],
                int(row["ingredient_count"]),
                int(row["ingredient_scientific"]),
                float(row["claim_length_norm"]),
                float(row["review_length_norm"]),
                float(row["rating_norm"]),
            )
             for i, (_, row) in enumerate(df.iterrows())]
        )
    except Exception as e:
        if log_callback:
            log_callback("warn", f"Insert fitur_tekstual (diabaikan): {e}")

    # ── Update is_processed ───────────────────────────────────
    try:
        ids = [i["id"] for i in iklan_list]
        ph  = ",".join(["%s"] * len(ids))
        execute_query(
            f"UPDATE dataset_iklan SET is_processed=1 WHERE id IN ({ph})",
            tuple(ids)
        )
    except Exception:
        pass

    if log_callback:
        log_callback("ok",
            f"Selesai. Shape fitur DataFrame: {df.shape} | "
            f"Kolom fitur: {[c for c in df.columns if c not in ('id','claim_text')]}")

    return df
