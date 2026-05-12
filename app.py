from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import forecast
from data.binance import fetch_ohlcv as fetch_binance
from data.symbols import load_crypto_symbols, load_stock_symbols
from data.yfinance_source import fetch_ohlcv as fetch_yfinance

st.set_page_config(page_title="CandleCast", layout="wide")


_primary = st.get_option("theme.primaryColor")
with st.container(
    horizontal=True, vertical_alignment="center", horizontal_alignment="center"
):
    st.image("assets/logo.svg", width=128)
    st.markdown(
        f'<h1 style="margin:0;padding:0;">Candle<span style="color:{_primary}">Cast</span></h1>',
        unsafe_allow_html=True,
    )
st.header(":primary[AI-powered market forecasts in seconds]", text_alignment="center")
st.caption(
    "From ticker to forecast in seconds — AI-powered price predictions for crypto and stock markets.",
    text_alignment="center",
)

st.container(height=24, border=False)


CRYPTO_INTERVALS = ["15m", "1h", "4h", "1d"]
STOCK_INTERVALS = ["30m", "1h", "1d"]

_, center, _ = st.columns([1, 6, 1])

with center:
    col1, col2, col3, col4 = st.columns([1, 2, 1, 1], vertical_alignment="bottom")
    with col1:
        asset_type = st.selectbox("Asset", ["Crypto", "Stock"])
    with col2:
        symbols = (
            load_crypto_symbols() if asset_type == "Crypto" else load_stock_symbols()
        )
        symbol = st.selectbox("Ticker", symbols, help="Type to filter")
    with col3:
        intervals = CRYPTO_INTERVALS if asset_type == "Crypto" else STOCK_INTERVALS
        interval = st.selectbox("Interval", intervals, index=1)
    with col4:
        submitted = st.button(
            "Forecast", type="primary", width="stretch", icon=":material/auto_awesome:"
        )


@st.cache_data(show_spinner=False)
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
                increasing_line_color="#0ECB81",
                decreasing_line_color="#F6465D",
                increasing_fillcolor="#0ECB81",
                decreasing_fillcolor="#F6465D",
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
                increasing_line_color="#F0B90B",
                decreasing_line_color="#7A4DFF",
                increasing_fillcolor="#F0B90B",
                decreasing_fillcolor="#7A4DFF",
                opacity=0.75,
            )
        )
        fig.add_vline(
            x=history.index[-1],
            line_width=1,
            line_dash="dash",
            line_color="rgba(240,185,11,0.6)",
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

    if forecast_df is not None and not forecast_df.empty:
        title = (
            f"{symbol} — history "
            f"<span style='color:{_primary}'>"
            f"+ forecast · {len(forecast_df)} candles ahead</span>"
        )
    else:
        title = f"{symbol} — history"

    fig.update_layout(
        title=title,
        xaxis_title="Time (UTC)",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        xaxis=dict(
            range=[x_start, x_end],
            autorange=False,
            gridcolor="#2B3139",
            zerolinecolor="#2B3139",
        ),
        yaxis=dict(
            range=[lo - pad, hi + pad],
            autorange=False,
            fixedrange=False,
            gridcolor="#2B3139",
            zerolinecolor="#2B3139",
        ),
        height=600,
        paper_bgcolor="#181A20",
        plot_bgcolor="#181A20",
        font=dict(color="#EAECEF", family="Inter, -apple-system, Segoe UI, sans-serif"),
        legend=dict(bgcolor="rgba(30,35,41,0.8)", bordercolor="#2B3139", borderwidth=1),
    )
    return fig


with center:
    try:
        with st.spinner(f"Loading {symbol}…"):
            history = load_history(asset_type, symbol, interval)
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        st.stop()

    st.container(height=24, border=False)

    chart_slot = st.empty()
    caption_slot = st.empty()
    status_slot = st.empty()

    chart_slot.plotly_chart(render_chart(history, symbol), width="stretch")
    caption_slot.caption(
        f"Loaded {len(history)} candles · last: {history.index[-1]:%Y-%m-%d %H:%M} UTC"
    )

    forecast_df: pd.DataFrame | None = None
    forecast_error: str | None = None
    if submitted:
        try:
            with status_slot, st.spinner("Generating forecast…"):
                forecast_df = forecast.predict(history)
        except Exception as e:
            forecast_error = str(e)
        status_slot.empty()

        if forecast_df is not None:
            chart_slot.plotly_chart(
                render_chart(history, symbol, forecast_df), width="stretch"
            )
            caption_slot.caption(
                f"Loaded {len(history)} candles · last: "
                f"{history.index[-1]:%Y-%m-%d %H:%M} UTC"
            )

    if forecast_error:
        st.error(f"Forecast failed: {forecast_error}")
