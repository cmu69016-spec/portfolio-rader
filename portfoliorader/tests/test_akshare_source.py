from __future__ import annotations

from datetime import date, timedelta

from app.datasources.akshare_source import (
    fetch_daily_quote,
    fetch_fund_holdings,
    fetch_money_flow,
)


def _recent_window(days: int = 10) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


def _previous_weekday() -> str:
    day = date.today() - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day.isoformat()


def test_fetch_daily_quote() -> None:
    start_date, end_date = _recent_window()
    quotes = fetch_daily_quote("000001", start_date, end_date)

    assert 0 < len(quotes) <= 7
    for quote in quotes:
        assert {"trade_date", "open", "high", "low", "close", "volume"} <= quote.keys()
        assert isinstance(quote["close"], float)
        assert quote["close"] > 0


def test_fetch_money_flow() -> None:
    flow = fetch_money_flow("000001", _previous_weekday())

    assert "super_net_in" in flow
    assert isinstance(flow["super_net_in"], int | float)


def test_fetch_fund_holdings() -> None:
    holdings = fetch_fund_holdings("161725")

    assert 0 < len(holdings) <= 10
    assert sum(item["weight"] for item in holdings) <= 1.0
    for holding in holdings:
        assert {"stock_code", "weight", "report_date"} <= holding.keys()
