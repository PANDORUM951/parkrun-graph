import sqlite3
from contextlib import closing
from functools import wraps
from pathlib import Path
from time import time

from flask import Flask, abort, g, jsonify, make_response, request

app = Flask(__name__)

DB_FILE = Path(__file__).with_name("runs.db")
COLUMNS = ["id", "location", "date", "position", "time", "age_grade_pct", "pb"]


# ---------- Database ----------
def get_db():
    # one connection per request, closed automatically by close_db
    if "db" not in g:
        g.db = sqlite3.connect(DB_FILE)
        g.db.row_factory = sqlite3.Row  # rows behave like dicts
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with closing(sqlite3.connect(DB_FILE)) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                location TEXT NOT NULL,
                date TEXT NOT NULL,
                position INTEGER,
                time TEXT NOT NULL,
                age_grade_pct REAL,
                pb INTEGER NOT NULL DEFAULT 0
            )""")
        db.commit()


def row_to_dict(row):
    d = dict(row)
    d["pb"] = bool(d["pb"])  # SQLite has no boolean type: stored as 0/1
    return d


init_db()
client_times = {}


# ---------- Auth ----------
def check_auth(username, password):
    return username == "admin" and password == "password"


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            abort(401)
        return f(*args, **kwargs)
    return decorated


# ---------- Rate limit ----------
def rate_limit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr
        now = time()
        recent = [t for t in client_times.get(ip, []) if now - t < 60]
        if len(recent) >= 10:
            return make_response(jsonify({"error": "Too many requests"}), 429)
        recent.append(now)
        client_times[ip] = recent
        return f(*args, **kwargs)
    return decorated


# ---------- Routes ----------
@app.route("/runs", methods=["GET"])
@rate_limit
def get_runs():
    offset = request.args.get("offset", 0, type=int)
    limit = request.args.get("limit", 10, type=int)
    rows = get_db().execute(
        "SELECT * FROM runs ORDER BY date DESC, id LIMIT ? OFFSET ?", (limit, offset)
    ).fetchall()
    return jsonify([row_to_dict(r) for r in rows])

@app.route("/runs/<string:run_id>", methods=["GET"])
@rate_limit
def get_run_id(run_id):
    row = get_db().execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Run not found"}), 404
    return jsonify(row_to_dict(row))

@app.route("/runs", methods=["POST"])
@requires_auth
def add_run():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Body must be a JSON object"}), 400
    missing = [c for c in COLUMNS if c not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    row = {c: data[c] for c in COLUMNS}
    row["pb"] = int(bool(row["pb"]))

    db = get_db()
    existed = db.execute("SELECT 1 FROM runs WHERE id = ?", (row["id"],)).fetchone() is not None

    # upsert: insert, or overwrite the existing row if the id already exists (like PUT)
    db.execute("""
        INSERT INTO runs (id, location, date, position, time, age_grade_pct, pb)
        VALUES (:id, :location, :date, :position, :time, :age_grade_pct, :pb)
        ON CONFLICT(id) DO UPDATE SET
            location = excluded.location, date = excluded.date,
            position = excluded.position, time = excluded.time,
            age_grade_pct = excluded.age_grade_pct, pb = excluded.pb
    """, row)
    db.commit()
    return jsonify({**row, "pb": bool(row["pb"])}), (200 if existed else 201)


@app.route("/runs/<string:run_id>", methods=["PUT"])
@rate_limit
@requires_auth
def update_run(run_id):
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Body must be a JSON object"}), 400
    # whitelist columns (also keeps ids fixed); only these names are ever put in the SQL text
    updates = {k: v for k, v in data.items() if k in COLUMNS and k != "id"}
    if not updates:
        return jsonify({"error": "No updatable fields given"}), 400
    if "pb" in updates:
        updates["pb"] = int(bool(updates["pb"]))

    db = get_db()
    set_clause = ", ".join(f"{col} = ?" for col in updates)
    cur = db.execute(f"UPDATE runs SET {set_clause} WHERE id = ?", (*updates.values(), run_id))
    db.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "Run not found"}), 404
    row = db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return jsonify(row_to_dict(row))


@app.route("/runs/<string:run_id>", methods=["DELETE"])
@rate_limit
@requires_auth
def delete_run(run_id):
    db = get_db()
    cur = db.execute("DELETE FROM runs WHERE id = ?", (run_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "Run not found"}), 404
    return jsonify({"result": "Run deleted"})


if __name__ == "__main__":
    app.run(debug=True)
