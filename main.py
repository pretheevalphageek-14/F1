import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent / "f1_analysis.duckdb"

def main():
    if not DB_PATH.exists():
        print("Database not found:", DB_PATH)
        return

    con = duckdb.connect(str(DB_PATH), read_only=True)

    print("=== F1 RACE PERFORMANCE AND STRATEGY ANALYSIS ===")
    print("Database connected successfully!")

    tables = con.execute("SHOW TABLES").fetchall()
    print("Total tables:", len(tables))

    query = """
        SELECT driverName, COUNT(*) AS wins
        FROM race_results
        WHERE position = 1
        GROUP BY driverName
        ORDER BY wins DESC
        LIMIT 5
    """

    print("\nTop 5 drivers by race wins:")
    print(con.execute(query).df().to_string(index=False))

    con.close()

if __name__ == "__main__":
    main()