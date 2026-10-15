"""AutoDeploy - TaskFlow: a small Kanban task manager (Flask + SQLite)."""
import os
import sqlite3
from datetime import date, datetime, timezone

from flask import Flask, g, jsonify, render_template, request

STATUSES = ("todo", "in_progress", "completed")
PRIORITIES = ("low", "medium", "high")
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'todo',
    priority    TEXT NOT NULL DEFAULT 'medium',
    due_date    TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_app(test_config=None):
    """App factory: tests pass their own DATABASE path so real data is safe."""
    app = Flask(__name__, instance_relative_config=True)
    app.config["DATABASE"] = os.path.join(BASE_DIR, "instance", "taskflow.db")
    if test_config:
        app.config.update(test_config)
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)

    with app.app_context():
        get_db().executescript(SCHEMA)

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.after_request
    def security_headers(resp):
        # Blocks inline scripts / foreign scripts, a second layer against XSS.
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:"
        )
        resp.headers["X-Content-Type-Options"] = "nosniff"
        return resp

    # ---------- pages ----------
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        try:
            count = get_db().execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            return jsonify(status="ok", database="connected", task_count=count,
                           time=now())
        except sqlite3.Error as exc:
            return jsonify(status="error", database="unavailable", detail=str(exc)), 500

    # ---------- API ----------
    @app.get("/api/tasks")
    def list_tasks():
        sql, args = "SELECT * FROM tasks WHERE 1=1", []
        search = request.args.get("search", "").strip()
        status = request.args.get("status", "").strip()
        priority = request.args.get("priority", "").strip()
        if status and status not in STATUSES:
            return error("Invalid status filter.")
        if priority and priority not in PRIORITIES:
            return error("Invalid priority filter.")
        if search:
            sql += " AND (title LIKE ? OR description LIKE ?)"
            args += [f"%{search}%"] * 2
        if status:
            sql += " AND status = ?"
            args.append(status)
        if priority:
            sql += " AND priority = ?"
            args.append(priority)
        sql += " ORDER BY (due_date IS NULL), due_date, id DESC"
        rows = get_db().execute(sql, args).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/api/stats")
    def stats():
        rows = get_db().execute("SELECT status, due_date FROM tasks").fetchall()
        today = date.today().isoformat()
        out = {"total": len(rows), "todo": 0, "in_progress": 0, "completed": 0, "overdue": 0}
        for r in rows:
            out[r["status"]] += 1
            if r["status"] != "completed" and r["due_date"] and r["due_date"] < today:
                out["overdue"] += 1
        return jsonify(out)

    @app.post("/api/tasks")
    def create_task():
        data, err = validate(request.get_json(silent=True))
        if err:
            return error(err)
        ts = now()
        cur = get_db().execute(
            "INSERT INTO tasks (title, description, status, priority, due_date,"
            " created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (data["title"], data["description"], data["status"], data["priority"],
             data["due_date"], ts, ts))
        get_db().commit()
        return jsonify(fetch(cur.lastrowid)), 201

    @app.get("/api/tasks/<int:task_id>")
    def get_task(task_id):
        task = fetch(task_id)
        return jsonify(task) if task else error("Task not found.", 404)

    @app.put("/api/tasks/<int:task_id>")
    def update_task(task_id):
        if not fetch(task_id):
            return error("Task not found.", 404)
        data, err = validate(request.get_json(silent=True))
        if err:
            return error(err)
        get_db().execute(
            "UPDATE tasks SET title=?, description=?, status=?, priority=?, due_date=?,"
            " updated_at=? WHERE id=?",
            (data["title"], data["description"], data["status"], data["priority"],
             data["due_date"], now(), task_id))
        get_db().commit()
        return jsonify(fetch(task_id))

    @app.patch("/api/tasks/<int:task_id>/status")
    def update_status(task_id):
        if not fetch(task_id):
            return error("Task not found.", 404)
        body = request.get_json(silent=True)
        status = body.get("status") if isinstance(body, dict) else None
        if status not in STATUSES:
            return error("Status must be one of: " + ", ".join(STATUSES))
        get_db().execute("UPDATE tasks SET status=?, updated_at=? WHERE id=?",
                         (status, now(), task_id))
        get_db().commit()
        return jsonify(fetch(task_id))

    @app.delete("/api/tasks/<int:task_id>")
    def delete_task(task_id):
        if not fetch(task_id):
            return error("Task not found.", 404)
        get_db().execute("DELETE FROM tasks WHERE id=?", (task_id,))
        get_db().commit()
        return jsonify(message="Task deleted.")

    @app.errorhandler(404)
    def not_found(_e):
        if request.path.startswith("/api/"):
            return error("Not found.", 404)
        return "Page not found", 404

    return app


def get_db():
    if "db" not in g:
        from flask import current_app
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def fetch(task_id):
    row = get_db().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row) if row else None


def error(message, code=400):
    return jsonify(error=message), code


def validate(body):
    """Return (clean_data, None) or (None, error_message)."""
    if not isinstance(body, dict):
        return None, "Request body must be JSON."
    title = str(body.get("title") or "").strip()
    description = str(body.get("description") or "").strip()
    status = body.get("status") or "todo"
    priority = body.get("priority") or "medium"
    due = body.get("due_date") or None
    if not title:
        return None, "Title is required."
    if len(title) > 100:
        return None, "Title must be 100 characters or fewer."
    if len(description) > 500:
        return None, "Description must be 500 characters or fewer."
    if status not in STATUSES:
        return None, "Status must be one of: " + ", ".join(STATUSES)
    if priority not in PRIORITIES:
        return None, "Priority must be one of: " + ", ".join(PRIORITIES)
    if due:
        try:
            due = date.fromisoformat(str(due)).isoformat()
        except ValueError:
            return None, "Due date must look like YYYY-MM-DD."
    return {"title": title, "description": description, "status": status,
            "priority": priority, "due_date": due}, None


if __name__ == "__main__":
    create_app().run(debug=True)
