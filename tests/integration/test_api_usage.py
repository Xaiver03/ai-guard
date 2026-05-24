"""tests/integration/test_api_usage.py -- Claude 使用统计 API 端点"""

import pytest
from unittest.mock import patch, MagicMock


class TestUsageAPI:
    @patch("aigard.api.usage._ensure_cache")
    @patch("aigard.api.usage.cache")
    def test_get_summary(self, mock_cache, mock_ensure):
        mock_cache.get_summary.return_value = {
            "input_tokens": 10000,
            "output_tokens": 5000,
            "total_tokens": 15000,
            "total_cost": 0.05,
            "active_days": 3,
            "models_count": 2,
            "total_requests": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
        }
        from fastapi.testclient import TestClient
        from aigard.api.usage import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            resp = client.get("/api/usage/summary")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_tokens"] == 15000
            assert data["active_days"] == 3

    @patch("aigard.api.usage._ensure_cache")
    @patch("aigard.api.usage.cache")
    def test_get_daily(self, mock_cache, mock_ensure):
        mock_cache.get_daily.return_value = [
            {"date": "2026-05-24", "total_tokens": 1000, "total_cost": 0.01}
        ]
        from fastapi.testclient import TestClient
        from aigard.api.usage import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            resp = client.get("/api/usage/daily")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["date"] == "2026-05-24"

    @patch("aigard.api.usage._ensure_cache")
    @patch("aigard.api.usage.cache")
    def test_get_hourly(self, mock_cache, mock_ensure):
        mock_cache.get_hourly.return_value = [
            {"hour": "2026-05-24T14", "total_tokens": 500}
        ]
        from fastapi.testclient import TestClient
        from aigard.api.usage import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            resp = client.get("/api/usage/hourly")
            assert resp.status_code == 200
            assert len(resp.json()) == 1

    @patch("aigard.api.usage._ensure_cache")
    @patch("aigard.api.usage.cache")
    def test_get_monthly(self, mock_cache, mock_ensure):
        mock_cache.get_daily.return_value = [
            {"date": "2026-05-24", "input_tokens": 1000, "output_tokens": 500,
             "cache_creation_tokens": 200, "cache_read_tokens": 100,
             "total_tokens": 1800, "total_cost": 0.01,
             "models_used": ["claude-sonnet-4-6"], "model_breakdowns": []},
        ]
        from fastapi.testclient import TestClient
        from aigard.api.usage import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            resp = client.get("/api/usage/monthly")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["month"] == "2026-05"

    def test_get_pricing(self, client):
        resp = client.get("/api/usage/pricing")
        assert resp.status_code == 200
        data = resp.json()
        assert "claude-sonnet-4-6" in data


class TestUsagePresets:
    @patch("aigard.api.usage._ensure_cache")
    @patch("aigard.api.usage.cache")
    def test_preset_today(self, mock_cache, mock_ensure):
        mock_cache.get_summary.return_value = {
            "input_tokens": 0, "output_tokens": 0,
            "total_tokens": 0, "total_cost": 0, "active_days": 0,
            "models_count": 0, "total_requests": 0,
            "cache_creation_tokens": 0, "cache_read_tokens": 0,
        }
        from fastapi.testclient import TestClient
        from aigard.api.usage import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            resp = client.get("/api/usage/summary?preset=today")
            assert resp.status_code == 200
