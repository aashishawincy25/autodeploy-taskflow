"""Automated tests. Each test gets a fresh temporary database (never the real one)."""
import pytest
from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})


@pytest.fixture
def client(app):
    return app.test_client()


def make(client, **over):
    data = {"title": "Write report", "description": "Chapter 1", "priority": "high",
            "due_date": "2030-01-15"}
    data.update(over)
    return client.post("/api/tasks", json=data)


def test_homepage(client):
    r = client.get("/")
    assert r.status_code == 200 and b"TaskFlow" in r.data
    assert "Content-Security-Policy" in r.headers


def test_create_task(client):
    r = make(client)
    t = r.get_json()
    assert r.status_code == 201
    assert t["id"] == 1 and t["status"] == "todo" and t["priority"] == "high"
    assert t["created_at"] and t["updated_at"]
    assert len(client.get("/api/tasks").get_json()) == 1


def test_edit_task(client):
    tid = make(client).get_json()["id"]
    r = client.put(f"/api/tasks/{tid}", json={"title": "New title", "priority": "low",
                                              "status": "in_progress"})
    t = r.get_json()
    assert r.status_code == 200
    assert (t["title"], t["priority"], t["status"]) == ("New title", "low", "in_progress")


def test_delete_task(client):
    tid = make(client).get_json()["id"]
    assert client.delete(f"/api/tasks/{tid}").status_code == 200
    assert client.get(f"/api/tasks/{tid}").status_code == 404
    assert client.get("/api/tasks").get_json() == []


def test_status_update_and_stats(client):
    tid = make(client).get_json()["id"]
    r = client.patch(f"/api/tasks/{tid}/status", json={"status": "completed"})
    assert r.get_json()["status"] == "completed"
    s = client.get("/api/stats").get_json()
    assert s["total"] == 1 and s["completed"] == 1 and s["todo"] == 0


def test_status_update_invalid(client):
    tid = make(client).get_json()["id"]
    assert client.patch(f"/api/tasks/{tid}/status", json={"status": "bogus"}).status_code == 400
    assert client.patch(f"/api/tasks/{tid}/status", json={}).status_code == 400


def test_search_and_filter(client):
    make(client, title="Buy milk", description="shop", priority="low")
    make(client, title="Deploy app", description="Flask server", priority="high")
    make(client, title="Fix bug", status="completed", priority="high")
    assert len(client.get("/api/tasks?search=flask").get_json()) == 1
    assert len(client.get("/api/tasks?priority=high").get_json()) == 2
    assert len(client.get("/api/tasks?status=completed").get_json()) == 1
    assert len(client.get("/api/tasks?search=zzz").get_json()) == 0
    assert client.get("/api/tasks?priority=urgent").status_code == 400


def test_sql_injection_is_harmless(client):
    make(client)
    r = client.get("/api/tasks?search=' OR 1=1 --")
    assert r.get_json() == []
    assert client.get("/health").get_json()["task_count"] == 1


@pytest.mark.parametrize("payload", [
    {"title": ""}, {"title": "   "}, {"title": "x" * 101},
    {"title": "ok", "description": "d" * 501}, {"title": "ok", "status": "nope"},
    {"title": "ok", "priority": "urgent"}, {"title": "ok", "due_date": "31/12/2030"},
    {"title": "ok", "due_date": "2030-02-31"},
])
def test_validation_rejects_bad_input(client, payload):
    r = client.post("/api/tasks", json=payload)
    assert r.status_code == 400 and "error" in r.get_json()


def test_non_json_body_rejected(client):
    assert client.post("/api/tasks", data="hello").status_code == 400


def test_missing_task_ids(client):
    assert client.get("/api/tasks/999").status_code == 404
    assert client.put("/api/tasks/999", json={"title": "x"}).status_code == 404
    assert client.delete("/api/tasks/999").status_code == 404
    assert client.patch("/api/tasks/999/status", json={"status": "todo"}).status_code == 404
    assert client.get("/api/tasks/abc").status_code == 404


def test_xss_text_stored_as_data_with_safe_headers(client):
    payload = "<script>alert(1)</script>"
    r = make(client, title=payload)
    assert r.content_type == "application/json"          # never served as HTML
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert "script-src 'self'" in r.headers["Content-Security-Policy"]
    assert client.get("/api/tasks").get_json()[0]["title"] == payload


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok" and body["database"] == "connected"


def test_persistence_across_app_restart(tmp_path):
    db = str(tmp_path / "persist.db")
    make(create_app({"TESTING": True, "DATABASE": db}).test_client(), title="Keep me")
    restarted = create_app({"TESTING": True, "DATABASE": db}).test_client()
    tasks = restarted.get("/api/tasks").get_json()
    assert [t["title"] for t in tasks] == ["Keep me"]


def test_tests_use_isolated_database(app):
    assert "instance" not in app.config["DATABASE"].replace("\\", "/").split("/")[-2:]
