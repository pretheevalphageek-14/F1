
from pathlib import Path
import duckdb

DB_PATH = Path(__file__).parent / "f1_analysis.duckdb"

if not DB_PATH.exists():
    raise FileNotFoundError(f"Database not found: {DB_PATH}")

con = duckdb.connect(str(DB_PATH), read_only=True)

checks = {
    "2024 race count": """
        SELECT COUNT(*) FROM races WHERE season = 2024
    """,
    "Distinct 2024 rounds": """
        SELECT COUNT(DISTINCT round)
        FROM races WHERE season = 2024
    """,
    "2024 race results": """
        SELECT COUNT(*) FROM race_results WHERE season = 2024
    """,
    "Duplicate race-driver results": """
        SELECT COUNT(*) FROM (
            SELECT season, round, driverId
            FROM race_results
            WHERE season = 2024
            GROUP BY season, round, driverId
            HAVING COUNT(*) > 1
        )
    """,
    "Results with missing driver IDs": """
        SELECT COUNT(*)
        FROM race_results
        WHERE season = 2024
          AND (driverId IS NULL OR TRIM(driverId) = '')
    """,
    "2024 lap-time records": """
        SELECT COUNT(*) FROM lap_times WHERE season = 2024
    """,
    "2024 pit-stop records": """
        SELECT COUNT(*) FROM pitstops WHERE season = 2024
    """,
    "Results with missing points": """
        SELECT COUNT(*)
        FROM race_results
        WHERE season = 2024 AND points IS NULL
    """
}

try:
    print("=" * 55)
    print("F1 DATABASE QUALITY REPORT — 2024")
    print("=" * 55)

    for label, query in checks.items():
        value = con.execute(query).fetchone()[0]
        print(f"{label}: {value}")

    print("\nRace calendar:")
    print(
        con.execute("""
            SELECT round, raceName, date
            FROM races
            WHERE season = 2024
            ORDER BY round
        """).fetchdf().to_string(index=False)
    )

    print("\nTop 10 drivers by total Grand Prix points:")
    print(
        con.execute("""
            SELECT
                driverName,
                SUM(points) AS total_points,
                COUNT(*) FILTER (WHERE position = 1) AS wins
            FROM race_results
            WHERE season = 2024
            GROUP BY driverName
            ORDER BY total_points DESC, wins DESC
            LIMIT 10
        """).fetchdf().to_string(index=False)
    )

finally:
    con.close()
