from __future__ import annotations

import os
from datetime import date, datetime, timedelta

import pytest


pytestmark = pytest.mark.skipif(
    not os.getenv("TUSHARE_TOKEN"),
    reason="TUSHARE_TOKEN is required for live Tushare validation",
)

if os.getenv("TUSHARE_TOKEN"):
    os.environ.setdefault("SMTP_HOST", "test_host")
    os.environ.setdefault("SMTP_USER", "test_user")
    os.environ.setdefault("SMTP_PASS", "test_pass")
    os.environ.setdefault("SMTP_TO", "test_to")


def _recent_window(days: int = 30) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


def test_fetch_index_daily() -> None:
    from app.datasources.tushare_source import fetch_index_daily

    start_date, end_date = _recent_window()
    quotes = fetch_index_daily("399300.SZ", start_date, end_date)

    assert quotes
    for quote in quotes:
        assert quote["close"] > 0


def test_fetch_trade_calendar() -> None:
    from app.datasources.tushare_source import fetch_trade_calendar

    start_date, end_date = _recent_window()
    trade_dates = fetch_trade_calendar(start_date, end_date)

    assert trade_dates
    for trade_date in trade_dates:
        assert datetime.fromisoformat(trade_date).weekday() < 5
