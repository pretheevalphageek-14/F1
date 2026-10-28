from database import get_connection


def main():
    # CREATE TABLE
    with get_connection(read_only=False) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS crud_demo (
                record_id INTEGER PRIMARY KEY,
                driver_name VARCHAR NOT NULL,
                team_name VARCHAR,
                championship_points INTEGER
            )
        """)

        print("\n1. TABLE CREATED / VERIFIED")

        # CREATE: Insert a test record if it doesn't exist
        con.execute("""
            INSERT INTO crud_demo
                (record_id, driver_name, team_name, championship_points)
            SELECT 9001, 'Test Driver', 'Test Team', 10
            WHERE NOT EXISTS (
                SELECT 1 FROM crud_demo WHERE record_id = 9001
            )
        """)

        print("\n2. CREATE: Inserted or verified test record")

        # READ: Display the record
        print("\n3. READ: Record after insertion")
        print(
            con.execute("""
                SELECT *
                FROM crud_demo
                WHERE record_id = 9001
            """).fetchdf().to_string(index=False)
        )

        # UPDATE: Change its points
        con.execute("""
            UPDATE crud_demo
            SET championship_points = 25
            WHERE record_id = 9001
        """)

        print("\n4. UPDATE: Record after changing points")
        print(
            con.execute("""
                SELECT *
                FROM crud_demo
                WHERE record_id = 9001
            """).fetchdf().to_string(index=False)
        )

        # DELETE: Remove the test record
        con.execute("""
            DELETE FROM crud_demo
            WHERE record_id = 9001
        """)

        print("\n5. DELETE: Remaining matching records")
        print(
            con.execute("""
                SELECT *
                FROM crud_demo
                WHERE record_id = 9001
            """).fetchdf().to_string(index=False)
        )

    print("\nCRUD DEMONSTRATION COMPLETED")


if __name__ == "__main__":
    main()
