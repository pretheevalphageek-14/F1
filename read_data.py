import duckdb
from database import DB_PATH

def quote_ident(name):
    return '"' + str(name).replace('"', '""') + '"'

def connect_db(read_only=False):
    # Uses the same DB_PATH configured in your existing database.py / Streamlit app.
    return duckdb.connect(database=str(DB_PATH), read_only=read_only)

def choose_table(con):
    tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
    if not tables:
        raise RuntimeError("No tables were found in this database.")
    print("\nExisting tables:")
    for i, name in enumerate(tables, 1):
        print(f"  {i}. {name}")
    while True:
        raw = input("Enter the table number or exact table name: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(tables):
            return tables[int(raw) - 1]
        if raw in tables:
            return raw
        print("Please enter a listed table number or exact table name.")

def get_schema(con, table):
    return con.execute(f"DESCRIBE {quote_ident(table)}").fetchall()

def show_rows(con, table, limit=30):
    df = con.execute(
        f"SELECT rowid AS __rowid__, * FROM {quote_ident(table)} LIMIT ?",
        [limit]
    ).fetchdf()
    if df.empty:
        print("(No records found.)")
    else:
        print(df.to_string(index=False))
    return df

def parse_value(raw, dtype):
    from datetime import date, datetime
    import json
    value = raw.strip()
    if value == "":
        return None
    t = str(dtype).upper()
    if any(x in t for x in ("TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT", "UBIGINT")):
        return int(value)
    if any(x in t for x in ("DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL")):
        return float(value)
    if t.startswith("BOOL"):
        if value.lower() in ("true", "1", "yes", "y"):
            return True
        if value.lower() in ("false", "0", "no", "n"):
            return False
        raise ValueError("Enter true/false for a BOOLEAN column.")
    if t.startswith("DATE"):
        return date.fromisoformat(value)
    if "TIMESTAMP" in t or t.startswith("DATETIME"):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.startswith("JSON"):
        json.loads(value)
    return value

def main():
    con = connect_db(read_only=True)
    try:
        table = choose_table(con)
        print(f"\nSchema for {table}:")
        for col in get_schema(con, table):
            print(f"  {col[0]} ({col[1]})")
        print(f"\nFirst 30 records from {table}:")
        show_rows(con, table)
    finally:
        con.close()

if __name__ == "__main__":
    main()
