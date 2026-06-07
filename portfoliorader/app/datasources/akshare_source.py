from __future__ import annotations

import logging
import os
from collections.abc import Callable
from contextlib import contextmanager
from datetime import date
from typing import Any

import akshare as ak


def _to_yyyymmdd(value: str) -> str:
    return value.replace("-", "")


def _to_iso_date(value: Any) -> str:
    return str(value)[:10].replace("/", "-")


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _market_for_stock(stock_code: str) -> str:
    return "sh" if stock_code.startswith(("5", "6", "9")) else "sz"


@contextmanager
def _without_proxy() -> Any:
    proxy_keys = (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    )
    original = {key: os.environ.get(key) for key in proxy_keys}
    for key in proxy_keys:
        os.environ.pop(key, None)
    try:
        yield
    finally:
        for key, value in original.items():
            if value is not None:
                os.environ[key] = value


def _call_with_direct_retry(call: Callable[[], Any], label: str) -> Any:
    try:
        return call()
    except Exception as exc:
        logging.warning("AKShare %s failed, retrying without proxy: %s", label, exc)
        with _without_proxy():
            return call()


def fetch_daily_quote(stock_code: str, start_date: str, end_date: str) -> list[dict]:
    df = _call_with_direct_retry(
        lambda: ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=_to_yyyymmdd(start_date),
            end_date=_to_yyyymmdd(end_date),
            adjust="qfq",
        ),
        "daily quote",
    )
    records: list[dict] = []
    for _, row in df.iterrows():
        records.append(
            {
                "trade_date": _to_iso_date(row.get("日期")),
                "open": _to_float(row.get("开盘")),
                "high": _to_float(row.get("最高")),
                "low": _to_float(row.get("最低")),
                "close": _to_float(row.get("收盘")),
                "volume": _to_float(row.get("成交量")),
            }
        )
    return records


def fetch_money_flow(stock_code: str, date: str) -> dict:
    try:
        df = _call_with_direct_retry(
            lambda: ak.stock_individual_fund_flow(
                stock=stock_code,
                market=_market_for_stock(stock_code),
            ),
            "money flow",
        )
    except Exception as exc:
        logging.warning("AKShare money flow unavailable: %s", exc)
        return {"super_net_in": 0.0}

    if df.empty:
        return {"super_net_in": 0.0}

    flow_columns = [
        "超大单净流入-净额",
        "超大单净流入净额",
        "超大单净额",
    ]
    target_rows = df[df["日期"].astype(str).str[:10] == date]
    if target_rows.empty:
        return {"super_net_in": 0.0}

    row = target_rows.iloc[-1]
    for column in flow_columns:
        if column in row:
            return {"super_net_in": _to_float(row.get(column))}
    return {"super_net_in": 0.0}


def fetch_fund_holdings(fund_code: str) -> list[dict]:
    latest_df = None
    current_year = date.today().year
    for year in range(current_year, current_year - 5, -1):
        try:
            df = _call_with_direct_retry(
                lambda: ak.fund_portfolio_hold_em(symbol=fund_code, date=str(year)),
                "fund holdings",
            )
        except Exception as exc:
            logging.warning("AKShare fund holdings unavailable for %s: %s", year, exc)
            continue
        if not df.empty:
            latest_df = df
            break

    if latest_df is None or latest_df.empty:
        return []

    records: list[dict] = []
    for _, row in latest_df.head(10).iterrows():
        records.append(
            {
                "stock_code": str(row.get("股票代码", "")).zfill(6),
                "weight": _to_float(row.get("占净值比例")) / 100,
                "report_date": str(row.get("季度", "")),
            }
        )
    return records
