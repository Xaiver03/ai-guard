"""tests/integration/test_api_processes.py -- 进程操作 API 端点"""

import pytest
from unittest.mock import patch, MagicMock
from aigard.core.killer import ActionResult


class TestGetProcesses:
    def test_empty_processes(self, client):
        resp = client.get("/api/processes")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_with_processes(self, client, app_state):
        # Clear the DataCache to avoid stale empty cache from prior test
        client.post("/api/cache/clear")
        app_state["threads"].latest_processes = [
            {"pid": 1, "name": "node", "cmdline": "node", "mem_mb": 100,
             "cpu_percent": 5, "status": "running", "risk": "safe",
             "create_time": 1000, "risk_label": "safe", "risk_reasons": [],
             "suggested_action": "kill"},
        ]
        resp = client.get("/api/processes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "node"
        assert "whitelisted" in data[0]


class TestSingleProcessOps:
    @patch("aigard.api.routes.pause_process")
    def test_pause_success(self, mock_pause, client):
        mock_pause.return_value = ActionResult(True, "已暂停", 100.0)
        resp = client.post("/api/processes/123/pause")
        assert resp.status_code == 200
        assert "已暂停" in resp.json()["message"]

    @patch("aigard.api.routes.pause_process")
    def test_pause_failure(self, mock_pause, client):
        mock_pause.return_value = ActionResult(False, "不存在")
        resp = client.post("/api/processes/999/pause")
        assert resp.status_code == 400

    @patch("aigard.api.routes.resume_process")
    def test_resume_success(self, mock_resume, client):
        mock_resume.return_value = ActionResult(True, "已恢复")
        resp = client.post("/api/processes/123/resume")
        assert resp.status_code == 200

    @patch("aigard.api.routes.kill_process")
    def test_kill_success(self, mock_kill, client):
        mock_kill.return_value = ActionResult(True, "已终止", 200.0)
        resp = client.post("/api/processes/123/kill")
        assert resp.status_code == 200
        assert resp.json()["mem_freed_mb"] == 200.0

    @patch("aigard.api.routes.kill_process")
    def test_kill_failure(self, mock_kill, client):
        mock_kill.return_value = ActionResult(False, "权限不足")
        resp = client.post("/api/processes/123/kill")
        assert resp.status_code == 400


class TestBatchOps:
    @patch("aigard.api.routes.kill_process")
    def test_batch_kill(self, mock_kill, client):
        mock_kill.return_value = ActionResult(True, "ok", 100.0)
        resp = client.post("/api/processes/batch/kill", json={"pids": [1, 2, 3]})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 3
        assert data["total_freed_mb"] == 300.0

    @patch("aigard.api.routes.pause_process")
    def test_batch_pause(self, mock_pause, client):
        mock_pause.return_value = ActionResult(True, "ok", 0)
        resp = client.post("/api/processes/batch/pause", json={"pids": [1, 2]})
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 2

    @patch("aigard.api.routes.kill_process")
    def test_batch_kill_safe(self, mock_kill, client, app_state):
        app_state["threads"].latest_processes = [
            {"pid": 10, "name": "node", "mem_mb": 100, "risk": "safe"},
            {"pid": 20, "name": "vite", "mem_mb": 200, "risk": "safe"},
            {"pid": 30, "name": "claude", "mem_mb": 300, "risk": "danger"},
        ]
        mock_kill.return_value = ActionResult(True, "ok", 100.0)
        resp = client.post("/api/processes/batch/kill-safe")
        assert resp.status_code == 200
        data = resp.json()
        assert data["killed"] == 2  # Only safe processes


class TestAutokill:
    def test_get_status(self, client):
        resp = client.get("/api/autokill/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert data["enabled"] is False

    def test_toggle(self, client, app_state):
        resp = client.post("/api/autokill/toggle")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

        resp = client.post("/api/autokill/toggle")
        assert resp.json()["enabled"] is False

    def test_get_log(self, client):
        resp = client.get("/api/autokill/log")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestBlacklist:
    def test_block_process(self, client):
        resp = client.post("/api/processes/block", json={"name": "badproc"})
        assert resp.status_code == 200
        assert "badproc" in resp.json()["blocked"]

    def test_block_empty_name(self, client):
        resp = client.post("/api/processes/block", json={"name": ""})
        assert resp.status_code == 400

    def test_unblock_process(self, client, app_state):
        with app_state["threads"].lock:
            app_state["threads"].blocked_processes.add("badproc")
        resp = client.post("/api/processes/unblock", json={"name": "badproc"})
        assert resp.status_code == 200

    def test_get_blocked(self, client, app_state):
        with app_state["threads"].lock:
            app_state["threads"].blocked_processes.add("proc1")
        resp = client.get("/api/processes/blocked")
        assert resp.status_code == 200
        assert "proc1" in resp.json()["blocked"]

    def test_clear_blocked(self, client, app_state):
        with app_state["threads"].lock:
            app_state["threads"].blocked_processes.add("proc1")
        resp = client.post("/api/processes/blocked/clear")
        assert resp.status_code == 200
        assert resp.json()["blocked"] == []


class TestScheduledKill:
    def test_get_status(self, client):
        resp = client.get("/api/scheduled-kill/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "interval_minutes" in data

    def test_update_config(self, client):
        resp = client.post("/api/scheduled-kill/config",
                          json={"enabled": True, "interval_minutes": 5})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True
        assert resp.json()["interval_minutes"] == 5

    def test_invalid_interval(self, client):
        resp = client.post("/api/scheduled-kill/config",
                          json={"interval_minutes": 0})
        assert resp.status_code == 400
