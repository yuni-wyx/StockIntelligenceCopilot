from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

try:
    from ..schemas.portfolio import (
        HoldingInput,
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
        HoldingInput,
        InvestorHistoryEntry,
        InvestorMemorySnapshot,
        InvestorProfile,
        InvestorProfileUpdate,
        PortfolioRequest,
        SavedPortfolioRecord,
        SavedPortfolioSummary,
    )

KNOWN_HOLDING_ALIASES: dict[str, tuple[str, str]] = {
    "我有中華": ("2204.TW", "中華"),
    "我持有中華": ("2204.TW", "中華"),
    "目前有中華": ("2204.TW", "中華"),
    "另外有中華": ("2204.TW", "中華"),
    "還有中華": ("2204.TW", "中華"),
    "中華": ("2204.TW", "中華"),
    "2204": ("2204.TW", "中華"),
    "2204.TW": ("2204.TW", "中華"),
    "兆利": ("3548.TW", "兆利"),
    "3548": ("3548.TW", "兆利"),
    "3548.TW": ("3548.TW", "兆利"),
    "00878": ("00878.TW", "國泰永續高股息"),
    "00878.TW": ("00878.TW", "國泰永續高股息"),
}


def _clean_alias(value: str | None) -> str:
    if not value:
        return ""
    cleaned = value.strip()
    for prefix in ("我有", "我持有", "目前有", "另外有", "還有", "以及", "和", "跟", "加上"):
        if cleaned.startswith(prefix):
            cleaned = cleaned.removeprefix(prefix).strip()
            break
    return cleaned


def _normalize_known_holding(holding: HoldingInput) -> tuple[HoldingInput, bool]:
    candidates = [
        holding.ticker,
        holding.name,
        _clean_alias(holding.ticker),
        _clean_alias(holding.name),
    ]
    mapping: tuple[str, str] | None = None
    for candidate in candidates:
        if not candidate:
            continue
        mapping = KNOWN_HOLDING_ALIASES.get(candidate.strip())
        if mapping is not None:
            break

    if mapping is None:
        return holding, False

    ticker, display_name = mapping
    changed = holding.ticker != ticker or holding.name != display_name
    if not changed:
        return holding, False

    prior_label = holding.name or holding.ticker
    note = f"Normalized from saved workspace alias '{prior_label}'."
    notes = holding.notes
    if notes:
        if note not in notes:
            notes = f"{notes} {note}"
    else:
        notes = note
    return holding.model_copy(
        update={
            "ticker": ticker,
            "name": display_name,
            "notes": notes,
        }
    ), True


def normalize_saved_portfolio(portfolio: PortfolioRequest) -> tuple[PortfolioRequest, bool]:
    normalized_holdings: list[HoldingInput] = []
    changed = False
    for holding in portfolio.holdings:
        normalized, holding_changed = _normalize_known_holding(holding)
        normalized_holdings.append(normalized)
        changed = changed or holding_changed
    if not changed:
        return portfolio, False
    return portfolio.model_copy(update={"holdings": normalized_holdings}), True


class PortfolioStore:
    LOCAL_USER_ID = "local-demo"

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
                    user_id TEXT NOT NULL DEFAULT 'local-demo',
                    portfolio_id TEXT NOT NULL DEFAULT 'current',
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(portfolios)").fetchall()
            }
            if "version" not in columns:
                conn.execute(
                    "ALTER TABLE portfolios ADD COLUMN version INTEGER NOT NULL DEFAULT 1"
                )
            if "user_id" not in columns:
                conn.execute(
                    "ALTER TABLE portfolios ADD COLUMN user_id TEXT NOT NULL DEFAULT 'local-demo'"
                )
            if "portfolio_id" not in columns:
                conn.execute(
                    "ALTER TABLE portfolios ADD COLUMN portfolio_id TEXT NOT NULL DEFAULT 'current'"
                )
            # Older named workspaces were migrated with the safe singleton
            # default above; preserve their identity for the future composite
            # user/workspace key.
            conn.execute(
                "UPDATE portfolios SET portfolio_id = name "
                "WHERE portfolio_id = 'current' AND name <> 'current'"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_portfolios_user_portfolio "
                "ON portfolios (user_id, portfolio_id)"
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
        portfolio, _ = normalize_saved_portfolio(portfolio)
        updated_at = datetime.now(timezone.utc).isoformat()
        payload_json = portfolio.model_dump_json()
        with self._connect() as conn:
            prior = conn.execute(
                "SELECT payload_json, version FROM portfolios WHERE name = ?",
                (name,),
            ).fetchone()
            version = int(prior["version"] or 1) if prior else 1
            if prior and prior["payload_json"] != payload_json:
                version += 1
            conn.execute(
                """
                INSERT INTO portfolios (
                    name, user_id, portfolio_id, payload_json, updated_at, version
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    user_id=excluded.user_id,
                    portfolio_id=excluded.portfolio_id,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at,
                    version=excluded.version
                """,
                (name, self.LOCAL_USER_ID, name, payload_json, updated_at, version),
            )
            conn.commit()
        return SavedPortfolioRecord(
            name=name,
            user_id=self.LOCAL_USER_ID,
            portfolio_id=name,
            updated_at=datetime.fromisoformat(updated_at),
            version=version,
            portfolio=portfolio,
        )

    def load_portfolio(self, name: str = "current") -> SavedPortfolioRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT name, user_id, portfolio_id, payload_json, updated_at, version "
                "FROM portfolios WHERE name = ?",
                (name,),
            ).fetchone()
        if row is None:
            return None
        portfolio, changed = normalize_saved_portfolio(
            PortfolioRequest(**json.loads(row["payload_json"]))
        )
        if changed:
            self.save_portfolio(portfolio, name=row["name"])
            return self.load_portfolio(name)
        return SavedPortfolioRecord(
            name=row["name"],
            user_id=row["user_id"] or self.LOCAL_USER_ID,
            portfolio_id=row["portfolio_id"] or row["name"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
            version=int(row["version"] or 1),
            portfolio=portfolio,
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
                "SELECT name, user_id, portfolio_id, payload_json, updated_at, version "
                "FROM portfolios ORDER BY updated_at DESC"
            ).fetchall()
        results: list[SavedPortfolioSummary] = []
        for row in rows:
            payload, _ = normalize_saved_portfolio(
                PortfolioRequest(**json.loads(row["payload_json"]))
            )
            results.append(
                SavedPortfolioSummary(
                    name=row["name"],
                    user_id=row["user_id"] or self.LOCAL_USER_ID,
                    portfolio_id=row["portfolio_id"] or row["name"],
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    version=int(row["version"] or 1),
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
