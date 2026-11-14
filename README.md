# parkrun-graph

parkrun doesn't show a chart of your times over time, only a table. This project takes your parkrun results table and plots your times against date, with PBs highlighted and your current PB in the legend.

## How it works

```
saved parkrun HTML  ->  scrape_parkrun.py  ->  Flask API (parkrun_v2.py)  ->  runs.db (SQLite)  ->  plot.py  ->  parkrun_times.png
```

1. **`parkrun_v2.py`** is a small Flask REST API that stores runs in a **SQLite database** (`runs.db`, created automatically on first start) using Python's built-in `sqlite3`.
   - `GET /runs` (paginated with `offset` and `limit`), `GET /runs/<id>`
   - `POST /runs` creates a run, or **updates it if the id already exists** (upsert)
   - `PUT /runs/<id>`, `DELETE /runs/<id>`
   - Writes use HTTP Basic auth, and reads are rate limited to 10 requests per minute per IP.
   - A run's id is `<event>-<run number>`, e.g. `coventry-770`.
2. **`scrape_parkrun.py`** reads your saved results page with BeautifulSoup and `POST`s every run to the API.
3. **`plot.py`** reads `runs.db`, plots time against date, and saves `parkrun_times.png`.
4. **`run_all.sh`** starts the server, runs the scraper, then plots. It stops the server when you close the plot.

## Usage

1. On your parkrun athlete page, open the "All results" page for your athlete number while logged in, and save it with **Save As, "Webpage, HTML only"** (or Ctrl+S).
2. **Put the file in this folder and name it `results _ parkrun UK.html`.** The scripts expect that exact name and location, and they won't work without it. parkrun doesn't allow automated scraping, so this project reads a page you save yourself instead of fetching it.
3. Install and run:

```bash
pip install -r requirements.txt
bash run_all.sh
```

Port 5000 needs to be free. You can also run the pieces by hand: `python parkrun_v2.py`, then `python scrape_parkrun.py`, then `python plot.py`.

## Why go through an API?

Honestly, it's unnecessary. The scraper could write to the database directly and the plot could read it, with no server in between. I routed everything through API calls **for learning purposes**: this was my first Flask project, and I wanted to practise building a REST API with auth, rate limiting, persistence and an upsert endpoint, then use it from a real client.

## Extra files

- **`scrape_parkrun_pandas.py`** does the same scraping in about 20 lines with `pandas.read_html`, and loads the rows straight into `runs.db` with no API (re-running it is safe, since it upserts). If you only want the chart, this is the simpler and more sensible route: run it, then `plot.py`.
- **`requirements.txt`**: `pandas` and `lxml` are only needed for the pandas version.

## Notes

- The API uses hard-coded demo credentials (`admin` / `password`). That's fine for a local learning project, but don't expose it to the internet as is.
- `runs.db`, the saved HTML and the generated PNG are in `.gitignore` because they contain personal results. `parkrun.py` is an early draft of the API, superseded by `parkrun_v2.py`.
- SQLite is plenty for one person's results. For many users or concurrent writers, I'd move to PostgreSQL.
