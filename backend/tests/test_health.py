"""M0 健康检查路由的烟雾测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import create_app


def test_health_returns_ok() -> None:
    """/api/health 应返回 200 + {ok: True, service: beacon-backend}。"""
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["service"] == "beacon-backend"
    assert "version" in payload
