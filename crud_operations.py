from __future__ import annotations

import re
from typing import Any, Mapping

import pandas as pd
from database import get_connection


def quote_identifier(identifier: str) -> str:
    """Safely quote a DuckDB table or column identifier."""
    return '"' + str(identifier).replace('"', '""') + '"'


def list_tables() -> list[str]:
    with get_connection() as con:
        return [row[0] for row in con.execute("SHOW TABLES").fetchall()]


def get_schema(table: str) -> pd.DataFrame:
    with get_connection() as con:
        return con.execute(f"DESCRIBE {quote_identifier(table)}").fetchdf()


def read_records(table: str, limit: int | None = None) -> pd.DataFrame:
    sql = f"SELECT * FROM {quote_identifier(table)}"
    if limit is not None:
        sql += f" LIMIT {max(0, int(limit))}"
    with get_connection() as con:
        return con.execute(sql).fetchdf()


def insert_record(table: str, values: Mapping[str, Any]) -> None:
    """Insert provided columns. Omitted columns use database defaults."""
    clean = {str(k): v for k, v in values.items() if v is not None}
    if not clean:
        raise ValueError("Enter at least one non-blank field.")
    columns = ", ".join(quote_identifier(c) for c in clean)
    placeholders = ", ".join("?" for _ in clean)
    with get_connection() as con:
        con.execute(
            f"INSERT INTO {quote_identifier(table)} ({columns}) VALUES ({placeholders})",
            list(clean.values()),
        )


def update_record(table: str, rowid: int, column: str, value: Any) -> None:
    """Update one field of the selected DuckDB row."""
    with get_connection() as con:
        con.execute(
            f"UPDATE {quote_identifier(table)} SET {quote_identifier(column)} = ? WHERE rowid = ?",
            [value, int(rowid)],
        )


def delete_record(table: str, rowid: int) -> None:
    """Delete the selected DuckDB row."""
    with get_connection() as con:
        con.execute(
            f"DELETE FROM {quote_identifier(table)} WHERE rowid = ?",
            [int(rowid)],
        )


def get_records_with_rowid(table: str, limit: int = 5000) -> pd.DataFrame:
    """Return rows with a temporary row handle used by the UI selectors."""
    with get_connection() as con:
        return con.execute(
            f"SELECT rowid AS __rowid__, * FROM {quote_identifier(table)} LIMIT ?",
            [int(limit)],
        ).fetchdf()
