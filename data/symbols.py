from __future__ import annotations

import json
from pathlib import Path

SYMBOLS_DIR = Path(__file__).parent / "symbols"


def load_crypto_symbols() -> list[str]:
    """Binance spot trading symbols, ranked with major quote assets first."""
    return json.loads((SYMBOLS_DIR / "binance.json").read_text())


def load_stock_symbols() -> list[str]:
    """Curated list of popular Yahoo Finance tickers."""
    return json.loads((SYMBOLS_DIR / "stocks.json").read_text())
