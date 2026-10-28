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
    con = connect_db(read_only=False)
    try:
        table = choose_table(con)
        print(f"\nCurrent records from {table} (first 30; use __rowid__ to identify a row):")
        rows = show_rows(con, table)
        if rows.empty:
            return
        try:
            rowid = int(input("\nEnter the __rowid__ of the record to modify: ").strip())
        except ValueError:
            print("Invalid rowid; cancelled.")
            return
        found = con.execute(f"SELECT * FROM {quote_ident(table)} WHERE rowid = ?", [rowid]).fetchdf()
        if found.empty:
            print("No record with that rowid was found; cancelled.")
            return
        print("\nSelected record:")
        print(found.to_string(index=False))
        schema = get_schema(con, table)
        names = [c[0] for c in schema]
        print("\nColumns:")
        for i, col in enumerate(schema, 1):
            print(f"  {i}. {col[0]} ({col[1]})")
        selected = input("Enter column number or exact column name to change: ").strip()
        if selected.isdigit() and 1 <= int(selected) <= len(schema):
            column = schema[int(selected)-1][0]
        elif selected in names:
            column = selected
        else:
            print("Invalid column; cancelled.")
            return
        dtype = next(c[1] for c in schema if c[0] == column)
        new_value = parse_value(input(f"New value for {column} ({dtype}) [blank = NULL]: "), dtype)
        print(f"\nProposed change: rowid {rowid}, {column} = {new_value!r}")
        if input("Type YES to apply this update: ").strip() != "YES":
            print("Cancelled; no changes made.")
            return
        con.execute(f"UPDATE {quote_ident(table)} SET {quote_ident(column)} = ? WHERE rowid = ?", [new_value, rowid])
        print("\nRecord updated successfully.")
        show_rows(con, table)
    except Exception as exc:
        print(f"\nUPDATE failed: {exc}")
        print("Check data types, constraints, and whether the selected row still exists.")
    finally:
        con.close()

if __name__ == "__main__":
    main()
