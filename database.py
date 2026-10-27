
from pathlib import Path
import duckdb

# Database file is stored in the same folder as this script.
DB_PATH = Path(__file__).resolve().parent / "f1_analysis.duckdb"


def get_connection(read_only=True):
    """Open a connection to the F1 DuckDB database."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    return duckdb.connect(
        str(DB_PATH),
        read_only=read_only
    )


def list_tables():
    """Return the names of all database tables."""
    with get_connection() as con:
        return [
            row[0]
            for row in con.execute("SHOW TABLES").fetchall()
        ]


def main():
    print("=" * 50)
    print("F1 DUCKDB DATABASE INFORMATION")
    print("=" * 50)
    print(f"Database path: {DB_PATH}")

    tables = list_tables()

    print(f"\nTotal tables: {len(tables)}")
    print("\nTable details:")

    with get_connection() as con:
        for table in tables:
            # Quote the table name safely for SQL.
            safe_name = '"' + table.replace('"', '""') + '"'

            count = con.execute(
                f"SELECT COUNT(*) FROM {safe_name}"
            ).fetchone()[0]

            print(f"  {table}: {count:,} rows")


if __name__ == "__main__":
    main()
