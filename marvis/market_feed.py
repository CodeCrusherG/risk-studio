"""Public ECB reference FX rates for the Risk Studio dashboard."""

from __future__ import annotations

import csv
import ssl
from datetime import UTC, datetime
from io import StringIO
from math import isfinite
from threading import Lock
from time import monotonic
from urllib.request import Request, urlopen

import certifi

from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/api/risk-studio", tags=["risk-studio"])
ECB_URL = (
    "https://data-api.ecb.europa.eu/service/data/EXR/"
    "D.USD+GBP+JPY+INR.EUR.SP00.A?lastNObservations=121&format=csvdata"
)
_cache: tuple[float, dict] | None = None
_lock = Lock()


def _fetch_rates() -> dict:
    request = Request(ECB_URL, headers={"Accept": "text/csv", "User-Agent": "RiskStudio/2.5"})
    with urlopen(request, timeout=8, context=ssl.create_default_context(cafile=certifi.where())) as response:
        data = response.read(1_000_001)
    if len(data) > 1_000_000:
        raise ValueError("ECB response exceeded the size limit")
    rows = csv.DictReader(StringIO(data.decode("utf-8-sig")))
    series: dict[str, list[dict]] = {currency: [] for currency in ("USD", "GBP", "JPY", "INR")}
    for row in rows:
        currency = row.get("CURRENCY", "")
        if currency not in series:
            continue
        value = float(row["OBS_VALUE"])
        date = row["TIME_PERIOD"]
        datetime.strptime(date, "%Y-%m-%d")
        if value <= 0 or not isfinite(value):
            continue
        series[currency].append({"date": date, "value": value})
    if any(len(values) < 2 for values in series.values()):
        raise ValueError("ECB response did not contain the expected currency observations")
    for values in series.values():
        values.sort(key=lambda item: item["date"])
    return {
        "source": "European Central Bank",
        "source_url": "https://data.ecb.europa.eu/data/datasets/EXR",
        "basis": "Units of quote currency per EUR; ECB daily reference rates",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "rates": [
            {
                "currency": currency,
                "date": values[-1]["date"],
                "value": values[-1]["value"],
                "previous_value": values[-2]["value"],
                "change_pct": (values[-1]["value"] / values[-2]["value"] - 1) * 100,
            }
            for currency, values in series.items()
        ],
        "eur_usd_history": series["USD"][-121:],
    }


@router.get("/market-feed")
def market_feed() -> dict:
    global _cache
    with _lock:
        if _cache and monotonic() - _cache[0] < 900:
            return _cache[1]
        try:
            result = _fetch_rates()
        except (OSError, UnicodeError, KeyError, ValueError) as exc:
            raise HTTPException(status_code=503, detail="ECB market feed is temporarily unavailable") from exc
        _cache = (monotonic(), result)
        return result
