from database import get_connection


def race_calendar(season=2024):
    """Display the race calendar for the selected F1 season."""

    query = """
        SELECT
            season,
            round,
            raceName,
            circuitName,
            date
        FROM races
        WHERE season = ?
        ORDER BY round
    """

    with get_connection() as con:
        return con.execute(query, [season]).fetchdf()


def race_results(season=2024):
    """Display race results for the selected F1 season."""

    query = """
        SELECT
            rr.round,
            r.raceName,
            rr.driverId,
            rr.position,
            rr.points,
            rr.grid,
            rr.status
        FROM race_results AS rr
        LEFT JOIN races AS r
            ON rr.season = r.season
            AND rr.round = r.round
        WHERE rr.season = ?
        ORDER BY rr.round, rr.position
    """

    with get_connection() as con:
        return con.execute(query, [season]).fetchdf()


def race_summary(season=2024):
    """Summarize the number of races and results for a season."""

    query = """
        SELECT
            r.season,
            COUNT(DISTINCT r.round) AS total_races,
            COUNT(DISTINCT rr.driverId) AS distinct_drivers,
            SUM(rr.points) AS total_points
        FROM races AS r
        LEFT JOIN race_results AS rr
            ON r.season = rr.season
            AND r.round = rr.round
        WHERE r.season = ?
        GROUP BY r.season
    """

    with get_connection() as con:
        return con.execute(query, [season]).fetchdf()


def main():
    season = 2024

    print("=" * 90)
    print(f"{season} F1 RACE ANALYSIS")
    print("=" * 90)

    # 1. Race calendar
    print("\n1. RACE CALENDAR")
    print("-" * 90)

    calendar = race_calendar(season)

    if calendar.empty:
        print(f"No race calendar records found for {season}.")
    else:
        print(
            calendar[
                ["season", "round", "raceName", "circuitName", "date"]
            ].to_string(index=False)
        )

    # 2. Race summary
    print("\n2. RACE SUMMARY")
    print("-" * 90)

    summary = race_summary(season)

    if summary.empty:
        print(f"No race summary available for {season}.")
    else:
        print(summary.to_string(index=False))

    # 3. Race results
    print("\n3. RACE RESULTS")
    print("-" * 90)

    results = race_results(season)

    if results.empty:
        print(f"No race results found for {season}.")
    else:
        print(results.head(30).to_string(index=False))
        print(f"\nTotal displayed results: {min(len(results), 30)}")
        print(f"Total records retrieved: {len(results)}")


if __name__ == "__main__":
    main()
