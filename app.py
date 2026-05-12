from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data.binance import fetch_ohlcv as fetch_binance
from data.symbols import load_crypto_symbols, load_stock_symbols
from data.yfinance_source import fetch_ohlcv as fetch_yfinance

st.set_page_config(page_title="CandleCast", layout="wide")
st.title("CandleCast")
st.caption("AI-powered price forecasts for crypto and stocks.")

CRYPTO_INTERVALS = ["15m", "1h", "4h", "1d"]
STOCK_INTERVALS = ["30m", "1h", "1d"]

col1, col2, col3, col4 = st.columns([1, 2, 1, 1], vertical_alignment="bottom")
with col1:
    asset_type = st.selectbox("Asset", ["Crypto", "Stock"])
with col2:
    symbols = load_crypto_symbols() if asset_type == "Crypto" else load_stock_symbols()
    symbol = st.selectbox("Ticker", symbols, help="Type to filter")
with col3:
    intervals = CRYPTO_INTERVALS if asset_type == "Crypto" else STOCK_INTERVALS
    interval = st.selectbox("Interval", intervals, index=1)
with col4:
    submitted = st.button("Forecast", type="primary", width="stretch")


def load_history(asset_type: str, symbol: str, interval: str) -> pd.DataFrame:
    if asset_type == "Crypto":
        return fetch_binance(symbol, interval=interval, limit=500)
    period = "60d" if interval in {"30m", "1h"} else "2y"
    return fetch_yfinance(symbol, period=period, interval=interval)


def render_chart(history: pd.DataFrame, symbol: str, tail: int = 120) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=history.index,
                open=history["open"],
                high=history["high"],
                low=history["low"],
                close=history["close"],
                name="History",
            )
        ]
    )
    tail = min(tail, len(history))
    visible = history.iloc[-tail:]
    lo = float(visible["low"].min())
    hi = float(visible["high"].max())
    pad = (hi - lo) * 0.05 or hi * 0.01
    fig.update_layout(
        title=f"{symbol} — history",
        xaxis_title="Time (UTC)",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        xaxis=dict(range=[visible.index[0], visible.index[-1]], autorange=False),
        yaxis=dict(range=[lo - pad, hi + pad], autorange=False, fixedrange=False),
        height=600,
    )
    return fig


if submitted:
    try:
        with st.spinner(f"Fetching {symbol}…"):
            history = load_history(asset_type, symbol, interval)
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
    else:
        st.plotly_chart(render_chart(history, symbol), width="stretch")
        st.caption(f"Loaded {len(history)} candles · last: {history.index[-1]}")
