from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

try:
    from ..schemas.portfolio import (
        PortfolioRequest,
        SavedPortfolioRecord,
        SavedPortfolioSummary,
    )
except ImportError:
    from schemas.portfolio import (
        PortfolioRequest,
        SavedPortfolioRecord,
        SavedPortfolioSummary,
    )


class PortfolioStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        default_path = Path(__file__).resolve().parents[1] / "data" / "portfolio_store.sqlite3"
        self.db_path = Path(db_path or default_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolios (
                    name TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_portfolio(
        self,
        portfolio: PortfolioRequest,
        *,
        name: str = "current",
    ) -> SavedPortfolioRecord:
        updated_at = datetime.now(timezone.utc).isoformat()
        payload_json = portfolio.model_dump_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO portfolios (name, payload_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (name, payload_json, updated_at),
            )
            conn.commit()
        return SavedPortfolioRecord(
            name=name,
            updated_at=datetime.fromisoformat(updated_at),
            portfolio=portfolio,
        )

    def load_portfolio(self, name: str = "current") -> SavedPortfolioRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT name, payload_json, updated_at FROM portfolios WHERE name = ?",
                (name,),
            ).fetchone()
        if row is None:
            return None
        return SavedPortfolioRecord(
            name=row["name"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
            portfolio=PortfolioRequest(**json.loads(row["payload_json"])),
        )

    def update_portfolio(
        self,
        portfolio: PortfolioRequest,
        *,
        name: str = "current",
    ) -> SavedPortfolioRecord:
        return self.save_portfolio(portfolio, name=name)

    def delete_portfolio(self, name: str = "current") -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM portfolios WHERE name = ?", (name,))
            conn.commit()
        return cursor.rowcount > 0

    def list_saved_portfolios(self) -> list[SavedPortfolioSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, payload_json, updated_at FROM portfolios ORDER BY updated_at DESC"
            ).fetchall()
        results: list[SavedPortfolioSummary] = []
        for row in rows:
            payload = PortfolioRequest(**json.loads(row["payload_json"]))
            results.append(
                SavedPortfolioSummary(
                    name=row["name"],
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    holding_count=len(payload.holdings),
                    base_currency=payload.base_currency,
                    risk_profile=payload.risk_profile,
                    goal=payload.goal,
                )
            )
        return results
