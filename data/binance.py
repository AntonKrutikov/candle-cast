from __future__ import annotations

import pandas as pd
import requests

BINANCE_KLINES_URL = "https://data-api.binance.vision/api/v3/klines"

VALID_INTERVALS = {
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1M",
}


def fetch_ohlcv(symbol: str, interval: str = "1h", limit: int = 500) -> pd.DataFrame:
    """Fetch OHLCV candles from Binance public API.

    Returns a DataFrame indexed by UTC timestamp with columns:
    open, high, low, close, volume (all float).
    """
    if interval not in VALID_INTERVALS:
        raise ValueError(f"Invalid interval {interval!r}. One of: {sorted(VALID_INTERVALS)}")
    if not 1 <= limit <= 1000:
        raise ValueError(f"limit must be in 1..1000, got {limit}")

    params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    resp = requests.get(BINANCE_KLINES_URL, params=params, timeout=10)
    resp.raise_for_status()
    raw = resp.json()

    if not raw:
        raise ValueError(f"No data returned for symbol {symbol!r}")

    df = pd.DataFrame(
        raw,
        columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades",
            "taker_buy_base", "taker_buy_quote", "ignore",
        ],
    )
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index("timestamp")[["open", "high", "low", "close", "volume"]]
    return df.astype(float)
