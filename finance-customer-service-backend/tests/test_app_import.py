"""FastAPI 应用构建 + 路由注册测试。"""
from jinrong.api.app import app


def test_app_builds_with_routes():
    assert app is not None
    assert app.title is not None or app.description is not None


def test_expected_routes_are_registered():
    # FastAPI 0.136 将 include_router 的路由包装为 _IncludedRouter，
    # 直接读 app.routes 拿不到真实 path，改用 OpenAPI schema 校验。
    routes = set(app.openapi()["paths"].keys())

    expected = {
        "/api/chat",
        "/api/chat/stream",
        "/api/chat/history",
        "/api/session",
        "/api/session/state",
        "/health",
    }

    assert expected <= routes
