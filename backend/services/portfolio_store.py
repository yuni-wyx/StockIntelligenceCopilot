from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

try:
    from ..schemas.portfolio import (
        InvestorHistoryEntry,
        InvestorMemorySnapshot,
        InvestorProfile,
        InvestorProfileUpdate,
        PortfolioRequest,
        SavedPortfolioRecord,
        SavedPortfolioSummary,
    )
except ImportError:
    from schemas.portfolio import (
        InvestorHistoryEntry,
        InvestorMemorySnapshot,
        InvestorProfile,
        InvestorProfileUpdate,
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS investor_profiles (
                    name TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS investor_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    tickers_json TEXT NOT NULL,
                    raw_query TEXT,
                    created_at TEXT NOT NULL
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

    def get_investor_profile(self, name: str = "default") -> InvestorProfile:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json, updated_at FROM investor_profiles WHERE name = ?",
                (name,),
            ).fetchone()
        if row is None:
            return InvestorProfile()
        payload = json.loads(row["payload_json"])
        return InvestorProfile(
            **payload,
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def update_investor_profile(
        self,
        profile: InvestorProfileUpdate,
        *,
        name: str = "default",
    ) -> InvestorProfile:
        updated_at = datetime.now(timezone.utc).isoformat()
        saved = InvestorProfile(
            **profile.model_dump(),
            updated_at=datetime.fromisoformat(updated_at),
        )
        payload_json = InvestorProfile(**profile.model_dump()).model_dump_json(
            exclude={"updated_at"}
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO investor_profiles (name, payload_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (
                    name,
                    payload_json,
                    updated_at,
                ),
            )
            conn.commit()
        return saved

    def record_investor_history(
        self,
        event_type: str,
        tickers: list[str],
        *,
        raw_query: str | None = None,
    ) -> InvestorHistoryEntry:
        created_at = datetime.now(timezone.utc).isoformat()
        entry = InvestorHistoryEntry(
            event_type=event_type,
            tickers=tickers,
            raw_query=raw_query,
            created_at=datetime.fromisoformat(created_at),
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO investor_history (event_type, tickers_json, raw_query, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (event_type, json.dumps(tickers), raw_query, created_at),
            )
            conn.commit()
        return entry

    def list_investor_history(
        self,
        *,
        event_types: set[str] | None = None,
        limit: int = 20,
    ) -> list[InvestorHistoryEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_type, tickers_json, raw_query, created_at
                FROM investor_history
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        entries = [
            InvestorHistoryEntry(
                event_type=row["event_type"],
                tickers=json.loads(row["tickers_json"]),
                raw_query=row["raw_query"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]
        if event_types is None:
            return entries
        return [entry for entry in entries if entry.event_type in event_types]

    def get_investor_memory_snapshot(self) -> InvestorMemorySnapshot:
        return InvestorMemorySnapshot(
            profile=self.get_investor_profile(),
            watchlist_history=self.list_investor_history(
                event_types={"watchlist"},
                limit=10,
            ),
            prior_research_history=self.list_investor_history(
                event_types={"research", "explain", "trade"},
                limit=10,
            ),
        )
