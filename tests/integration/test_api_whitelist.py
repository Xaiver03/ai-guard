"""tests/integration/test_api_whitelist.py -- 白名单 CRUD API 端点"""

import pytest


class TestWhitelistAPI:
    def test_get_empty(self, client):
        resp = client.get("/api/whitelist")
        assert resp.status_code == 200
        data = resp.json()
        assert data["process_names"] == []
        assert data["command_keywords"] == []
        assert data["pids"] == []

    def test_add_process_name(self, client):
        resp = client.post("/api/whitelist/process_name",
                          json={"name": "chrome"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_add_duplicate_process_name(self, client):
        client.post("/api/whitelist/process_name", json={"name": "chrome"})
        resp = client.post("/api/whitelist/process_name", json={"name": "chrome"})
        assert resp.status_code == 400

    def test_remove_process_name(self, client):
        client.post("/api/whitelist/process_name", json={"name": "chrome"})
        resp = client.delete("/api/whitelist/process_name/chrome")
        assert resp.status_code == 200

    def test_remove_nonexistent_process_name(self, client):
        resp = client.delete("/api/whitelist/process_name/nonexistent")
        assert resp.status_code == 404

    def test_add_command_keyword(self, client):
        resp = client.post("/api/whitelist/command_keyword",
                          json={"keyword": "python"})
        assert resp.status_code == 200

    def test_remove_command_keyword(self, client):
        client.post("/api/whitelist/command_keyword", json={"keyword": "python"})
        resp = client.delete("/api/whitelist/command_keyword/python")
        assert resp.status_code == 200

    def test_add_pid(self, client):
        resp = client.post("/api/whitelist/pid", json={"pid": 12345})
        assert resp.status_code == 200

    def test_remove_pid(self, client):
        client.post("/api/whitelist/pid", json={"pid": 12345})
        resp = client.delete("/api/whitelist/pid/12345")
        assert resp.status_code == 200

    def test_full_crud_flow(self, client):
        # Add entries
        client.post("/api/whitelist/process_name", json={"name": "chrome"})
        client.post("/api/whitelist/command_keyword", json={"keyword": "python"})
        client.post("/api/whitelist/pid", json={"pid": 999})

        # Verify all present
        resp = client.get("/api/whitelist")
        data = resp.json()
        assert "chrome" in data["process_names"]
        assert "python" in data["command_keywords"]
        assert 999 in data["pids"]

        # Remove each
        client.delete("/api/whitelist/process_name/chrome")
        client.delete("/api/whitelist/command_keyword/python")
        client.delete("/api/whitelist/pid/999")

        # Verify all removed
        resp = client.get("/api/whitelist")
        data = resp.json()
        assert data["process_names"] == []
        assert data["command_keywords"] == []
        assert data["pids"] == []
