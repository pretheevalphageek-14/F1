
from database import get_connection


def constructor_standings():
    """Summarize 2024 Grand Prix performance by constructor."""
    with get_connection() as con:
        return con.execute("""
            SELECT
                constructorName AS constructor,
                ROUND(SUM(points), 1) AS total_points,
                COUNT(*) FILTER (WHERE position = 1) AS wins,
                COUNT(*) FILTER (
                    WHERE position BETWEEN 1 AND 3
                ) AS podium_finishes,
                COUNT(*) AS driver_race_entries
            FROM race_results
            WHERE season = 2024
            GROUP BY constructorName
            ORDER BY total_points DESC, wins DESC
        """).fetchdf()


def main():
    print("=" * 75)
    print("2024 F1 CONSTRUCTOR PERFORMANCE ANALYSIS")
    print("=" * 75)

    results = constructor_standings()
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
