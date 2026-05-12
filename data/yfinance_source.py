from __future__ import annotations

import pandas as pd
import yfinance as yf


def fetch_ohlcv(symbol: str, period: str = "60d", interval: str = "1h") -> pd.DataFrame:
    """Fetch OHLCV candles from Yahoo Finance via yfinance.

    Returns a DataFrame indexed by UTC timestamp with columns:
    open, high, low, close, volume (all float).
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=False)

    if df.empty:
        raise ValueError(f"No data returned for symbol {symbol!r}")

    df = df.rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    )[["open", "high", "low", "close", "volume"]]

    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df.index.name = "timestamp"
    return df.astype(float)
