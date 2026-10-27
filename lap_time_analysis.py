from database import get_connection


def fastest_laps(limit=20):
    """Find the fastest recorded laps in the 2024 season."""

    with get_connection() as con:
        return con.execute("""
            WITH parsed_laps AS (
                SELECT
                    season,
                    round,
                    lapNumber,
                    driverId,
                    position,
                    time,
                    TRY_CAST(SPLIT_PART(time, ':', 1) AS DOUBLE) * 60
                    + TRY_CAST(SPLIT_PART(time, ':', 2) AS DOUBLE)
                    AS lap_seconds
                FROM lap_times
                WHERE season = 2024
            )
            SELECT
                driverId AS driver,
                round AS race_round,
                lapNumber AS lap,
                time AS lap_time,
                ROUND(lap_seconds, 3) AS lap_seconds
            FROM parsed_laps
            WHERE lap_seconds > 0
            ORDER BY lap_seconds ASC
            LIMIT ?
        """, [limit]).fetchdf()


def main():
    print("=" * 80)
    print("2024 F1 FASTEST LAP-TIME ANALYSIS")
    print("=" * 80)

    results = fastest_laps(20)

    if results.empty:
        print("No valid lap-time records found for 2024.")
    else:
        print(results.to_string(index=False))


if __name__ == "__main__":
    main()