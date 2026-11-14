#!/usr/bin/env bash
# Start the API, load runs from the saved parkrun HTML, then plot.
set -euo pipefail

cd "$(dirname "$0")"

# 1. Start the Flask server in the background (no debug reloader, so one clean process)
python -m flask --app parkrun_v2 run &
SERVER_PID=$!
# On Windows, bash's kill can't stop native python.exe; use taskkill on its Windows PID
stop_server() {
    WIN_PID=$(ps -p "$SERVER_PID" 2>/dev/null | awk 'NR==2{print $4}')
    if [ -n "$WIN_PID" ]; then taskkill //F //T //PID "$WIN_PID" > /dev/null 2>&1 || true; fi
    kill "$SERVER_PID" 2>/dev/null || true
}
trap stop_server EXIT

# Wait until the server answers (max ~15s)
for _ in $(seq 1 30); do
    if curl -s -o /dev/null http://127.0.0.1:5000/runs; then
        break
    fi
    sleep 0.5
done

# 2. Scrape the HTML and POST every run to the API
python scrape_parkrun.py

# 3. Plot (reads runs.db, saves parkrun_times.png, opens the window)
python plot.py
