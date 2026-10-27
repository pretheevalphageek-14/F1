# Formula 1 2024 Analytics Dashboard

## 1. Put files in your project folder
Copy `app.py` and `requirements.txt` into:
`X:\AMRITA\DBMS CASE\F1-DuckDB-Case-Study\formula-one-datasets-main`

Make sure `f1_analysis.duckdb` is in the same folder. The app looks for it automatically.

## 2. Install dependencies (PowerShell)
```powershell
python -m pip install -r requirements.txt
```

## 3. Run the dashboard
```powershell
python -m streamlit run app.py
```

Streamlit will print a local address, usually `http://localhost:8501`. Open it in your browser.

## Notes
- This app inspects your DuckDB tables and columns at runtime to handle small schema differences.
- The lap-time table shown in your screenshots stores `time` as text (for example `1:07.694`), so the app parses that format rather than expecting a `milliseconds` column.
- The initial constructor view lists constructor records. A true constructor-points chart needs constructor IDs joined to race results; the app will show the detected schema instead of inventing those totals if the relationship is missing.
- If your database has a different filename, edit `DB_CANDIDATES` near the top of `app.py`.
