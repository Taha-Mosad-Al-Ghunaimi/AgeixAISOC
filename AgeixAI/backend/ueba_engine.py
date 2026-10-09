"""
AgeixAISOC — Unsupervised UEBA (User and Entity Behavior Analytics) Engine.

Architecture
------------
1. An Isolation Forest model is trained on a baseline of "normal" behavior logs
   (login hour, data downloaded, failed logins, access type).
2. Live logs ingested via POST /api/ueba/ingest are scored against this baseline.
3. If the anomaly score exceeds the threshold, the engine returns a structured
   alert that gets routed to the CrewAI Hive-Mind for human review (HITL).

Why Isolation Forest?
---------------------
- Unsupervised: No labeled attack data needed — ideal for SOC where benign logs
  are abundant but confirmed attacks are rare.
- Efficient: O(n log n) complexity. Runs on CPU, leaving GPU VRAM free for LLMs.
- Tabular-native: Works directly on numerical feature vectors without windowing.
- Interpretable: Feature-level anomaly contributions can be extracted for the
  "reason" field sent to the Master Brain.

Pipeline
--------
  generate_mock_ueba_data()   →   train_ueba_model()   →   predict_anomaly()
                                                                      │
                          ┌───────────────────────────────────────────┘
                          ▼
                   POST /api/ueba/ingest
                          │
                   is_anomaly? ──No──→ return ok
                          │
                          ▼
                  ┌─ 1. Save to DB ─────────────────┐
                  ├─ 2. Write to Beehive            │
                  ├─ 3. Run CrewAI Master Brain     │
                  ├─ 4. Push HITL Decision via WS   │
                  └─────────────────────────────────┘
"""

import hashlib
import json
import logging
import os
import random
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger("AgeixAI.ueba")

# ── Configuration ────────────────────────────────────────────────────────────

MODEL_PATH = os.path.join(os.path.dirname(__file__), "ueba_model.joblib")

# Isolation Forest decision_function returns:
#   positive = normal (in-distribution)
#   negative = anomaly (out-of-distribution)
# ANOMALY_PERCENTILE: percentiles below this threshold are flagged.
#   We compute the actual threshold dynamically from the training data scores.
ANOMALY_PERCENTILE = 20           # Bottom 20% of training scores = anomaly candidates
ANOMALY_THRESHOLD = -0.05         # Static fallback if training data unavailable
CONFIDENCE_FLOOR = 0.6            # Minimum confidence to report an anomaly
HIGH_RISK_SCORE_FLOOR = 50        # Minimum risk score for any flag-worthy event


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  Mock data generator
# ═══════════════════════════════════════════════════════════════════════════════

def generate_mock_ueba_data(n_samples: int = 2000) -> pd.DataFrame:
    """
    Create a realistic DataFrame of normal user behavior for training.

    "Normal" profile:
      - Login hour:       8 AM – 5 PM (peak at 9–11 AM, 2–4 PM)
      - Data downloaded:  1 – 800 MB (most < 200 MB)
      - Failed logins:    0 – 2 (rarely 3+)
      - Access type:      mostly VPN and Internal (Office rarely)
    """
    np.random.seed(42)
    random.seed(42)

    # Login hour — truncated normal centred at 10 AM, clamped to 6–22
    login_hour_raw = np.random.normal(loc=10.0, scale=2.5, size=n_samples)
    login_hour = np.clip(np.round(login_hour_raw), 6, 22).astype(int)

    # Data downloaded — exponential-ish distribution, most < 200 MB
    data_downloaded = np.random.exponential(scale=80, size=n_samples)
    data_downloaded = np.clip(data_downloaded, 0.5, 950).astype(float)

    # Failed logins — mostly 0, occasionally 1–2
    failed_logins = np.random.poisson(lam=0.3, size=n_samples)
    failed_logins = np.clip(failed_logins, 0, 10).astype(int)

    # Access type — 0 = VPN, 1 = Internal, 2 = Office
    access_type = np.random.choice([0, 0, 0, 1, 1, 2], size=n_samples)

    # Add a tiny amount of noise to avoid perfect zero-variance features
    noise = np.random.normal(0, 0.02, size=n_samples)

    df = pd.DataFrame({
        "login_hour": login_hour,
        "data_downloaded_mb": data_downloaded + noise,
        "failed_logins": failed_logins,
        "access_type": access_type,
    })

    logger.info("Mock UEBA data generated: %d samples, 4 features", n_samples)
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  Model training
# ═══════════════════════════════════════════════════════════════════════════════

def train_ueba_model(data: pd.DataFrame | None = None, save_path: str = MODEL_PATH) -> Any:
    """
    Train an Isolation Forest on UEBA baseline data and persist with joblib.

    Also computes the anomaly threshold from the training data's decision
    function scores (the ANOMALY_PERCENTILE-th percentile) and stores it
    alongside the model so that scoring is calibrated to the actual data.

    Parameters
    ----------
    data : pd.DataFrame, optional
        Training data with columns [login_hour, data_downloaded_mb,
        failed_logins, access_type]. Auto-generates if None.
    save_path : str
        Where to save the joblib file.

    Returns
    -------
    Trained IsolationForest model (with a .ageixai_threshold attribute).
    """
    from sklearn.ensemble import IsolationForest
    import joblib

    if data is None:
        data = generate_mock_ueba_data()

    features = ["login_hour", "data_downloaded_mb", "failed_logins", "access_type"]
    X = data[features].values

    model = IsolationForest(
        n_estimators=100,
        max_samples="auto",
        contamination=0.1,         # Expect ~10% of production to require attention
        random_state=42,
        n_jobs=-1,                 # Use all CPU cores
    )
    model.fit(X)

    # Compute dynamic threshold: the ANOMALY_PERCENTILE-th percentile of
    # the training decision scores. Scores below this are flagged.
    train_scores = model.decision_function(X)
    dynamic_threshold = float(np.percentile(train_scores, ANOMALY_PERCENTILE))
    # Attach to model so predict_anomaly can use it
    model.ageixai_threshold = dynamic_threshold

    bundle = {
        "model": model,
        "threshold": dynamic_threshold,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(data),
        "features": features,
        "anomaly_percentile": ANOMALY_PERCENTILE,
    }

    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    joblib.dump(bundle, save_path)

    logger.info(
        "Isolation Forest trained on %d samples, threshold=%.4f (p%d), saved to %s",
        len(data), dynamic_threshold, ANOMALY_PERCENTILE, save_path,
    )
    return model


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  Anomaly prediction
# ═══════════════════════════════════════════════════════════════════════════════

def load_model(model_path: str = MODEL_PATH) -> tuple[Any, float]:
    """
    Load the trained Isolation Forest model and its dynamic threshold.

    Returns
    -------
    Tuple of (model, threshold). The threshold is the decision_function
    value below which a log is considered anomalous.
    """
    import joblib
    if not os.path.exists(model_path):
        logger.warning("UEBA model not found at %s — training on mock data", model_path)
        model = train_ueba_model(save_path=model_path)
        threshold = getattr(model, "ageixai_threshold", ANOMALY_THRESHOLD)
        return model, threshold
    try:
        bundle = joblib.load(model_path)
        if isinstance(bundle, dict) and "model" in bundle:
            return bundle["model"], bundle.get("threshold", ANOMALY_THRESHOLD)
        # Legacy format — just the model itself
        threshold = getattr(bundle, "ageixai_threshold", ANOMALY_THRESHOLD)
        return bundle, threshold
    except Exception as exc:
        logger.warning("Failed to load UEBA model: %s — retraining", exc)
        model = train_ueba_model(save_path=model_path)
        return model, getattr(model, "ageixai_threshold", ANOMALY_THRESHOLD)


def _generate_anomaly_reason(
    log: dict[str, Any],
    features: dict[str, float],
    score: float,
) -> str:
    """
    Build a human-readable reason string for the anomaly.
    Examines which features deviated most from expected norms.
    """
    reasons: list[str] = []
    hour = log.get("login_hour", -1)
    data_mb = log.get("data_downloaded_mb", 0.0)
    failed = log.get("failed_logins", 0)
    access_type = log.get("access_type", 0)

    access_labels = {0: "VPN", 1: "Internal", 2: "Office"}
    atype = access_labels.get(access_type, f"Unknown({access_type})")

    # Off-hours login
    if hour < 7 or hour > 19:
        reasons.append(f"Off-hours login at {hour}:00 (expected 8–18)")

    # Massive data transfer
    if data_mb > 2000:
        reasons.append(f"Massive data transfer: {data_mb:.0f} MB (normal < 200 MB)")
    elif data_mb > 800:
        reasons.append(f"Elevated data transfer: {data_mb:.0f} MB (normal < 200 MB)")

    # Failed login spike
    if failed >= 5:
        reasons.append(f"High failed-login count: {failed} (normal 0–2)")

    # Rare access type + off-hours
    if access_type == 2 and (hour < 7 or hour > 18):
        reasons.append("Office access during off-hours")

    # Generic fallback
    if not reasons:
        reasons.append(
            f"Unusual access pattern: {failed} failed logins, {data_mb:.0f} MB at hour {hour}:00 "
            f"via {atype}"
        )

    return "; ".join(reasons)


def predict_anomaly(
    log: dict[str, Any],
    model_path: str = MODEL_PATH,
) -> dict[str, Any]:
    """
    Score a single user-log entry against the trained Isolation Forest model.

    Parameters
    ----------
    log : dict
        Must contain keys: login_hour (int 0-23), data_downloaded_mb (float),
        failed_logins (int), access_type (int 0=VPN, 1=Internal, 2=Office).
    model_path : str
        Path to the joblib model file.

    Returns
    -------
    dict with keys:
        is_anomaly (bool), risk_score (int 0-100),
        reason (str), anomaly_score (float), confidence (float).
    """
    model, threshold = load_model(model_path)

    features = np.array([[
        log.get("login_hour", 10),
        log.get("data_downloaded_mb", 0.0),
        log.get("failed_logins", 0),
        log.get("access_type", 0),
    ]])

    # Isolation Forest: decision_function returns positive = normal,
    # negative = anomaly.  More negative = more anomalous.
    anomaly_score = model.decision_function(features)[0]
    prediction = model.predict(features)[0]  # 1 = normal, -1 = anomaly

    # Map anomaly_score to risk_score 0-100 using the dynamic threshold.
    # Scores below threshold get mapped to HIGH_RISK_SCORE_FLOOR..100.
    # Scores significantly below threshold hit 95+.
    if anomaly_score <= threshold:
        # How far past the threshold (in score-space)
        depth = (threshold - anomaly_score) / max(abs(threshold), 0.01)
        risk_score = int(min(100, HIGH_RISK_SCORE_FLOOR + depth * 35))
    else:
        # Normal — map 0..1+ range to 0..49
        normal_factor = max(0.0, min(1.0, (1.0 - anomaly_score) / 1.5))
        risk_score = int(normal_factor * 49)

    # is_anomaly: model flags it AND risk score is meaningful
    is_anomaly = prediction == -1 and risk_score >= HIGH_RISK_SCORE_FLOOR

    # Confidence: how far past the threshold (capped 0..1)
    if is_anomaly:
        depth = (threshold - anomaly_score) / max(abs(threshold), 0.01)
        confidence = min(1.0, max(CONFIDENCE_FLOOR, depth / 3.0))
    else:
        normal_dist = (anomaly_score - threshold) / max(abs(threshold), 0.01)
        confidence = min(1.0, max(CONFIDENCE_FLOOR, normal_dist / 4.0))

    reason = _generate_anomaly_reason(log, {}, anomaly_score) if is_anomaly else "Normal behavior"

    result = {
        "is_anomaly": is_anomaly,
        "risk_score": min(100, risk_score),
        "reason": reason,
        "anomaly_score": round(anomaly_score, 4),
        "confidence": round(confidence, 4),
    }

    logger.debug("UEBA predict: score=%.4f threshold=%.4f → %s risk=%d",
                 anomaly_score, threshold, "ANOMALY" if is_anomaly else "OK", risk_score)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  Model health
# ═══════════════════════════════════════════════════════════════════════════════

def get_ueba_stats(model_path: str = MODEL_PATH) -> dict[str, Any]:
    """Return model status and training metadata."""
    import joblib
    if not os.path.exists(model_path):
        return {"status": "untrained", "model_path": model_path}
    try:
        bundle = joblib.load(model_path)
        if isinstance(bundle, dict) and "model" in bundle:
            model = bundle["model"]
            return {
                "status": "ready",
                "model_path": model_path,
                "n_estimators": model.n_estimators,
                "threshold": bundle.get("threshold", ANOMALY_THRESHOLD),
                "anomaly_percentile": bundle.get("anomaly_percentile", ANOMALY_PERCENTILE),
                "trained_at": bundle.get("trained_at", "unknown"),
                "n_samples": bundle.get("n_samples", 0),
                "features": bundle.get("features", []),
                "trained": True,
            }
        # Legacy format
        return {
            "status": "ready",
            "model_path": model_path,
            "n_estimators": bundle.n_estimators,
            "threshold": getattr(bundle, "ageixai_threshold", ANOMALY_THRESHOLD),
            "trained": True,
        }
    except Exception as exc:
        return {"status": "error", "model_path": model_path, "error": str(exc)}
