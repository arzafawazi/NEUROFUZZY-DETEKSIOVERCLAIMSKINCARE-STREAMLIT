"""
models/preprocessor.py
Preprocessing teks iklan: tokenisasi, stopword, stemming (Sastrawi), normalisasi
"""
import re
import json
import nltk
from typing import List, Tuple

# Lazy-load Sastrawi agar tidak error jika belum terinstall
try:
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
    _stemmer_factory  = StemmerFactory()
    _stemmer          = _stemmer_factory.create_stemmer()
    _sw_factory       = StopWordRemoverFactory()
    _stopword_list    = set(_sw_factory.get_stop_words())
    SASTRAWI_AVAILABLE = True
except ImportError:
    SASTRAWI_AVAILABLE = False
    _stemmer = None
    _stopword_list = set()

# NLTK punkt (tokenizer)
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)

# ── Normalisasi kamus sederhana (slang → formal) ─────────────
NORMALIZATION_DICT = {
    "bgt": "banget", "bgt.": "banget", "yg": "yang", "dgn": "dengan",
    "utk": "untuk", "krn": "karena", "sdh": "sudah", "blm": "belum",
    "ga": "tidak", "gak": "tidak", "nggak": "tidak", "tdk": "tidak",
    "hrs": "harus", "bs": "bisa", "bsa": "bisa", "msh": "masih",
    "jg": "juga", "juga.": "juga", "kpd": "kepada", "dr": "dari",
    "sy": "saya", "km": "kamu", "aq": "aku", "ny": "nya",
    "skrg": "sekarang", "lg": "lagi", "bkn": "bukan", "spy": "supaya",
    "dpt": "dapat", "sm": "sama", "sbg": "sebagai", "dll": "dan lain lain",
}

# ── Kata hiperbolik (contoh kosakata domain skincare) ─────────
HYPERBOLIC_WORDS = {
    "terbaik", "tercepat", "terbukti", "revolusioner", "ajaib", "mukjizat",
    "dahsyat", "luar biasa", "super", "ultra", "mega", "power", "turbo",
    "extreme", "maksimal", "permanen", "selamanya", "abadi", "instan",
    "instant", "langsung", "sekejap", "ampuh", "cespleng", "manjur",
    "sakti", "dewa", "magic", "miracle", "wonder", "amazing", "incredible",
    "fantastic", "spectacular", "extraordinary", "paling", "nomor satu",
    "nomor1", "no1", "no.1", "#1", "juara", "terpercaya", "terampuh",
}

# ── Klaim saintifik ───────────────────────────────────────────
SCIENTIFIC_CLAIMS = {
    "klinis", "dermatologis", "dermatologi", "uji klinis", "lab", "laboratorium",
    "penelitian", "riset", "ilmiah", "scientifically", "clinically", "dermatologist",
    "dermatologist-tested", "hypoallergenic", "non-comedogenic", "ph balanced",
    "fda", "bpom", "iso", "sertifikat", "teruji", "terbukti secara klinis",
    "dokter", "ahli", "pakar", "expert", "spesialis", "formula",
    "vitamin", "retinol", "niacinamide", "hyaluronic", "peptide", "collagen",
    "ceramide", "aha", "bha", "spf", "uva", "uvb", "antioxidant",
}

# ── Klaim absolut ─────────────────────────────────────────────
ABSOLUTE_CLAIMS = {
    "100%", "pasti", "dijamin", "garansi", "tanpa", "bebas", "zero",
    "0%", "semua", "seluruh", "tidak ada", "tiada", "bersih total",
    "hilang sempurna", "putih sempurna", "bebas jerawat", "anti aging",
    "anti-aging", "forever", "permanen", "full", "complete", "total",
    "keseluruhan", "mutlak", "absolut", "tanpa efek samping",
    "tanpa bahan berbahaya", "100 persen", "sepenuhnya",
}


def normalize_text(text: str) -> str:
    """Normalisasi: lowercase, hapus karakter aneh, slang → formal."""
    text = text.lower().strip()
    # Hapus URL
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)
    # Hapus mention & hashtag
    text = re.sub(r'[@#]\w+', ' ', text)
    # Pertahankan huruf, angka, spasi, persen, titik
    text = re.sub(r'[^\w\s%.]', ' ', text)
    # Normalisasi whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Ganti slang
    tokens = text.split()
    tokens = [NORMALIZATION_DICT.get(t, t) for t in tokens]
    return ' '.join(tokens)


def tokenize(text: str) -> List[str]:
    """Tokenisasi sederhana berbasis spasi + nltk."""
    try:
        from nltk.tokenize import word_tokenize
        return word_tokenize(text)
    except Exception:
        return text.split()


def remove_stopwords(tokens: List[str]) -> List[str]:
    """Hapus stopword bahasa Indonesia."""
    extra_stop = {"yuk", "nih", "lho", "dong", "deh", "sih", "nya",
                  "kan", "lah", "ah", "oh", "eh", "ya", "iya", "ok",
                  "oke", "kak", "ka", "gan", "sis", "bro", "sob"}
    stop = _stopword_list | extra_stop
    return [t for t in tokens if t not in stop and len(t) > 1]


def stem_tokens(tokens: List[str]) -> List[str]:
    """Stemming dengan Sastrawi (atau fallback identity)."""
    if SASTRAWI_AVAILABLE and _stemmer:
        return [_stemmer.stem(t) for t in tokens]
    return tokens


def full_preprocess(text: str) -> dict:
    """
    Pipeline lengkap preprocessing.
    Kembalikan dict berisi setiap tahap.
    """
    normalized = normalize_text(text)
    tokens     = tokenize(normalized)
    no_stop    = remove_stopwords(tokens)
    stemmed    = stem_tokens(no_stop)
    final      = ' '.join(stemmed)

    return {
        "original":        text,
        "normalized":      normalized,
        "tokens":          json.dumps(tokens,  ensure_ascii=False),
        "after_stopword":  ' '.join(no_stop),
        "after_stemming":  final,
        "token_count":     len(tokens),
    }


def count_feature_words(text: str) -> dict:
    """Hitung kata-kata fitur khusus dari teks asli."""
    lower = text.lower()
    words = set(re.findall(r'\b\w+\b', lower))

    hyperbolic = len(words & HYPERBOLIC_WORDS)
    scientific = len(words & SCIENTIFIC_CLAIMS)
    absolute   = len(words & ABSOLUTE_CLAIMS)

    # Intensitas: jumlah tanda seru + huruf kapital / total
    excl_count    = text.count('!')
    words_raw     = text.split()
    upper_ratio   = sum(1 for w in words_raw if w.isupper()) / max(len(words_raw), 1)
    avg_word_len  = sum(len(w) for w in words_raw) / max(len(words_raw), 1)
    intensity     = (hyperbolic * 0.4 + excl_count * 0.2 +
                     upper_ratio * 0.2 + scientific * 0.1 + absolute * 0.1)

    return {
        "hyperbolic_count": hyperbolic,
        "scientific_count": scientific,
        "absolute_count":   absolute,
        "exclamation_count": excl_count,
        "uppercase_ratio":  round(upper_ratio, 4),
        "avg_word_length":  round(avg_word_len, 4),
        "intensity_score":  round(intensity, 4),
    }
