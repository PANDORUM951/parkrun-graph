import json
import requests
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup


HERE = Path(__file__).parent
HTML_FILE = HERE / "results _ parkrun UK.html"

# 1. Parse the HTML text into a navigable tree
soup = BeautifulSoup(HTML_FILE.read_text(encoding="utf-8"), "html.parser")

# 2. Find the right table: the page has several <table id="results">,
#    so pick the one whose <caption> says "All Results"
table = next(
    t for t in soup.find_all("table", id="results")
    if t.caption and "All" in t.caption.get_text() and "Results" in t.caption.get_text()
)

# 3. Walk the body rows; each <td> is one column
URL = "http://127.0.0.1:5000/runs"
AUTH = ("admin", "password")

count = 0
for row in table.tbody.find_all("tr"):
    cells = row.find_all("td")
    event, date, run_no, pos, time_, grade, pb = (
        c.get_text(strip=True).replace("\xa0", "") for c in cells
    )
    data = {
        "location": event,
        "date": datetime.strptime(date, "%d/%m/%Y").date().isoformat(),
        "id": f"{event.lower().replace(' ', '-')}-{run_no}",
        "position": int(pos),
        "time": time_,
        "age_grade_pct": float(grade.rstrip("%")),
        "pb": pb == "PB",
    }

    resp = requests.post(URL, json=data, auth=AUTH)
    if resp.status_code in (200, 201):
        count += 1
    else:
        print(data["id"], resp.status_code, resp.text)

print(f"{count} runs added to the API")