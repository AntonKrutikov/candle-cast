from __future__ import annotations

import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import forecast
from data.binance import fetch_ohlcv as fetch_binance
from data.symbols import load_crypto_symbols, load_stock_symbols
from data.yfinance_source import fetch_ohlcv as fetch_yfinance

st.set_page_config(page_title="CandleCast", layout="wide")


_primary = st.get_option("theme.primaryColor")

st.markdown(
    f"""
    <style>
    .stMainBlockContainer {{
        background:
            radial-gradient(
            ellipse 70% 260px at top center,
            rgba(184, 134, 11, 0.24) 0%,
            rgba(184, 134, 11, 0.10) 35%,
            #181A20 100%
        );
    }}
    a.cc-anchor-btn,
    a.cc-anchor-btn:visited {{
        display:block;text-align:center;
        padding:0.4rem 0.75rem;
        border:1px solid rgba(250,250,250,0.2);
        border-radius:0.5rem;
        color:rgb(250,250,250) !important;
        text-decoration:none !important;
        font-weight:400;
        transition:border-color 120ms ease, color 120ms ease;
    }}
    a.cc-anchor-btn:hover {{
        border-color:{_primary};
        color:{_primary} !important;
        text-decoration:none !important;
    }}
    a.cc-anchor-btn:active {{
        background-color:{_primary}26;
    }}
    [class*="st-key-cc_card"] {{
        # background:linear-gradient(180deg,#262B33 0%,#20252C 100%);
        border:1px solid rgba(0,0,0,0.5);
        border-radius:18px;
        padding:24px;
        box-shadow:0 10px 30px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.04);
    }}
    </style>
    """,
    unsafe_allow_html=True,
)
with st.container(
    horizontal=True, vertical_alignment="center", horizontal_alignment="center"
):
    st.image("assets/logo.svg", width=128)
    st.markdown(
        f'<h1 style="margin:0;padding:0;">Candle<span style="color:{_primary}">Cast</span></h1>',
        unsafe_allow_html=True,
    )
st.header(
    ":primary[AI-powered market forecasts in seconds]",
    text_alignment="center",
    anchor="forecast",
)
st.caption(
    "From ticker to forecast in seconds — AI-powered price predictions for crypto and stock markets.",
    text_alignment="center",
)

st.container(height=24, border=False)


CRYPTO_INTERVALS = ["15m", "1h", "4h", "1d"]
STOCK_INTERVALS = ["30m", "1h", "1d"]
POPULAR_CRYPTO = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
POPULAR_STOCKS = ["AAPL", "TSLA", "NVDA"]


def _on_popular_change(state_key: str) -> None:
    val = st.session_state.get(state_key)
    if val:
        st.session_state.ticker_select = val


_, center, _ = st.columns([2, 6, 2])

with center, st.container(key="cc_card_forecast"):
    st.caption("Choose a market, ticker, and interval.")
    col1, col2, col3, col4 = st.columns([1, 2, 1, 1], vertical_alignment="bottom")
    with col1:
        asset_type = st.selectbox("Asset", ["Crypto", "Stock"])
    with col2:
        symbols = (
            load_crypto_symbols() if asset_type == "Crypto" else load_stock_symbols()
        )
        if st.session_state.get("ticker_select") not in symbols:
            st.session_state.ticker_select = symbols[0]
        symbol = st.selectbox(
            "Ticker", symbols, key="ticker_select", help="Type to filter"
        )
    with col3:
        intervals = CRYPTO_INTERVALS if asset_type == "Crypto" else STOCK_INTERVALS
        interval = st.selectbox("Interval", intervals, index=1)
    with col4:
        button_slot = st.empty()


def _start_forecast() -> None:
    st.session_state.forecasting = True


if st.session_state.get("forecasting"):
    button_slot.button(
        "Forecasting…",
        type="primary",
        width="stretch",
        disabled=True,
        icon=":material/progress_activity:",
        key="forecast_btn_busy",
    )
    submitted = True
else:
    button_slot.button(
        "Forecast",
        type="primary",
        width="stretch",
        icon=":material/auto_awesome:",
        on_click=_start_forecast,
        key="forecast_btn_idle",
    )
    submitted = False


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
    reveal: int | None = None,
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
        shown = forecast_df if reveal is None else forecast_df.iloc[:reveal]
        fig.add_trace(
            go.Candlestick(
                x=shown.index,
                open=shown["open"],
                high=shown["high"],
                low=shown["low"],
                close=shown["close"],
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
        showlegend=True,
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

    st.container(height=16, border=False)

    popular = POPULAR_CRYPTO if asset_type == "Crypto" else POPULAR_STOCKS
    popular_key = f"popular_pills_{asset_type}"
    st.session_state[popular_key] = symbol if symbol in popular else None
    with st.container(
        horizontal=True, vertical_alignment="center", horizontal_alignment="left"
    ):
        st.caption("Popular:", width="content")
        st.pills(
            "Popular",
            options=[t for t in popular if t in symbols],
            selection_mode="single",
            key=popular_key,
            on_change=_on_popular_change,
            args=(popular_key,),
            label_visibility="collapsed",
            width="content",
        )

    st.container(height=16, border=False)

    with st.container(key="cc_card_chart"):
        chart_slot = st.empty()
        caption_slot = st.empty()

        chart_slot.plotly_chart(render_chart(history, symbol), width="stretch")
        caption_slot.caption(
            f"Loaded {len(history)} candles · last: {history.index[-1]:%Y-%m-%d %H:%M} UTC"
        )

    forecast_df: pd.DataFrame | None = None
    forecast_error: str | None = None
    if submitted:
        try:
            forecast_df = forecast.predict(history)
        except Exception as e:
            forecast_error = str(e)

        if forecast_df is not None:
            step = 1
            for i in range(step, len(forecast_df) + step, step):
                chart_slot.plotly_chart(
                    render_chart(history, symbol, forecast_df, reveal=i),
                    width="stretch",
                )
                time.sleep(0.03)

        st.session_state.forecasting = False
        button_slot.button(
            "Forecast",
            type="primary",
            width="stretch",
            icon=":material/auto_awesome:",
            on_click=_start_forecast,
            key="forecast_btn_done",
        )

    if forecast_error:
        st.error(f"Forecast failed: {forecast_error}")

    st.container(height=48, border=False)

    FEATURES = [
        (
            ":material/neurology:",
            "AI Forecasts",
            "Advanced AI models analyze market data and generate future OHLCV candles with precision.",
        ),
        (
            ":material/candlestick_chart:",
            "Interactive Charts",
            "Explore historical data and AI predictions with a full-featured, interactive charting experience.",
        ),
        (
            ":material/public:",
            "Crypto + Stocks",
            "Supports crypto pairs from Binance and stocks via market data integrations.",
        ),
        (
            ":material/share:",
            "Shareable Insights",
            "Download or share your forecast charts with others. Perfect for research and discussion.",
        ),
    ]

    feature_cols = st.columns(4, gap="medium")
    for i, (col, (icon, title, body)) in enumerate(zip(feature_cols, FEATURES)):
        with col, st.container(key=f"cc_card_feature_{i}", height="stretch"):
            st.markdown(f"# :primary[{icon}]")
            st.markdown(f"**{title}**")
            st.caption(body)

    st.container(height=64, border=False)

    st.header(":primary[Simple pricing]", text_alignment="center")
    st.caption(
        "Start free, upgrade when you need more forecasts and power.",
        text_alignment="center",
    )

    st.container(height=24, border=False)

    _, free_col, pro_col, _ = st.columns([1, 2, 2, 1], gap="large")

    with free_col, st.container(key="cc_card_pricing_free", height="stretch"):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.subheader("Free")
            st.markdown(":gray-badge[:material/rocket_launch: Get started]")
        st.markdown("## $0 :gray[/ month]")
        st.caption("For casual exploration of AI market forecasts.")
        st.divider()
        st.markdown(":primary[:material/check:] 10 forecasts per day")
        st.markdown(":primary[:material/check:] Crypto + stock tickers")
        st.markdown(":primary[:material/check:] Interactive charts")
        st.markdown(":gray[:material/close:] Priority compute")
        st.markdown(":gray[:material/close:] CSV / PNG export")
        st.container(height=8, border=False)
        st.markdown(
            '<a href="#forecast" class="cc-anchor-btn">Try it now</a>',
            unsafe_allow_html=True,
        )

    with pro_col, st.container(key="cc_card_pricing_pro", height="stretch"):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.subheader("Pro")
            st.markdown(":primary-badge[:material/star: Most popular]")
        st.markdown("## $19 :gray[/ month]")
        st.caption("For traders and researchers who need more headroom.")
        st.divider()
        st.markdown(":primary[:material/check:] Unlimited forecasts")
        st.markdown(":primary[:material/check:] All intervals & longer horizons")
        st.markdown(":primary[:material/check:] Priority compute")
        st.markdown(":primary[:material/check:] CSV / PNG export")
        st.markdown(":primary[:material/check:] Email support")
        st.container(height=8, border=False)
        st.button(
            "Upgrade to Pro",
            type="primary",
            width="stretch",
            key="pro_cta",
            disabled=True,
        )

    st.container(height=64, border=False)
    st.divider()
    st.caption(
        "Market forecasts are generated for research and educational purposes only. "
        "CandleCast does not provide financial advice or guarantee future price movement.",
        text_alignment="center",
    )
