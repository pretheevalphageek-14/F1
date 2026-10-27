from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from database import DB_PATH, get_connection

# ============================================================
# F1 PADDOCK | Formula One dashboard + database CRUD
# ============================================================
st.set_page_config(
    page_title="F1 Paddock | F1 Dashboard",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
      --bg:#111216; --panel:#191b21; --panel2:#20232a; --line:#383b44;
      --red:#ff354d; --teal:#00d6bd; --blue:#273cff; --muted:#a6a9b4;
    }
    .stApp { background: radial-gradient(circle at 10% 0%, #24171d 0, #111216 40%); }
    [data-testid="stSidebar"] { background:#17191f; border-right:1px solid var(--line); }
    .block-container { padding-top:1.35rem; padding-bottom:3rem; max-width:1600px; }
    .hero { background:linear-gradient(115deg,#00cdb6 0%,#00bcae 60%,#078e91 100%);
      border-radius:22px; padding:27px 30px; color:#071b1c; min-height:180px; }
    .hero-kicker { font-size:.78rem; text-transform:uppercase; letter-spacing:2px; font-weight:800; }
    .hero-title { font-size:2.45rem; font-weight:950; line-height:1.05; letter-spacing:-1.5px; }
    .hero-sub { font-size:.95rem; margin-top:10px; opacity:.9; }
    .eyebrow { color:var(--muted); font-size:.72rem; letter-spacing:1.8px; text-transform:uppercase; font-weight:800; }
    .panel { background:linear-gradient(145deg,#1c1e25,#15171c); border:1px solid var(--line);
      border-radius:17px; padding:18px 20px; }
    .kpi { background:linear-gradient(145deg,#20232b,#17191f); border:1px solid var(--line);
      border-radius:15px; padding:17px 18px; min-height:106px; }
    .kpi-label { color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:1.4px; }
    .kpi-value { font-size:1.8rem; font-weight:900; margin-top:8px; line-height:1.1; }
    .kpi-note { color:var(--teal); font-size:.78rem; margin-top:5px; }
    .section-title { font-size:1.05rem; font-weight:850; letter-spacing:.5px; margin:.4rem 0 .7rem; }
    .small-muted { color:var(--muted); font-size:.85rem; }
    .stTabs [data-baseweb="tab-list"] { gap:7px; }
    .stTabs [data-baseweb="tab"] { background:#1a1c22; border-radius:9px 9px 0 0; padding:10px 15px; }
    div[data-testid="stMetric"] { background:#1b1d24; border:1px solid var(--line); padding:12px; border-radius:13px; }
    div[data-testid="stDataFrame"] { border:1px solid #343741; border-radius:12px; overflow:hidden; }
    hr { border-color:var(--line); }
    .tag { display:inline-block; border:1px solid #4a4e59; border-radius:99px; padding:4px 9px; color:#d6d8df; font-size:.72rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------ Helpers ------------------------------
def qident(identifier: str) -> str:
    """Quote a DuckDB identifier safely."""
    return '"' + str(identifier).replace('"', '""') + '"'


def safe_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def get_tables() -> list[str]:
    with get_connection() as con:
        return [row[0] for row in con.execute("SHOW TABLES").fetchall()]


@st.cache_data(ttl=30, show_spinner=False)
def load_table(table_name: str) -> pd.DataFrame:
    with get_connection() as con:
        return con.execute(f"SELECT * FROM {qident(table_name)}").fetchdf()


@st.cache_data(ttl=30, show_spinner=False)
def get_table_info(table_name: str) -> pd.DataFrame:
    with get_connection() as con:
        return con.execute(f"DESCRIBE {qident(table_name)}").fetchdf()


def invalidate_data() -> None:
    load_table.clear()
    get_table_info.clear()


def first_col(df: pd.DataFrame, *names: str) -> str | None:
    lookup = {str(c).lower(): c for c in df.columns}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def numeric_series(df: pd.DataFrame, name: str | None) -> pd.Series:
    if name and name in df.columns:
        return pd.to_numeric(df[name], errors="coerce")
    return pd.Series(dtype="float64")


def display_driver_table(drivers: pd.DataFrame) -> pd.DataFrame:
    if drivers.empty:
        return drivers.copy()
    result = drivers.copy()
    direct = first_col(result, "driverName", "driver_name", "name")
    first = first_col(result, "forename", "firstName", "first_name")
    last = first_col(result, "surname", "lastName", "last_name")
    ref = first_col(result, "driverRef", "driverId", "driver_id")
    if direct:
        result["_driver_label"] = result[direct].astype(str)
    elif first and last:
        result["_driver_label"] = result[first].fillna("").astype(str) + " " + result[last].fillna("").astype(str)
    else:
        result["_driver_label"] = result[ref].astype(str) if ref else "Unknown"
    return result


def metric_card(label: str, value: Any, note: str = "") -> None:
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


def to_python_value(raw: str, dtype: str) -> Any:
    """Convert a form value using DuckDB's reported type; blank means NULL."""
    if raw is None or not str(raw).strip():
        return None
    value = str(raw).strip()
    t = dtype.upper()
    if any(x in t for x in ("TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT", "UBIGINT")):
        return int(value)
    if any(x in t for x in ("DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL")):
        return float(value)
    if t == "BOOLEAN" or t.startswith("BOOL"):
        if value.lower() in {"true", "1", "yes", "y"}:
            return True
        if value.lower() in {"false", "0", "no", "n"}:
            return False
        raise ValueError("Enter true/false for a BOOLEAN column.")
    if t.startswith("DATE"):
        return date.fromisoformat(value)
    if "TIMESTAMP" in t or t.startswith("DATETIME"):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.startswith("JSON"):
        json.loads(value)
        return value
    return value


def query_is_read_only(sql: str) -> bool:
    """Allow query exploration without permitting mutations in SQL Lab."""
    cleaned = re.sub(r"/\*.*?\*/|--[^\n]*", "", sql, flags=re.S).strip()
    if not cleaned:
        return False
    # One statement only; SELECT/WITH/EXPLAIN/SHOW/DESCRIBE/PRAGMA are allowed.
    if ";" in cleaned.rstrip(";"):
        return False
    first = cleaned.split(None, 1)[0].upper()
    return first in {"SELECT", "WITH", "EXPLAIN", "SHOW", "DESCRIBE", "PRAGMA"}


def run_read_query(sql: str) -> pd.DataFrame:
    with get_connection() as con:
        return con.execute(sql).fetchdf()


# ------------------------------ Connection ------------------------------
try:
    table_names = get_tables()
except Exception as exc:
    st.error("Could not connect to your DuckDB database.")
    st.write("Check that `database.py` and the database file are in the same project folder.")
    st.code(str(getattr(__import__("database"), "DB_PATH", "database path unavailable")))
    st.exception(exc)
    st.stop()

if not table_names:
    st.error("The DuckDB database opened, but it contains no tables.")
    st.stop()

# Flexible table discovery: supports the schema in this project and common variants.
tables_lower = {t.lower(): t for t in table_names}
def table_named(*names: str) -> pd.DataFrame:
    for name in names:
        actual = tables_lower.get(name.lower())
        if actual:
            try:
                return load_table(actual).copy()
            except Exception:
                pass
    return pd.DataFrame()

results_raw = table_named("race_results", "results")
races = table_named("races", "race")
drivers_raw = table_named("drivers", "driver")
constructors = table_named("constructors", "constructor")
laps = table_named("lap_times", "laptimes")
pitstops = table_named("pitstops", "pit_stops")
drivers = display_driver_table(drivers_raw)

# Normalize race-result data into a dashboard-friendly view.
results = results_raw.copy()
season_col = first_col(results, "season", "year")
round_col = first_col(results, "round", "race_round", "roundNumber")
driver_id_col = first_col(results, "driverId", "driver_id")
constructor_id_col = first_col(results, "constructorId", "constructor_id")
points_col = first_col(results, "points", "total_points")
position_col = first_col(results, "position", "final_position")
status_col = first_col(results, "status", "resultStatus")
grid_col = first_col(results, "grid", "grid_position", "starting_grid")
race_name_col = first_col(results, "raceName", "race_name", "name")

if not results.empty:
    if season_col and season_col != "season":
        results["season"] = results[season_col]
    elif not season_col:
        results["season"] = 2024
    if round_col and round_col != "round":
        results["round"] = results[round_col]
    if points_col and points_col != "points":
        results["points"] = results[points_col]
    if position_col and position_col != "position":
        results["position"] = results[position_col]
    if grid_col and grid_col != "grid":
        results["grid"] = results[grid_col]
    if status_col and status_col != "status":
        results["status"] = results[status_col]

    # Add race names by joining on season + round when possible.
    race_season_col = first_col(races, "season", "year")
    race_round_col = first_col(races, "round", "race_round", "roundNumber")
    race_name_meta_col = first_col(races, "raceName", "race_name", "name")
    if not races.empty and race_round_col and race_name_meta_col and "round" in results.columns:
        meta_cols = [race_round_col, race_name_meta_col]
        join_keys = ["round"]
        meta = races[meta_cols + ([race_season_col] if race_season_col else [])].copy()
        rename_meta = {race_round_col: "round", race_name_meta_col: "race_name"}
        if race_season_col:
            rename_meta[race_season_col] = "season"
            if "season" in results.columns:
                join_keys.append("season")
        meta = meta.rename(columns=rename_meta).drop_duplicates(join_keys)
        results = results.merge(meta, on=join_keys, how="left", suffixes=("", "_meta"))
    if "race_name" not in results.columns:
        results["race_name"] = results[race_name_col] if race_name_col else "Race"
    if "race_name_meta" in results.columns:
        results["race_name"] = results["race_name"].fillna(results["race_name_meta"])
    results["race_name"] = results["race_name"].fillna("Unknown race").astype(str)

    # Attach display names for drivers.
    if not drivers.empty and driver_id_col:
        d_id = first_col(drivers, "driverId", "driver_id")
        if d_id and "_driver_label" in drivers.columns:
            driver_map = drivers[[d_id, "_driver_label"]].drop_duplicates(d_id).rename(
                columns={d_id: "_driver_join_id", "_driver_label": "driver_name"}
            )
            results = results.merge(driver_map, left_on=driver_id_col, right_on="_driver_join_id", how="left")
    if "driver_name" not in results.columns:
        results["driver_name"] = results[driver_id_col].astype(str) if driver_id_col else "Unknown driver"
    if driver_id_col:
        results["driver_name"] = results["driver_name"].fillna(results[driver_id_col].astype(str))
    results["driver_name"] = results["driver_name"].fillna("Unknown driver")

    # Attach constructor names where available.
    if not constructors.empty and constructor_id_col:
        c_id = first_col(constructors, "constructorId", "constructor_id")
        c_name = first_col(constructors, "constructorName", "constructor_name", "name")
        if c_id and c_name:
            c_map = constructors[[c_id, c_name]].drop_duplicates(c_id).rename(
                columns={c_id: "_constructor_join_id", c_name: "constructor_name"}
            )
            results = results.merge(c_map, left_on=constructor_id_col, right_on="_constructor_join_id", how="left")
    if "constructor_name" not in results.columns:
        results["constructor_name"] = results[constructor_id_col].astype(str) if constructor_id_col else "Unknown team"
    if constructor_id_col:
        results["constructor_name"] = results["constructor_name"].fillna(results[constructor_id_col].astype(str))

# ------------------------------ Sidebar ------------------------------
st.sidebar.markdown("## 🏁 PADDOCK CONTROL")
st.sidebar.caption("DuckDB · F1 race intelligence")
st.sidebar.markdown(f'<span class="tag">{len(table_names)} tables connected</span>', unsafe_allow_html=True)
if st.sidebar.button("↻ Refresh data", use_container_width=True):
    invalidate_data()
    st.rerun()

if not results.empty:
    seasons_available = sorted(pd.to_numeric(results["season"], errors="coerce").dropna().astype(int).unique().tolist())
else:
    seasons_available = []
if not seasons_available:
    seasons_available = [2024]
default_season = 2024 if 2024 in seasons_available else seasons_available[-1]
season = st.sidebar.selectbox("Season", seasons_available, index=seasons_available.index(default_season))
st.sidebar.markdown("---")
st.sidebar.caption("Database file")
st.sidebar.code(str(DB_PATH), language=None)
st.sidebar.caption("CRUD changes write directly to your local DuckDB file. Back up the database before editing.")

# Season-filtered views
if not results.empty:
    all_season_results = results[pd.to_numeric(results["season"], errors="coerce") == season].copy()
else:
    all_season_results = pd.DataFrame()
all_season_laps = laps.copy()
lap_season_col = first_col(all_season_laps, "season", "year")
if lap_season_col:
    all_season_laps = all_season_laps[pd.to_numeric(all_season_laps[lap_season_col], errors="coerce") == season]

# ------------------------------ Header ------------------------------
header_left, header_right = st.columns([4, 1])
with header_left:
    st.markdown(
        '<div class="hero"><div class="hero-kicker">Formula One · Data intelligence</div>'
        '<div class="hero-title">THE PADDOCK</div>'
        '<div class="hero-sub">Formula One analytics and complete database management.</div></div>',
        unsafe_allow_html=True,
    )
with header_right:
    st.markdown('<div class="panel" style="height:100%;text-align:center;padding-top:28px;">'
                '<div class="eyebrow">Season focus</div>'
                f'<div style="font-size:2.3rem;font-weight:950;color:#00d6bd">{season}</div>'
                '<div class="small-muted">DuckDB powered</div></div>', unsafe_allow_html=True)
st.write("")

race_count = all_season_results["race_name"].nunique() if not all_season_results.empty else 0
driver_count = all_season_results["driver_name"].nunique() if not all_season_results.empty else 0
points_total = numeric_series(all_season_results, "points").sum() if not all_season_results.empty else 0
lap_count = len(all_season_laps)

m1, m2, m3, m4 = st.columns(4)
with m1: metric_card("Grands Prix", f"{race_count:,}", "Selected season")
with m2: metric_card("Drivers", f"{driver_count:,}", "Drivers with result records")
with m3: metric_card("Championship points", f"{points_total:,.1f}", "Points awarded in selected season")
with m4: metric_card("Lap records", f"{lap_count:,}", "Timing rows available")

# ============================================================
# Main navigation
# ============================================================
overview_tab, standings_tab, race_tab, timing_tab, studio_tab, sql_tab = st.tabs([
    "🏎️ Dashboard", "🏆 Standings", "📅 Race explorer", "⏱️ Lap & pit analysis",
    "🛠️ Database CRUD", "⌨️ SQL & Indexes"
])

with overview_tab:
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown('<div class="section-title">DRIVER CHAMPIONSHIP</div>', unsafe_allow_html=True)
        if not all_season_results.empty and "points" in all_season_results.columns:
            board = all_season_results.groupby("driver_name", as_index=False).agg(
                Points=("points", lambda x: pd.to_numeric(x, errors="coerce").sum()),
                Entries=("driver_name", "count"),
            ).sort_values("Points", ascending=False).head(10)
            st.bar_chart(board.set_index("driver_name")[["Points"]], height=300)
            st.dataframe(board.rename(columns={"driver_name":"Driver"}), hide_index=True, use_container_width=True)
        else:
            st.info("Race result or points data is unavailable.")
    with right:
        st.markdown('<div class="section-title">LATEST RACE RESULTS</div>', unsafe_allow_html=True)
        recent = all_season_results.copy()
        if "round" in recent.columns:
            recent["_round_sort"] = pd.to_numeric(recent["round"], errors="coerce")
            recent = recent.sort_values("_round_sort", ascending=False)
        wanted = [c for c in ["round", "race_name", "driver_name", "position", "points", "status"] if c in recent.columns]
        st.dataframe(recent[wanted].head(15).rename(columns={
            "round":"Round", "race_name":"Grand Prix", "driver_name":"Driver",
            "position":"Pos", "points":"Pts", "status":"Status"
        }), hide_index=True, use_container_width=True, height=370)
    st.markdown('<div class="section-title">SEASON CALENDAR</div>', unsafe_allow_html=True)
    if not races.empty:
        cal = races.copy()
        s_col = first_col(cal, "season", "year")
        if s_col:
            cal = cal[pd.to_numeric(cal[s_col], errors="coerce") == season]
        r_col = first_col(cal, "round", "race_round", "roundNumber")
        n_col = first_col(cal, "raceName", "race_name", "name")
        d_col = first_col(cal, "date", "raceDate")
        c_col = first_col(cal, "circuitName", "circuit_name")
        cols = [c for c in [r_col, n_col, d_col, c_col] if c]
        if cols:
            cal = cal[cols].copy()
            cal.columns = ["Round" if c == r_col else "Grand Prix" if c == n_col else "Date" if c == d_col else "Circuit" for c in cols]
            if "Round" in cal:
                cal = cal.sort_values("Round")
            st.dataframe(cal, hide_index=True, use_container_width=True)
    else:
        st.info("No races table was found.")

with standings_tab:
    st.markdown('<div class="section-title">DRIVER STANDINGS</div>', unsafe_allow_html=True)
    if not all_season_results.empty and "points" in all_season_results.columns:
        board = all_season_results.groupby("driver_name", as_index=False).agg(
            Points=("points", lambda x: pd.to_numeric(x, errors="coerce").sum()),
            Entries=("driver_name", "count"),
        )
        if "position" in all_season_results.columns:
            wins = all_season_results[pd.to_numeric(all_season_results["position"], errors="coerce") == 1].groupby("driver_name").size().rename("Wins")
            board = board.merge(wins, left_on="driver_name", right_index=True, how="left")
        else:
            board["Wins"] = 0
        board["Wins"] = board["Wins"].fillna(0).astype(int)
        board = board.sort_values(["Points", "Wins"], ascending=False).reset_index(drop=True)
        board.insert(0, "Rank", range(1, len(board) + 1))
        st.dataframe(board.rename(columns={"driver_name":"Driver"}), hide_index=True, use_container_width=True)
        st.bar_chart(board.set_index("driver_name")[["Points", "Wins"]], height=300)
    else:
        st.info("No race results are available.")
    st.markdown('<div class="section-title">CONSTRUCTOR STANDINGS</div>', unsafe_allow_html=True)
    if not all_season_results.empty and "points" in all_season_results.columns and "constructor_name" in all_season_results.columns:
        teams = all_season_results.groupby("constructor_name", as_index=False).agg(
            Points=("points", lambda x: pd.to_numeric(x, errors="coerce").sum())
        ).sort_values("Points", ascending=False)
        teams.insert(0, "Rank", range(1, len(teams) + 1))
        st.dataframe(teams.rename(columns={"constructor_name":"Constructor"}), hide_index=True, use_container_width=True)
        st.bar_chart(teams.set_index("constructor_name")[["Points"]], height=280)
    else:
        st.info("Constructor names or points are not available in the current schema.")

with race_tab:
    st.markdown('<div class="section-title">RACE RESULT EXPLORER</div>', unsafe_allow_html=True)
    if not all_season_results.empty:
        race_names = sorted(all_season_results["race_name"].dropna().astype(str).unique().tolist())
        chosen_race = st.selectbox("Select a Grand Prix", race_names, key="race_select")
        one_race = all_season_results[all_season_results["race_name"].astype(str) == chosen_race].copy()
        if "position" in one_race.columns:
            one_race["_position_sort"] = pd.to_numeric(one_race["position"], errors="coerce")
            one_race = one_race.sort_values("_position_sort", na_position="last")
        shown = [c for c in ["position", "driver_name", "constructor_name", "grid", "points", "status"] if c in one_race.columns]
        st.dataframe(one_race[shown].rename(columns={
            "position":"Position", "driver_name":"Driver", "constructor_name":"Constructor",
            "grid":"Grid", "points":"Points", "status":"Status"
        }), hide_index=True, use_container_width=True)
        if "grid" in one_race.columns and "position" in one_race.columns:
            chart = one_race[["driver_name", "grid", "position"]].copy()
            chart["Grid"] = pd.to_numeric(chart["grid"], errors="coerce")
            chart["Finish"] = pd.to_numeric(chart["position"], errors="coerce")
            chart = chart.dropna(subset=["Grid", "Finish"]).set_index("driver_name")[["Grid", "Finish"]]
            if not chart.empty:
                st.markdown("**Starting grid vs finishing position**")
                st.bar_chart(chart, height=300)
    else:
        st.info("Race results are unavailable.")

with timing_tab:
    lap_left, lap_right = st.columns([1.2, 1])
    with lap_left:
        st.markdown('<div class="section-title">FASTEST RECORDED LAPS</div>', unsafe_allow_html=True)
        if not all_season_laps.empty:
            ms_col = first_col(all_season_laps, "milliseconds", "lapMilliseconds", "lap_time_ms")
            time_col = first_col(all_season_laps, "time", "lap_time", "lapTime")
            lap_no_col = first_col(all_season_laps, "lapNumber", "lap", "lap_number")
            lap_driver_col = first_col(all_season_laps, "driverId", "driver_id")
            lap_round_col = first_col(all_season_laps, "round", "race_round")
            valid = all_season_laps.copy()
            if ms_col:
                valid["_seconds"] = pd.to_numeric(valid[ms_col], errors="coerce") / 1000
                valid = valid[(valid["_seconds"] > 0) & (valid["_seconds"] < 1000)].sort_values("_seconds").head(25)
                valid["Lap seconds"] = valid["_seconds"].round(3)
            elif time_col:
                valid["Lap time"] = valid[time_col].astype(str)
                valid = valid.head(25)
            else:
                valid = pd.DataFrame()
            if not valid.empty and lap_driver_col and not drivers.empty:
                d_id = first_col(drivers, "driverId", "driver_id")
                if d_id:
                    valid = valid.merge(drivers[[d_id, "_driver_label"]].drop_duplicates(d_id),
                                        left_on=lap_driver_col, right_on=d_id, how="left")
            if not valid.empty:
                valid["Driver"] = valid["_driver_label"] if "_driver_label" in valid.columns else (
                    valid[lap_driver_col].astype(str) if lap_driver_col else "Unknown"
                )
                if lap_round_col and not races.empty:
                    r_round = first_col(races, "round", "race_round", "roundNumber")
                    r_name = first_col(races, "raceName", "race_name", "name")
                    if r_round and r_name:
                        race_map = races[[r_round, r_name]].drop_duplicates(r_round).rename(
                            columns={r_round: lap_round_col, r_name:"Grand Prix"}
                        )
                        valid = valid.merge(race_map, on=lap_round_col, how="left")
                view_cols = [c for c in ["Driver", "Grand Prix", lap_round_col, lap_no_col, "Lap seconds", "Lap time"] if c and c in valid.columns]
                st.dataframe(valid[view_cols].rename(columns={lap_round_col:"Round", lap_no_col:"Lap"}),
                             hide_index=True, use_container_width=True, height=430)
            else:
                st.info("Lap table is present, but no usable timing column was detected.")
        else:
            st.info("No lap-time records were found.")
    with lap_right:
        st.markdown('<div class="section-title">PIT-STOP ANALYSIS</div>', unsafe_allow_html=True)
        if not pitstops.empty:
            pit = pitstops.copy()
            ps = first_col(pit, "season", "year")
            if ps:
                pit = pit[pd.to_numeric(pit[ps], errors="coerce") == season]
            duration_col = first_col(pit, "milliseconds", "duration_ms", "duration")
            if duration_col:
                raw_duration = pd.to_numeric(pit[duration_col], errors="coerce")
                pit["Duration seconds"] = (raw_duration / 1000 if duration_col.lower() in {"milliseconds", "duration_ms"} else raw_duration).round(3)
                p1, p2 = st.columns(2)
                p1.metric("Pit-stop records", f"{len(pit):,}")
                p2.metric("Average duration", f"{pit['Duration seconds'].replace(0, pd.NA).dropna().mean():.2f} s" if pit["Duration seconds"].replace(0, pd.NA).dropna().size else "—")
                st.dataframe(pit.sort_values("Duration seconds").head(15), hide_index=True, use_container_width=True)
            else:
                st.caption(f"{len(pit):,} pit-stop rows available.")
                st.dataframe(pit.head(15), hide_index=True, use_container_width=True)
        else:
            st.info("No pitstops table was found.")

# ============================================================
# Database Studio — live CRUD operations against DuckDB
# ============================================================
with studio_tab:
    st.markdown('<div class="section-title">DATABASE STUDIO · CREATE, READ, UPDATE, DELETE</div>', unsafe_allow_html=True)
    st.warning("These operations change the actual local database. Make a backup copy of the .duckdb file before modifying or deleting records.")
    crud_table = st.selectbox("Choose table to manage", table_names, key="crud_table")
    try:
        schema = get_table_info(crud_table)
        current = load_table(crud_table)
    except Exception as exc:
        st.error(f"Could not inspect this table: {safe_error(exc)}")
        schema, current = pd.DataFrame(), pd.DataFrame()

    if not schema.empty:
        schema_cols = list(schema["column_name"])
        dtype_by_col = dict(zip(schema["column_name"], schema["column_type"]))
        st.caption(f"Table `{crud_table}` · {len(current):,} rows · {len(schema_cols)} columns")
        with st.expander("View schema / column types", expanded=False):
            st.dataframe(schema, hide_index=True, use_container_width=True)
        read_tab, create_tab, update_tab, delete_tab = st.tabs(["📋 Read / Search", "➕ Add record", "✏️ Modify record", "🗑️ Delete record"])

        with read_tab:
            search = st.text_input("Search within this table", key="crud_search", placeholder="Search any column value…")
            view = current.copy()
            if search.strip() and not view.empty:
                mask = view.astype(str).apply(lambda s: s.str.contains(search.strip(), case=False, na=False, regex=False)).any(axis=1)
                view = view[mask]
            page_size = st.selectbox("Rows to show", [25, 50, 100, 250, 1000], index=2, key="crud_page_size")
            st.dataframe(view.head(page_size), hide_index=True, use_container_width=True, height=400)
            st.download_button(
                "⬇️ Export table / filtered rows to CSV",
                data=view.to_csv(index=False).encode("utf-8"),
                file_name=f"{crud_table}_export.csv",
                mime="text/csv",
                key="crud_export",
            )

        with create_tab:
            st.caption("Leave a field blank to store NULL. Required columns may reject NULL depending on the table constraints.")
            with st.form("insert_record_form", clear_on_submit=True):
                form_values = {}
                form_cols = st.columns(3)
                for i, column in enumerate(schema_cols):
                    dtype = str(dtype_by_col[column])
                    with form_cols[i % 3]:
                        form_values[column] = st.text_input(
                            f"{column} · {dtype}",
                            key=f"insert_{crud_table}_{column}",
                            placeholder="NULL / leave blank" if "NOT NULL" not in str(schema.iloc[i].get("null", "")) else "Required value",
                        )
                submitted = st.form_submit_button("➕ Insert record", type="primary", use_container_width=True)
            if submitted:
                try:
                    parsed = {c: to_python_value(form_values[c], str(dtype_by_col[c])) for c in schema_cols}
                    non_null = {c: v for c, v in parsed.items() if v is not None}
                    if not non_null:
                        st.error("Enter at least one value before inserting a record.")
                    else:
                        columns_sql = ", ".join(qident(c) for c in non_null)
                        placeholders = ", ".join(["?"] * len(non_null))
                        values = list(non_null.values())
                        with get_connection(read_only=False) as con:
                            con.execute(
                                f"INSERT INTO {qident(crud_table)} ({columns_sql}) VALUES ({placeholders})",
                                values,
                            )
                        invalidate_data()
                        st.success("Record inserted successfully.")
                        st.rerun()
                except Exception as exc:
                    st.error(f"Insert failed: {safe_error(exc)}")

        # Record selector uses DuckDB's rowid as a practical row handle for these local dataset tables.
        with update_tab:
            if current.empty:
                st.info("This table is empty; add a record first.")
            else:
                try:
                    with get_connection() as con:
                        record_frame = con.execute(f"SELECT rowid AS __rowid__, * FROM {qident(crud_table)} LIMIT 5000").fetchdf()
                    def record_label(row: pd.Series) -> str:
                        parts = []
                        for c in schema_cols[:4]:
                            val = row.get(c)
                            parts.append(f"{c}={val}")
                        return f"rowid {row['__rowid__']} · " + " | ".join(parts)
                    row_options = record_frame["__rowid__"].tolist()
                    selected_rowid = st.selectbox(
                        "Select record to modify",
                        row_options,
                        format_func=lambda rid: record_label(record_frame.loc[record_frame["__rowid__"] == rid].iloc[0]),
                        key=f"update_row_{crud_table}",
                    )
                    selected_record = record_frame[record_frame["__rowid__"] == selected_rowid].iloc[0]
                    st.dataframe(pd.DataFrame([selected_record[schema_cols]]), hide_index=True, use_container_width=True)
                    chosen_column = st.selectbox("Column to update", schema_cols, key=f"update_col_{crud_table}")
                    old_value = selected_record[chosen_column]
                    st.caption(f"Current value: {old_value if pd.notna(old_value) else 'NULL'} · Type: {dtype_by_col[chosen_column]}")
                    with st.form(f"update_form_{crud_table}"):
                        new_raw = st.text_input("New value (blank = NULL)", value="" if pd.isna(old_value) else str(old_value))
                        confirm_update = st.checkbox("I confirm this modification", key=f"confirm_update_{crud_table}")
                        update_submit = st.form_submit_button("💾 Update selected field", type="primary")
                    if update_submit:
                        if not confirm_update:
                            st.error("Tick the confirmation box before updating.")
                        else:
                            try:
                                new_value = to_python_value(new_raw, str(dtype_by_col[chosen_column]))
                                with get_connection(read_only=False) as con:
                                    con.execute(
                                        f"UPDATE {qident(crud_table)} SET {qident(chosen_column)} = ? WHERE rowid = ?",
                                        [new_value, int(selected_rowid)],
                                    )
                                invalidate_data()
                                st.success("Record updated successfully.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Update failed: {safe_error(exc)}")
                except Exception as exc:
                    st.error(f"Could not select a row for updating. {safe_error(exc)}")

        with delete_tab:
            if current.empty:
                st.info("This table is empty.")
            else:
                try:
                    with get_connection() as con:
                        delete_frame = con.execute(f"SELECT rowid AS __rowid__, * FROM {qident(crud_table)} LIMIT 5000").fetchdf()
                    delete_id = st.selectbox(
                        "Select record to delete",
                        delete_frame["__rowid__"].tolist(),
                        format_func=lambda rid: "rowid " + str(rid) + " · " + " | ".join(
                            f"{c}={delete_frame.loc[delete_frame['__rowid__'] == rid, c].iloc[0]}"
                            for c in schema_cols[:4]
                        ),
                        key=f"delete_row_{crud_table}",
                    )
                    delete_record = delete_frame[delete_frame["__rowid__"] == delete_id].iloc[0]
                    st.dataframe(pd.DataFrame([delete_record[schema_cols]]), hide_index=True, use_container_width=True)
                    st.error("Delete is permanent unless you restore a database backup.")
                    with st.form(f"delete_form_{crud_table}"):
                        confirm_delete = st.checkbox("I understand and want to delete this record", key=f"confirm_delete_{crud_table}")
                        delete_submit = st.form_submit_button("🗑️ Delete selected record", type="primary")
                    if delete_submit:
                        if not confirm_delete:
                            st.error("Tick the confirmation box before deleting.")
                        else:
                            try:
                                with get_connection(read_only=False) as con:
                                    con.execute(f"DELETE FROM {qident(crud_table)} WHERE rowid = ?", [int(delete_id)])
                                invalidate_data()
                                st.success("Record deleted.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Delete failed: {safe_error(exc)}")
                except Exception as exc:
                    st.error(f"Could not select a row for deletion. {safe_error(exc)}")

# ============================================================
# SQL Lab — safe read queries, joins, indexing demonstration
# ============================================================
with sql_tab:
    st.markdown('<div class="section-title">SQL LAB · QUERY, JOIN, EXPLAIN & INDEXING</div>', unsafe_allow_html=True)
    st.caption("SQL Lab is read-only by design. Use Database Studio for controlled CRUD writes.")
    st.markdown("**Schema quick reference**")
    schema_table = st.selectbox("Inspect schema", table_names, key="sql_schema_table")
    st.dataframe(get_table_info(schema_table), hide_index=True, use_container_width=True)
    with st.expander("Example queries", expanded=True):
        example_queries = {
            "Read rows": f'SELECT * FROM {qident(schema_table)} LIMIT 20',
            "Count rows": f'SELECT COUNT(*) AS row_count FROM {qident(schema_table)}',
            "Join race results + races": (
                'SELECT rr.*, r."raceName" FROM race_results rr '
                'LEFT JOIN races r ON rr."season" = r."season" AND rr."round" = r."round" LIMIT 50'
            ),
            "Explain query plan": f'EXPLAIN SELECT * FROM {qident(schema_table)} LIMIT 20',
        }
        chosen_example = st.selectbox("Load an example", list(example_queries), key="sql_example")
        if st.button("Load example into editor"):
            st.session_state["sql_editor"] = example_queries[chosen_example]
    sql_text = st.text_area(
        "Read-only SQL",
        key="sql_editor",
        value=st.session_state.get("sql_editor", f'SELECT * FROM {qident(schema_table)} LIMIT 20'),
        height=140,
    )
    if st.button("▶ Run read-only query", type="primary", key="run_sql"):
        if not query_is_read_only(sql_text):
            st.error("Only one read-only SELECT, WITH, EXPLAIN, SHOW, DESCRIBE, or PRAGMA statement is allowed here.")
        else:
            try:
                query_result = run_read_query(sql_text)
                st.success(f"Query completed · {len(query_result):,} rows returned")
                st.dataframe(query_result, hide_index=True, use_container_width=True)
                st.download_button("Download query results CSV", query_result.to_csv(index=False).encode("utf-8"),
                                   "query_results.csv", "text/csv", key="sql_download")
            except Exception as exc:
                st.error(f"Query failed: {safe_error(exc)}")

    st.markdown("---")
    st.markdown("**Indexing demonstration (DuckDB ART index)**")
    st.caption("Index creation is a write operation. Indexes can help selective lookups, but may add storage/write overhead and are not automatically beneficial for every analytical query.")
    index_table = st.selectbox("Table to index", table_names, key="index_table")
    index_schema = get_table_info(index_table)
    index_column = st.selectbox("Column to index", index_schema["column_name"].tolist(), key="index_column")
    index_name = "idx_" + re.sub(r"[^A-Za-z0-9_]", "_", f"{index_table}_{index_column}")
    st.code(f"CREATE INDEX {qident(index_name)} ON {qident(index_table)} ({qident(index_column)});", language="sql")
    if st.button("Create index", key="create_index"):
        try:
            with get_connection(read_only=False) as con:
                con.execute(
                    f"CREATE INDEX IF NOT EXISTS {qident(index_name)} ON {qident(index_table)} ({qident(index_column)})"
                )
            st.success(f"Index `{index_name}` created or already exists.")
        except Exception as exc:
            st.error(f"Index creation failed: {safe_error(exc)}")
    if st.button("Show database indexes", key="show_indexes"):
        try:
            idx = run_read_query("SELECT * FROM duckdb_indexes()")
            st.dataframe(idx, hide_index=True, use_container_width=True)
        except Exception as exc:
            st.info(f"Index metadata is not available in this DuckDB version: {safe_error(exc)}")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    '<div style="text-align:center;color:#8e929e;font-size:.78rem;">THE PADDOCK · Formula One Analytics · Streamlit + DuckDB</div>',
    unsafe_allow_html=True,
)
