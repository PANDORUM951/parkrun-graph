import sqlite3
from io import StringIO
from pathlib import Path

import pandas as pd

from parkrun_v2 import DB_FILE, init_db  # reuse the API's schema (importing it creates the table)

HERE = Path(__file__).parent
HTML_FILE = HERE / "results _ parkrun UK.html"

# read_html returns a list of DataFrames, one per <table>; pick the one with a "Run Number" column
tables = pd.read_html(StringIO(HTML_FILE.read_text(encoding="utf-8")))
df = next(t for t in tables if "Run Number" in t.columns)

df = df.rename(columns={
    "Event": "location", "Run Date": "date", "Pos": "position",
    "Time": "time", "Age Grade": "age_grade_pct", "PB?": "pb",
})
df["id"] = df["location"].str.lower().str.replace(" ", "-") + "-" + df["Run Number"].astype(str)
df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y").dt.strftime("%Y-%m-%d")
df["age_grade_pct"] = df["age_grade_pct"].str.rstrip("%").astype(float)
df["pb"] = df["pb"] == "PB"

cols = ["location", "date", "id", "position", "time", "age_grade_pct", "pb"]
df["pb"] = df["pb"].astype(int)  # SQLite stores booleans as 0/1

init_db()
with sqlite3.connect(DB_FILE) as db:  # commits on success
    db.executemany("""
        INSERT INTO runs (id, location, date, position, time, age_grade_pct, pb)
        VALUES (:id, :location, :date, :position, :time, :age_grade_pct, :pb)
        ON CONFLICT(id) DO UPDATE SET
            location = excluded.location, date = excluded.date, position = excluded.position,
            time = excluded.time, age_grade_pct = excluded.age_grade_pct, pb = excluded.pb
    """, df[cols].to_dict("records"))
print(f"Saved {len(df)} runs to {DB_FILE}")
