"""
models/anfis.py
Implementasi ANFIS (Adaptive Neuro-Fuzzy Inference System)
menggunakan scikit-fuzzy + numpy untuk deteksi overclaim skincare.

Arsitektur:
  Layer 1: Fuzzifikasi (Membership Functions)
  Layer 2: Rule Firing Strength
  Layer 3: Normalisasi
  Layer 4: Consequent (TSK linear)
  Layer 5: Defuzzifikasi (weighted average)
"""
import numpy as np
import pandas as pd
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from sklearn.metrics import (accuracy_score, precision_score,
                             recall_score, f1_score, classification_report)
from typing import Tuple, List, Optional
import warnings
warnings.filterwarnings("ignore")


# ── Label Mapping ────────────────────────────────────────────
LABEL_MAP = {
    0: "tidak_overclaim",
    1: "rendah",
    2: "sedang",
    3: "tinggi",
}
LABEL_MAP_INV = {v: k for k, v in LABEL_MAP.items()}

# ── Thresholds defuzzifikasi ──────────────────────────────────
THRESHOLDS = [0.25, 0.50, 0.75]   # batas tidak/rendah/sedang/tinggi


def _gaussian_mf(x: np.ndarray, mean: float, sigma: float) -> np.ndarray:
    return np.exp(-0.5 * ((x - mean) / (sigma + 1e-9)) ** 2)


class ANFISOverclaimDetector:
    """
    ANFIS sederhana dengan 3 input utama:
      x1 = intensity_score   (0-1)
      x2 = hyperbolic_norm   (0-1)
      x3 = absolute_norm     (0-1)

    Output: skor overclaim 0-1 → dikategorikan 4 kelas.
    Training: gradient descent + least squares (hybrid learning).
    """

    def __init__(self,
                 num_mf: int = 3,
                 mf_type: str = "gaussian",
                 learning_rate: float = 0.01,
                 epochs: int = 100):
        self.num_mf       = num_mf
        self.mf_type      = mf_type
        self.lr           = learning_rate
        self.epochs       = epochs
        self.is_trained   = False

        # Parameter MF per input (mean, sigma) — shape (n_input, num_mf, 2)
        self.n_input = 3
        self._init_mf_params()

        # Consequent params (TSK: p, q, r, const per rule)
        n_rules = num_mf ** self.n_input
        self.n_rules = n_rules
        self.consequent = np.random.randn(n_rules, self.n_input + 1) * 0.1

        # History
        self.loss_history: List[float] = []

    # ── Inisialisasi MF ─────────────────────────────────────
    def _init_mf_params(self):
        """Inisialisasi mean & sigma MF secara merata di [0,1]."""
        means  = np.linspace(0, 1, self.num_mf)
        sigma  = 1.0 / (2 * self.num_mf)
        params = []
        for _ in range(self.n_input):
            inp_params = [[m, sigma] for m in means]
            params.append(inp_params)
        self.mf_params = np.array(params, dtype=float)  # (n_input, num_mf, 2)

    # ── Forward Pass ────────────────────────────────────────
    def _fuzzify(self, x: np.ndarray) -> np.ndarray:
        """Layer 1: kembalikan (n_samples, n_input, num_mf)."""
        n = x.shape[0]
        mu = np.zeros((n, self.n_input, self.num_mf))
        for i in range(self.n_input):
            for j in range(self.num_mf):
                mean  = self.mf_params[i, j, 0]
                sigma = self.mf_params[i, j, 1]
                mu[:, i, j] = _gaussian_mf(x[:, i], mean, sigma)
        return mu

    def _firing_strength(self, mu: np.ndarray) -> np.ndarray:
        """Layer 2: produk semua kombinasi rules (n_samples, n_rules)."""
        n = mu.shape[0]
        w = np.ones((n, self.n_rules))
        for rule_idx in range(self.n_rules):
            # decode rule index ke MF index per input
            tmp = rule_idx
            for i in range(self.n_input - 1, -1, -1):
                mf_idx = tmp % self.num_mf
                tmp   //= self.num_mf
                w[:, rule_idx] *= mu[:, i, mf_idx]
        return w

    def _normalize(self, w: np.ndarray) -> np.ndarray:
        """Layer 3: normalisasi firing strength."""
        total = w.sum(axis=1, keepdims=True) + 1e-9
        return w / total

    def _consequent_output(self, w_bar: np.ndarray, x: np.ndarray) -> np.ndarray:
        """Layer 4: TSK weighted output."""
        # x_aug: append bias column
        x_aug = np.hstack([x, np.ones((x.shape[0], 1))])  # (n, n_input+1)
        # rule_out shape: (n, n_rules)
        rule_out = x_aug @ self.consequent.T  # (n, n_rules)
        return (w_bar * rule_out).sum(axis=1)  # (n,)

    def predict_raw(self, X: np.ndarray) -> np.ndarray:
        mu    = self._fuzzify(X)
        w     = self._firing_strength(mu)
        w_bar = self._normalize(w)
        y_hat = self._consequent_output(w_bar, X)
        # Clip ke [0,1]
        return np.clip(y_hat, 0, 1)

    def _score_to_label(self, scores: np.ndarray) -> np.ndarray:
        labels = np.zeros(len(scores), dtype=int)
        labels[scores >= THRESHOLDS[0]] = 1
        labels[scores >= THRESHOLDS[1]] = 2
        labels[scores >= THRESHOLDS[2]] = 3
        return labels

    # ── Training (Hybrid Learning) ───────────────────────────
    def fit(self, X: np.ndarray, y: np.ndarray,
            log_callback=None) -> "ANFISOverclaimDetector":
        """
        Hybrid: consequent → LSE per epoch,
                premise (MF params) → gradient descent.
        y: label int 0-3
        """
        # Konversi label ke skor target [0, 1/3, 2/3, 1]
        y_score = y / 3.0

        best_loss = float("inf")
        for epoch in range(self.epochs):
            mu    = self._fuzzify(X)
            w     = self._firing_strength(mu)
            w_bar = self._normalize(w)

            # LSE untuk consequent
            x_aug    = np.hstack([X, np.ones((X.shape[0], 1))])
            A = w_bar[:, :, None] * x_aug[:, None, :]  # (n, n_rules, n_input+1)
            A = A.reshape(X.shape[0], -1)               # (n, n_rules*(n_input+1))
            b = y_score
            try:
                sol, *_ = np.linalg.lstsq(A, b, rcond=None)
                self.consequent = sol.reshape(self.n_rules, self.n_input + 1)
            except Exception:
                pass

            # Forward
            y_hat = self._consequent_output(w_bar, X)
            y_hat = np.clip(y_hat, 0, 1)
            err   = y_hat - y_score
            loss  = float(np.mean(err ** 2))
            self.loss_history.append(loss)

            # Gradient descent pada MF params (mean, sigma)
            for i in range(self.n_input):
                for j in range(self.num_mf):
                    mean  = self.mf_params[i, j, 0]
                    sigma = self.mf_params[i, j, 1]
                    xi    = X[:, i]

                    dmu_dmean  = mu[:, i, j] * (xi - mean) / (sigma ** 2 + 1e-9)
                    dmu_dsigma = mu[:, i, j] * ((xi - mean) ** 2) / (sigma ** 3 + 1e-9)

                    # gradient loss terhadap mean
                    dl_dmean  = (2 * err * dmu_dmean).mean()
                    dl_dsigma = (2 * err * dmu_dsigma).mean()

                    self.mf_params[i, j, 0] -= self.lr * dl_dmean
                    self.mf_params[i, j, 1] -= self.lr * dl_dsigma
                    # Pastikan sigma positif
                    self.mf_params[i, j, 1]  = max(self.mf_params[i, j, 1], 0.01)

            if loss < best_loss:
                best_loss = loss

            if log_callback and (epoch + 1) % max(1, self.epochs // 10) == 0:
                log_callback("info",
                    f"[Epoch {epoch+1}/{self.epochs}] Loss: {loss:.6f} | Best: {best_loss:.6f}")

        self.is_trained = True
        return self

    # ── Prediksi & Evaluasi ──────────────────────────────────
    def predict(self, X: np.ndarray) -> np.ndarray:
        scores = self.predict_raw(X)
        return self._score_to_label(scores)

    def predict_with_confidence(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        scores = self.predict_raw(X)
        labels = self._score_to_label(scores)
        return labels, scores

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> dict:
        y_pred = self.predict(X)

        # Ambil label yang benar-benar muncul di data
        unique_labels = sorted(set(y) | set(y_pred))

        # Mapping ke nama label
        target_names = [LABEL_MAP[i] for i in unique_labels]

        report = classification_report(
            y,
            y_pred,
            labels=unique_labels,
            target_names=target_names,
            output_dict=True,
            zero_division=0
        )

        return {
            "accuracy":  round(accuracy_score(y, y_pred), 4),
            "precision": round(precision_score(y, y_pred, average="weighted", zero_division=0), 4),
            "recall":    round(recall_score(y, y_pred, average="weighted", zero_division=0), 4),
            "f1_score":  round(f1_score(y, y_pred, average="weighted", zero_division=0), 4),
            "report":    report,
        }

    def explain_prediction(self, x: np.ndarray) -> str:
        """Hasilkan interpretasi aturan fuzzy yang paling aktif."""
        x2d = x.reshape(1, -1)
        mu  = self._fuzzify(x2d)
        w   = self._firing_strength(mu)
        top_rule = int(np.argmax(w[0]))

        # Decode top_rule ke MF per input
        mf_labels = ["Rendah", "Sedang", "Tinggi"][:self.num_mf]
        tmp = top_rule
        indices = []
        for _ in range(self.n_input - 1, -1, -1):
            indices.insert(0, tmp % self.num_mf)
            tmp //= self.num_mf

        input_names = ["Intensitas", "Hiperbolik", "Absolut"]
        parts = [f"{input_names[i]}={mf_labels[min(indices[i], len(mf_labels)-1)]}"
                 for i in range(self.n_input)]
        return "IF " + " AND ".join(parts) + " THEN [Rule aktif]"


# ── Helper: siapkan X dan y dari DataFrame fitur ─────────────
def prepare_Xy(df: pd.DataFrame) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Ambil kolom fitur & label dari DataFrame.
    Kembalikan (X, y) atau (X, None) jika label tidak ada.
    """
    feat_cols = ["intensity_score", "hyperbolic_count", "absolute_count"]
    X = df[feat_cols].values.astype(float)
    y = None
    if "label_manual" in df.columns:
        y_raw = df["label_manual"].map(LABEL_MAP_INV)
        y = y_raw.fillna(0).values.astype(int)
    return X, y
