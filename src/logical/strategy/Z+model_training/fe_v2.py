from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, List, Dict, Optional
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score, log_loss, precision_recall_fscore_support
from lightgbm import LGBMClassifier
import warnings

# =============== ВСПОМОГАТЕЛЬНЫЕ УТИЛИТЫ ===============

def _safe_div(a, b):
    out = np.divide(a, b, out=np.zeros_like(a, dtype=float), where=(b != 0))
    return out

def _ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Date" in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("Нужен DatetimeIndex (или колонка Date).")
    return df.sort_index()

# =============== ФИЧИ (улучшенная версия) ===============

def make_features_v2(df: pd.DataFrame, horizon: int = 5) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Улучшенная версия вашей функции:
    - больше технических индикаторов
    - нормализация некоторых величин к цене
    - корректный shift всех фич (t -> решение на t, результат на t+1..t+h)
    """
    out = _ensure_datetime_index(df)

    # Базовые возвраты и волатильность
    out["ret_1"] = out["Close"].pct_change()
    for l in [2, 3, 5, 10]:
        out[f"ret_{l}"] = out["Close"].pct_change(l)

    # Скользящие средние и спрэды (MACD-подобное)
    out["ema_12"] = out["Close"].ewm(span=12, adjust=False).mean()
    out["ema_26"] = out["Close"].ewm(span=26, adjust=False).mean()
    out["ema_spread"] = (out["ema_12"] - out["ema_26"]) / out["Close"]
    out["macd"] = out["ema_12"] - out["ema_26"]
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["macd_hist"] = out["macd"] - out["macd_signal"]

    # RSI c экспоненциальным сглаживанием (Wilder)
    delta = out["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = _safe_div(avg_gain, avg_loss)
    out["rsi_14"] = 100 - (100 / (1 + rs))

    # Stochastic Oscillator
    low_min_14 = out["Low"].rolling(14).min()
    high_max_14 = out["High"].rolling(14).max()
    out["stoch_k"] = _safe_div(out["Close"] - low_min_14, (high_max_14 - low_min_14)) * 100
    out["stoch_d"] = out["stoch_k"].rolling(3).mean()

    # Bollinger Bands
    ma20 = out["Close"].rolling(20).mean()
    std20 = out["Close"].rolling(20).std()
    out["bb_pos"] = _safe_div(out["Close"] - ma20, std20)          # положение в полосах
    out["bb_width"] = 2 * std20 / out["Close"]

    # True Range / ATR (Wilder)
    prev_close = out["Close"].shift(1)
    tr = pd.concat([
        (out["High"] - out["Low"]).abs(),
        (out["High"] - prev_close).abs(),
        (out["Low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    atr14 = tr.ewm(alpha=1/14, adjust=False).mean()
    out["atr_14"] = atr14
    out["atr_pct"] = _safe_div(atr14, out["Close"])

    # Диапазоны и форма свечи
    out["hl_range_pct"] = _safe_div(out["High"] - out["Low"], out["Close"])
    out["oc_range_pct"] = _safe_div(out["Close"] - out.get("Open", out["Close"]), out["Close"])
    out["upper_wick"] = _safe_div(out["High"] - out[["Close", "Open"]].max(axis=1), out["Close"])
    out["lower_wick"] = _safe_div(out[["Close", "Open"]].min(axis=1) - out["Low"], out["Close"])

    # Волатильности
    for w in [5, 10, 20, 30]:
        out[f"ret_vol_{w}"] = out["ret_1"].rolling(w).std()
        out[f"ret_ewmvol_{w}"] = out["ret_1"].ewm(span=w, adjust=False).std()

    # Объём (если есть)
    if "Volume" in out.columns:
        out["vol_chg_1"] = out["Volume"].pct_change()
        out["vol_ma_20"] = out["Volume"].rolling(20).mean()
        out["vol_z_20"] = _safe_div(out["Volume"] - out["vol_ma_20"], out["Volume"].rolling(20).std())


    # Таргеты: форвардная доходность на горизонте и бинарная метка
    # Используем log-доходность (устойчивее при больших шагов)
    future_close = out["Close"].shift(-horizon)
    
    y_reg = ((future_close - out["Close"]) / out["Close"]) * 100
    
    # y_reg = np.log(_safe_div(future_close, out["Close"]))      # лог-ретёрн за horizon
    
    # Классификация: можно добавить "мёртвую зону" для шумовых движений
    threshold = 0.0  # при желании сделайте 0.001 (0.1%) и используйте 2-класса +/- (а нули отфильтровать)
    y_cls = (y_reg > threshold).astype(int)

    # Сдвиг фич на 1 бар, чтобы решение принималось на t, а результат на t+1..t+h
    features = [
        c for c in out.columns
        if c not in {"Close", "Open", "High", "Low", "future_close"}  # базовые цены в сыром виде не используем, чтобы не схватить утечку со shift?
    ]
    X = out[features].shift(1)

    # Синхронная очистка
    # df_all = pd.concat([X, y_reg.rename("y_reg"), y_cls.rename("y_cls")], axis=1).dropna()
    df_all = pd.concat([
    X,
    pd.Series(y_reg, index=X.index, name="y_reg"),
    pd.Series(y_cls, index=X.index, name="y_cls")
    ], axis=1).dropna()

    X = df_all.drop(columns=["y_reg", "y_cls"])
    y_reg = df_all["y_reg"]
    y_cls = df_all["y_cls"].astype(int)

    # # Явно отметить категориальные признаки
    # for cat_col in ["dow", "month", "is_month_end"]:
    #     if cat_col in X.columns:
    #         X[cat_col] = X[cat_col].astype("category")

    return X, y_reg, y_cls
