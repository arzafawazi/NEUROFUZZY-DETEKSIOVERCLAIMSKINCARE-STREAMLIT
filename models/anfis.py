"""
models/anfis.py
Implementasi ANFIS (Adaptive Neuro-Fuzzy Inference System)
untuk deteksi overclaim iklan skincare.

Arsitektur 5 Layer:
  Layer 1: Fuzzifikasi (Gaussian Membership Functions)
  Layer 2: Rule Firing Strength (produk antecedent)
  Layer 3: Normalisasi firing strength
  Layer 4: Consequent (TSK linear output)
  Layer 5: Defuzzifikasi (weighted average)

Fitur input (X) — 5 fitur utama dari skema baru:
  x1 = intensity_score       (intensitas bahasa klaim)
  x2 = hyperbolic_count      (jumlah kata hiperbolik)
  x3 = absolute_count        (jumlah klaim absolut)
  x4 = claim_length_norm     (panjang klaim ternormalisasi)
  x5 = ingredient_scientific (jumlah bahan saintifik)

Output (y): label 0–3
  0 = tidak_overclaim
  1 = rendah
  2 = sedang
  3 = tinggi
"""
import numpy as np
import pandas as pd
import warnings
from typing import Tuple, List, Optional
from sklearn.metrics import (accuracy_score, precision_score,
                             recall_score, f1_score, classification_report)

warnings.filterwarnings("ignore")

# ── Label Mapping ─────────────────────────────────────────────
LABEL_MAP = {
    0: "tidak_overclaim",
    1: "rendah",
    2: "sedang",
    3: "tinggi",
}
LABEL_MAP_INV = {v: k for k, v in LABEL_MAP.items()}

# ── Threshold defuzzifikasi [0,1] → kelas 0-3 ─────────────────
THRESHOLDS = [0.25, 0.50, 0.75]

# ── Nama & jumlah fitur input ─────────────────────────────────
FEATURE_NAMES = [
    "intensity_score",
    "hyperbolic_count",
    "absolute_count",
    "claim_length_norm",
    "ingredient_scientific",
]
N_INPUT = len(FEATURE_NAMES)   # = 5


# ── Gaussian MF ───────────────────────────────────────────────
def _gaussian_mf(x: np.ndarray, mean: float, sigma: float) -> np.ndarray:
    return np.exp(-0.5 * ((x - mean) / (sigma + 1e-9)) ** 2)


# ═════════════════════════════════════════════════════════════
class ANFISOverclaimDetector:
    """
    ANFIS dengan N_INPUT variabel input, num_mf membership function per input,
    training hybrid (LSE + gradient descent).
    """

    def __init__(
        self,
        num_mf: int = 3,
        mf_type: str = "gaussian",
        learning_rate: float = 0.01,
        epochs: int = 100,
    ):
        self.num_mf     = num_mf
        self.mf_type    = mf_type
        self.lr         = learning_rate
        self.epochs     = epochs
        self.is_trained = False
        self.n_input    = N_INPUT
        self.n_rules    = num_mf ** N_INPUT

        self._init_mf_params()

        # Consequent TSK: (n_rules × (n_input + 1))
        self.consequent = np.random.randn(self.n_rules, self.n_input + 1) * 0.1

        self.loss_history: List[float] = []

    # ── Inisialisasi MF ────────────────────────────────────────
    def _init_mf_params(self):
        means  = np.linspace(0, 1, self.num_mf)
        sigma  = 1.0 / (2 * self.num_mf)
        self.mf_params = np.array(
            [[[m, sigma] for m in means] for _ in range(self.n_input)],
            dtype=float
        )  # shape: (n_input, num_mf, 2)

    # ── Forward ────────────────────────────────────────────────
    def _fuzzify(self, X: np.ndarray) -> np.ndarray:
        """Layer 1 → shape (n_samples, n_input, num_mf)."""
        n  = X.shape[0]
        mu = np.zeros((n, self.n_input, self.num_mf))
        for i in range(self.n_input):
            for j in range(self.num_mf):
                mu[:, i, j] = _gaussian_mf(
                    X[:, i],
                    self.mf_params[i, j, 0],
                    self.mf_params[i, j, 1],
                )
        return mu

    def _firing_strength(self, mu: np.ndarray) -> np.ndarray:
        """Layer 2 → shape (n_samples, n_rules)."""
        n = mu.shape[0]
        w = np.ones((n, self.n_rules))
        for rule_idx in range(self.n_rules):
            tmp = rule_idx
            for i in range(self.n_input - 1, -1, -1):
                mf_idx = tmp % self.num_mf
                tmp   //= self.num_mf
                w[:, rule_idx] *= mu[:, i, mf_idx]
        return w

    def _normalize(self, w: np.ndarray) -> np.ndarray:
        """Layer 3."""
        return w / (w.sum(axis=1, keepdims=True) + 1e-9)

    def _consequent_output(self, w_bar: np.ndarray,
                           X: np.ndarray) -> np.ndarray:
        """Layer 4 → shape (n_samples,)."""
        x_aug    = np.hstack([X, np.ones((X.shape[0], 1))])   # (n, n_input+1)
        rule_out = x_aug @ self.consequent.T                   # (n, n_rules)
        return (w_bar * rule_out).sum(axis=1)

    def predict_raw(self, X: np.ndarray) -> np.ndarray:
        mu    = self._fuzzify(X)
        w     = self._firing_strength(mu)
        w_bar = self._normalize(w)
        y_hat = self._consequent_output(w_bar, X)
        return np.clip(y_hat, 0, 1)

    def _score_to_label(self, scores: np.ndarray) -> np.ndarray:
        labels = np.zeros(len(scores), dtype=int)
        labels[scores >= THRESHOLDS[0]] = 1
        labels[scores >= THRESHOLDS[1]] = 2
        labels[scores >= THRESHOLDS[2]] = 3
        return labels

    # ── Training (Hybrid Learning) ─────────────────────────────
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        log_callback=None,
    ) -> "ANFISOverclaimDetector":
        """
        Hybrid learning:
          - Consequent → Least Squares Estimation (LSE)
          - Premise (MF params) → Gradient Descent

        y: integer array 0-3
        """
        y_score = y / 3.0   # skalakan ke [0,1]
        best_loss = float("inf")

        for epoch in range(self.epochs):
            mu    = self._fuzzify(X)
            w     = self._firing_strength(mu)
            w_bar = self._normalize(w)

            # LSE untuk consequent
            x_aug = np.hstack([X, np.ones((X.shape[0], 1))])
            A = (w_bar[:, :, None] * x_aug[:, None, :]).reshape(
                X.shape[0], -1
            )
            try:
                sol, *_ = np.linalg.lstsq(A, y_score, rcond=None)
                self.consequent = sol.reshape(self.n_rules, self.n_input + 1)
            except Exception:
                pass

            y_hat = np.clip(self._consequent_output(w_bar, X), 0, 1)
            err   = y_hat - y_score
            loss  = float(np.mean(err ** 2))
            self.loss_history.append(loss)
            best_loss = min(best_loss, loss)

            # Gradient descent pada MF params
            for i in range(self.n_input):
                for j in range(self.num_mf):
                    mean  = self.mf_params[i, j, 0]
                    sigma = self.mf_params[i, j, 1]
                    xi    = X[:, i]

                    dmu_dmean  = mu[:, i, j] * (xi - mean) / (sigma ** 2 + 1e-9)
                    dmu_dsigma = mu[:, i, j] * ((xi - mean) ** 2) / (sigma ** 3 + 1e-9)

                    self.mf_params[i, j, 0] -= self.lr * (2 * err * dmu_dmean).mean()
                    self.mf_params[i, j, 1] -= self.lr * (2 * err * dmu_dsigma).mean()
                    self.mf_params[i, j, 1]  = max(self.mf_params[i, j, 1], 0.01)

            if log_callback and (epoch + 1) % max(1, self.epochs // 10) == 0:
                log_callback(
                    "info",
                    f"[Epoch {epoch+1:>4}/{self.epochs}] "
                    f"MSE Loss: {loss:.6f}  |  Best: {best_loss:.6f}"
                )

        self.is_trained = True
        return self

    # ── Prediksi & Evaluasi ────────────────────────────────────
    def predict(self, X: np.ndarray) -> np.ndarray:
        return self._score_to_label(self.predict_raw(X))

    def predict_with_confidence(
        self, X: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        scores = self.predict_raw(X)
        return self._score_to_label(scores), scores

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> dict:
        y_pred = self.predict(X)
        
        # --- LOGIKA DINAMIS ---
        # 1. Gabungkan y dan y_pred, lalu cari nilai uniknya (agar tahu kelas apa saja yang muncul)
        kelas_aktif = np.unique(np.concatenate((y, y_pred)))
        
        # 2. Ambil nama kelas dari LABEL_MAP hanya untuk kelas yang aktif saja
        dynamic_target_names = [LABEL_MAP[val] for val in kelas_aktif]
        # ----------------------

        return {
            "accuracy":  round(accuracy_score(y, y_pred), 4),
            "precision": round(precision_score(
                y, y_pred, average="weighted", zero_division=0), 4),
            "recall":    round(recall_score(
                y, y_pred, average="weighted", zero_division=0), 4),
            "f1_score":  round(f1_score(
                y, y_pred, average="weighted", zero_division=0), 4),
            "report":    classification_report(
                y, y_pred,
                labels=kelas_aktif,                # Gunakan label angka yang terdeteksi
                target_names=dynamic_target_names, # Gunakan nama kelas yang terdeteksi
                output_dict=True, 
                zero_division=0
            ),
        }

    def explain_prediction(self, x: np.ndarray) -> str:
        """Buat kalimat interpretasi aturan fuzzy paling aktif."""
        x2d   = x.reshape(1, -1)
        mu    = self._fuzzify(x2d)
        w     = self._firing_strength(mu)
        top_r = int(np.argmax(w[0]))

        mf_labels = (["Rendah","Sedang","Tinggi"] * self.num_mf)[:self.num_mf]
        tmp = top_r
        indices = []
        for _ in range(self.n_input - 1, -1, -1):
            indices.insert(0, tmp % self.num_mf)
            tmp //= self.num_mf

        short_names = ["Intensitas","Hiperbolik","Absolut","Len Klaim","Ing. Saintifik"]
        parts = [
            f"{short_names[i]}={mf_labels[min(indices[i], len(mf_labels)-1)]}"
            for i in range(self.n_input)
        ]
        return "IF " + " AND ".join(parts) + " THEN [Rule aktif]"


# ── Helper: siapkan X dan y dari DataFrame fitur ──────────────
def prepare_Xy(df: pd.DataFrame) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Ambil 5 fitur utama ANFIS dari DataFrame hasil preprocess_batch.
    Kembalikan (X, y) atau (X, None) jika label tidak tersedia.

    Urutan fitur harus konsisten dengan FEATURE_NAMES.
    """
    # Pastikan kolom ada; jika tidak, isi 0
    X_df = pd.DataFrame()
    for feat in FEATURE_NAMES:
        if feat in df.columns:
            X_df[feat] = pd.to_numeric(df[feat], errors="coerce").fillna(0)
        else:
            X_df[feat] = 0.0

    X = X_df.values.astype(float)

    y = None
    # Coba dari kolom label_manual (string enum)
    if "label_manual" in df.columns:
        y_raw = df["label_manual"].map(LABEL_MAP_INV)
        if y_raw.notna().any():
            y = y_raw.fillna(0).values.astype(int)
    # Atau dari label_overclaim (int 0-3)
    if y is None and "label_overclaim" in df.columns:
        lo = pd.to_numeric(df["label_overclaim"], errors="coerce")
        if lo.notna().any():
            y = lo.fillna(0).values.astype(int)

    return X, y
