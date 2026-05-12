"""Refresh data/symbols/binance.json from Binance public API.

Fetches the set of TRADING spot symbols and sorts them by 24h quote volume
(descending), so popular pairs surface first in the autocomplete dropdown.

Run from project root:
    uv run python scripts/refresh_symbols.py
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"
TICKER_24HR_URL = "https://api.binance.com/api/v3/ticker/24hr"

OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "symbols" / "binance.json"

# Quote asset priority tiers. Lower tier number = surfaces earlier in the list.
# Within each tier, symbols are ranked by 24h quote volume.
QUOTE_TIERS = {"USDT": 0, "USDC": 1, "FDUSD": 1, "BTC": 2, "ETH": 3, "BNB": 4}
OTHER_TIER = 5


def fetch_trading_symbols() -> list[dict]:
    resp = requests.get(EXCHANGE_INFO_URL, timeout=15)
    resp.raise_for_status()
    info = resp.json()
    return [
        s
        for s in info["symbols"]
        if s.get("status") == "TRADING" and s.get("isSpotTradingAllowed")
    ]


def fetch_volumes() -> dict[str, float]:
    resp = requests.get(TICKER_24HR_URL, timeout=30)
    resp.raise_for_status()
    return {row["symbol"]: float(row["quoteVolume"]) for row in resp.json()}


def main() -> None:
    print("Fetching exchangeInfo…")
    symbols = fetch_trading_symbols()
    print(f"  {len(symbols)} TRADING spot symbols")

    print("Fetching 24h ticker stats…")
    volumes = fetch_volumes()

    def sort_key(s: dict) -> tuple[int, float]:
        tier = QUOTE_TIERS.get(s["quoteAsset"], OTHER_TIER)
        return (tier, -volumes.get(s["symbol"], 0.0))

    ranked = [s["symbol"] for s in sorted(symbols, key=sort_key)]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(ranked, indent=2) + "\n")
    print(f"Wrote {len(ranked)} symbols → {OUT_PATH.relative_to(Path.cwd())}")
    print(f"Top 10: {ranked[:10]}")


if __name__ == "__main__":
    main()
