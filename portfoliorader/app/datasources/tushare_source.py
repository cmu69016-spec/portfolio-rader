from __future__ import annotations

from functools import lru_cache
from typing import Any

import tushare as ts


def _to_yyyymmdd(value: str) -> str:
    return value.replace("-", "")


def _to_iso_date(value: Any) -> str:
    text = str(value)
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text[:10]


@lru_cache(maxsize=1)
def _pro_api() -> Any:
    from app.config import settings

    return ts.pro_api(settings.tushare_token)


def fetch_index_daily(index_code: str, start_date: str, end_date: str) -> list[dict]:
    df = _pro_api().index_daily(
        ts_code=index_code,
        start_date=_to_yyyymmdd(start_date),
        end_date=_to_yyyymmdd(end_date),
    )
    if df.empty:
        return []

    records: list[dict] = []
    for _, row in df.sort_values("trade_date").iterrows():
        records.append(
            {
                "trade_date": _to_iso_date(row.get("trade_date")),
                "close": float(row.get("close")),
            }
        )
    return records


def fetch_trade_calendar(start_date: str, end_date: str) -> list[str]:
    df = _pro_api().trade_cal(
        exchange="",
        start_date=_to_yyyymmdd(start_date),
        end_date=_to_yyyymmdd(end_date),
        is_open="1",
    )
    if df.empty:
        return []

    return [
        _to_iso_date(row.get("cal_date"))
        for _, row in df.sort_values("cal_date").iterrows()
    ]
