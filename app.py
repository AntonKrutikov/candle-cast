from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import forecast
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


def render_chart(
    history: pd.DataFrame,
    symbol: str,
    forecast_df: pd.DataFrame | None = None,
    tail: int = 120,
) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=history.index,
                open=history["open"],
                high=history["high"],
                low=history["low"],
                close=history["close"],
                name="History",
                increasing_line_color="#26a69a",
                decreasing_line_color="#ef5350",
            )
        ]
    )

    if forecast_df is not None and not forecast_df.empty:
        fig.add_trace(
            go.Candlestick(
                x=forecast_df.index,
                open=forecast_df["open"],
                high=forecast_df["high"],
                low=forecast_df["low"],
                close=forecast_df["close"],
                name="Forecast",
                increasing_line_color="#42a5f5",
                decreasing_line_color="#ab47bc",
                opacity=0.7,
            )
        )
        fig.add_vline(
            x=history.index[-1],
            line_width=1,
            line_dash="dash",
            line_color="rgba(200,200,200,0.6)",
        )

    tail = min(tail, len(history))
    visible_hist = history.iloc[-tail:]
    if forecast_df is not None and not forecast_df.empty:
        x_start = visible_hist.index[0]
        x_end = forecast_df.index[-1]
        lo = float(min(visible_hist["low"].min(), forecast_df["low"].min()))
        hi = float(max(visible_hist["high"].max(), forecast_df["high"].max()))
    else:
        x_start = visible_hist.index[0]
        x_end = visible_hist.index[-1]
        lo = float(visible_hist["low"].min())
        hi = float(visible_hist["high"].max())
    pad = (hi - lo) * 0.05 or hi * 0.01

    fig.update_layout(
        title=f"{symbol} — history" + (" + forecast" if forecast_df is not None else ""),
        xaxis_title="Time (UTC)",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        xaxis=dict(range=[x_start, x_end], autorange=False),
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
        try:
            with st.spinner("Generating forecast…"):
                forecast_df = forecast.predict(history)
        except Exception as e:
            st.error(f"Forecast failed: {e}")
            st.plotly_chart(render_chart(history, symbol), width="stretch")
            st.caption(f"Loaded {len(history)} candles · last: {history.index[-1]}")
        else:
            st.plotly_chart(render_chart(history, symbol, forecast_df), width="stretch")
            st.caption(
                f"History: {len(history)} candles (last {history.index[-1]}) · "
                f"Forecast: {len(forecast_df)} candles ahead"
            )
