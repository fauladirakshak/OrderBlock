"""Opt-in SQLite cache for licensed historical market candles.

Caching is disabled by default. Enable it only after the provider/venue terms
permit local storage and the configured retention period.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any


def _database_path() -> str:
    return os.getenv("ORDERBLOCK_CACHE_DB", "./data/orderblock-market-cache.sqlite3")


def _connect() -> sqlite3.Connection:
    path = Path(_database_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=10)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS candle_cache (
            cache_key TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            stored_at REAL NOT NULL,
            expires_at REAL NOT NULL
        )
    """)
    connection.execute("CREATE INDEX IF NOT EXISTS idx_candle_cache_expiry ON candle_cache(expires_at)")
    return connection


def cache_enabled() -> bool:
    return os.getenv("ORDERBLOCK_CACHE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def cache_ttl_seconds() -> int:
    try:
        return max(0, int(os.getenv("ORDERBLOCK_CACHE_TTL_SECONDS", "300")))
    except ValueError:
        return 300


def make_cache_key(*, provider: str, venue_id: str, contract_type: str,
                   symbol: str, timeframe: str, limit: int) -> str:
    identity = json.dumps(
        [provider, venue_id, contract_type, symbol, timeframe, limit],
        separators=(",", ":"), ensure_ascii=True,
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def get_cached_payload(cache_key: str, *, now: float | None = None) -> dict[str, Any] | None:
    current = time.time() if now is None else now
    with _connect() as connection:
        row = connection.execute(
            "SELECT payload, expires_at FROM candle_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if row is None:
            return None
        if float(row[1]) <= current:
            connection.execute("DELETE FROM candle_cache WHERE cache_key = ?", (cache_key,))
            return None
        try:
            value = json.loads(row[0])
        except (TypeError, ValueError):
            connection.execute("DELETE FROM candle_cache WHERE cache_key = ?", (cache_key,))
            return None
        return value if isinstance(value, dict) else None


def put_cached_payload(cache_key: str, payload: dict[str, Any], *, ttl_seconds: int,
                       now: float | None = None) -> None:
    if ttl_seconds <= 0:
        return
    current = time.time() if now is None else now
    encoded = json.dumps(payload, separators=(",", ":"), allow_nan=False)
    with _connect() as connection:
        connection.execute(
            """INSERT INTO candle_cache(cache_key, payload, stored_at, expires_at)
               VALUES(?, ?, ?, ?)
               ON CONFLICT(cache_key) DO UPDATE SET
                 payload=excluded.payload, stored_at=excluded.stored_at,
                 expires_at=excluded.expires_at""",
            (cache_key, encoded, current, current + ttl_seconds),
        )
        connection.execute("DELETE FROM candle_cache WHERE expires_at <= ?", (current,))
