import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter, MultipleLocator

with closing(sqlite3.connect(Path(__file__).with_name("runs.db"))) as db:
    db.row_factory = sqlite3.Row
    runs = [dict(r) for r in db.execute("SELECT date, time, pb FROM runs ORDER BY date")]

dates = [datetime.fromisoformat(r["date"]) for r in runs]
# "20:49" -> 20.82 minutes
minutes = [int(m) + int(s) / 60 for m, s in (r["time"].split(":")[:2] for r in runs)]

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(dates, minutes, marker="o", linewidth=1, color="#2C233D")

# highlight PBs
pb_dates = [d for d, r in zip(dates, runs) if r["pb"]]
pb_mins = [m for m, r in zip(minutes, runs) if r["pb"]]
ax.scatter(pb_dates, pb_mins, color="#FFA300", zorder=3, label="PB")

# current PB = fastest time overall
best = min(minutes)
best_label = f"{int(best)}:{int(round((best % 1) * 60)):02d}"
ax.axhline(best, color="#FFA300", linestyle="--", linewidth=1, label=f"Current PB: {best_label}")

# show y axis as mm:ss instead of decimal minutes
ax.yaxis.set_major_formatter(FuncFormatter(lambda m, _: f"{int(m)}:{int(round((m % 1) * 60)):02d}"))

ax.set_ylim(19.5, 30)  # 19:30 to 30:00
ax.set_xlabel("Date")
ax.set_ylabel("Time")
ax.set_title("Parkrun times")
ax.yaxis.set_major_locator(MultipleLocator(1))     # major: every minute
ax.yaxis.set_minor_locator(MultipleLocator(1 / 6))  # minor: every 10s
ax.xaxis.set_minor_locator(mdates.MonthLocator())  # minor: every month
ax.grid(which="major", alpha=0.4)
ax.grid(which="minor", alpha=0.4, linestyle="--")
ax.legend()
fig.autofmt_xdate()
plt.tight_layout()
fig.savefig(Path(__file__).with_name("parkrun_times.png"), dpi=150)
# plt.show()
