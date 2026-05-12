from __future__ import annotations

import os
from typing import Final

import pandas as pd
import streamlit as st

from model import Kronos, KronosPredictor, KronosTokenizer

VARIANTS: Final[dict[str, dict]] = {
    "mini":  {"model": "NeoQuasar/Kronos-mini",  "tokenizer": "NeoQuasar/Kronos-Tokenizer-2k",   "max_context": 2048},
    "small": {"model": "NeoQuasar/Kronos-small", "tokenizer": "NeoQuasar/Kronos-Tokenizer-base", "max_context": 512},
    "base":  {"model": "NeoQuasar/Kronos-base",  "tokenizer": "NeoQuasar/Kronos-Tokenizer-base", "max_context": 512},
}

DEFAULT_PRED_LEN: Final = 24
DEFAULT_LOOKBACK: Final = 256


def _variant() -> dict:
    name = os.getenv("KRONOS_MODEL", "mini").lower()
    if name not in VARIANTS:
        raise ValueError(f"KRONOS_MODEL must be one of {sorted(VARIANTS)}; got {name!r}")
    return VARIANTS[name]


@st.cache_resource(show_spinner="Loading forecast model…")
def _load(model_id: str, tokenizer_id: str, max_context: int) -> KronosPredictor:
    tokenizer = KronosTokenizer.from_pretrained(tokenizer_id)
    model = Kronos.from_pretrained(model_id)
    return KronosPredictor(model, tokenizer, max_context=max_context)


def predict(
    history: pd.DataFrame,
    pred_len: int = DEFAULT_PRED_LEN,
    lookback: int = DEFAULT_LOOKBACK,
) -> pd.DataFrame:
    cfg = _variant()
    predictor = _load(cfg["model"], cfg["tokenizer"], cfg["max_context"])

    window = min(lookback, cfg["max_context"], len(history))
    x = history.tail(window)

    step = x.index[-1] - x.index[-2]
    future = pd.DatetimeIndex(
        [x.index[-1] + step * i for i in range(1, pred_len + 1)],
        name="timestamp",
    )

    pred = predictor.predict(
        df=x[["open", "high", "low", "close", "volume"]].reset_index(drop=True),
        x_timestamp=pd.Series(x.index),
        y_timestamp=pd.Series(future),
        pred_len=pred_len,
        T=1.0,
        top_p=0.9,
        sample_count=1,
        verbose=False,
    )
    pred.index = future
    return pred[["open", "high", "low", "close", "volume"]].astype(float)
