
from database import get_connection


def top_drivers(limit=10):
    """Rank 2024 drivers by Grand Prix points."""
    with get_connection() as con:
        return con.execute("""
            SELECT
                driverName AS driver,
                ROUND(SUM(points), 1) AS total_points,
                COUNT(*) FILTER (WHERE position = 1) AS wins,
                COUNT(*) FILTER (WHERE position BETWEEN 1 AND 3)
                    AS podiums,
                ROUND(AVG(position), 2) AS average_finish
            FROM race_results
            WHERE season = 2024
            GROUP BY driverName
            ORDER BY total_points DESC, wins DESC
            LIMIT ?
        """, [limit]).fetchdf()


def main():
    print("=" * 65)
    print("2024 F1 DRIVER PERFORMANCE ANALYSIS")
    print("=" * 65)

    print("\nTop 10 drivers by Grand Prix points:")
    print(top_drivers(10).to_string(index=False))


if __name__ == "__main__":
    main()
