"""tests/integration/test_api_metrics.py -- 指标和历史 API 端点"""

import pytest
from aigard.core.monitor import Metrics


class TestGetMetrics:
    def test_empty_returns_empty(self, client):
        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_with_data(self, client, app_state, make_metrics):
        m = make_metrics(cpu_percent=42, mem_percent=65)
        app_state["history"].push(m)

        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cpu_percent"] == 42
        assert data["mem_percent"] == 65


class TestGetHistory:
    def test_empty_returns_empty_list(self, client):
        resp = client.get("/api/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_all_data(self, client, app_state, make_metrics):
        app_state["history"].push(make_metrics(cpu_percent=10))
        app_state["history"].push(make_metrics(cpu_percent=20))

        resp = client.get("/api/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["cpu_percent"] == 10
        assert data[1]["cpu_percent"] == 20


class TestHTMLPages:
    def test_index_page(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "html" in resp.text.lower()

    def test_bookmarks_page(self, client):
        resp = client.get("/bookmarks.html")
        assert resp.status_code == 200

    def test_usage_page(self, client):
        resp = client.get("/usage.html")
        assert resp.status_code == 200


class TestCacheManagement:
    def test_clear_cache(self, client):
        resp = client.post("/api/cache/clear")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_cache_stats(self, client):
        resp = client.get("/api/cache/stats")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)


class TestAlertHistory:
    def test_get_alert_history(self, client):
        resp = client.get("/api/alerts/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
