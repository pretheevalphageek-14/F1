from database import get_connection

with get_connection(read_only=False) as con:
    con.execute("""
        INSERT INTO crud_demo
            (record_id, driver_name, team_name, championship_points)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (record_id) DO UPDATE SET
            driver_name = EXCLUDED.driver_name,
            team_name = EXCLUDED.team_name,
            championship_points = EXCLUDED.championship_points
    """, [9003, "Code Driver", "Python Team", 50])

    print("Record inserted or updated successfully.")

    print(
        con.execute("""
            SELECT *
            FROM crud_demo
            WHERE record_id = 9003
        """).fetchdf().to_string(index=False)
    )   