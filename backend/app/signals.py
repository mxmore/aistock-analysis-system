
import numpy as np
import pandas as pd

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = np.where(delta > 0, delta, 0.0)
    down = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(up, index=series.index).ewm(alpha=1/period, adjust=False).mean()
    roll_down = pd.Series(down, index=series.index).ewm(alpha=1/period, adjust=False).mean()
    rs = roll_up / (roll_down + 1e-9)
    return 100.0 - (100.0 / (1.0 + rs))

def macd(series: pd.Series, fast=12, slow=26, signal=9):
    e1 = series.ewm(span=fast, adjust=False).mean()
    e2 = series.ewm(span=slow, adjust=False).mean()
    macd_line = e1 - e2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def compute_signals(df: pd.DataFrame, short=10, long=30) -> pd.DataFrame:
    df = df.sort_values("trade_date").copy()
    df["ma_s"] = df["close"].rolling(short).mean()
    df["ma_l"] = df["close"].rolling(long).mean()
    df["rsi"] = rsi(df["close"], 14)
    macd_line, signal_line, hist = macd(df["close"])
    df["macd"] = macd_line
    df["macd_sig"] = signal_line
    df["macd_hist"] = hist

    score = np.zeros(len(df))
    cross_up = (df["ma_s"] > df["ma_l"]) & (df["ma_s"].shift(1) <= df["ma_l"].shift(1))
    cross_dn = (df["ma_s"] < df["ma_l"]) & (df["ma_s"].shift(1) >= df["ma_l"].shift(1))
    score = score + np.where(cross_up, 20, 0) - np.where(cross_dn, 20, 0)
    score += np.clip(50 - (df["rsi"] - 50).abs(), -15, 15)
    score += np.where((df["macd"] > df["macd_sig"]) & (df["macd"].shift(1) <= df["macd_sig"].shift(1)), 10, 0)

    df["signal_score"] = score
    df["action"] = np.where(
        df["signal_score"] >= 15, "BUY",
        np.where(df["signal_score"] <= -15, "TRIM", "HOLD")
    )
    return df
