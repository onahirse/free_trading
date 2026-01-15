from typing import Tuple
import pandas as pd

def make_features(df: pd.DataFrame, horizon: int = 5) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    out = df.copy()

    # базовые признаки
    out["ret_1"] = out["Close"].pct_change()
    out["ret_vol_30"] = out["ret_1"].rolling(30).std()

    # RSI
    delta = out["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    out["rsi_14"] = 100 - (100 / (1 + rs))

    # EMA
    out["ema_12"] = out["Close"].ewm(span=12, adjust=False).mean()
    out["ema_26"] = out["Close"].ewm(span=26, adjust=False).mean()
    out["ema_spread"] = (out["ema_12"] - out["ema_26"]) / out["Close"]

    # ATR
    high_low = out["High"] - out["Low"]
    high_close = (out["High"] - out["Close"].shift()).abs()
    low_close = (out["Low"] - out["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    out["atr_14"] = tr.rolling(14).mean()

    # таргеты
    out["future_close"] = out["Close"].shift(-horizon)
    y_reg = (out["future_close"] - out["Close"]) / out["Close"]     # регрессия
    y_cls = (y_reg > 0).astype(int)                                # классификация

    # сдвигаем фичи на 1, чтобы не было утечки
    X = out.drop(columns=["future_close"]).shift(1)

    # # убираем NaN
    # X, y_reg, y_cls = X.dropna(), y_reg.loc[X.index], y_cls.loc[X.index]
    # Очищаем всё по общему индексу
    df_all = pd.concat([X, y_reg, y_cls], axis=1).dropna()
    X = df_all.drop(columns=[0, 1]) if isinstance(df_all.columns[-2], int) else df_all.iloc[:,:-2]
    y_reg = df_all.iloc[:, -2]
    y_cls = df_all.iloc[:, -1]
    
    return X, y_reg, y_cls

