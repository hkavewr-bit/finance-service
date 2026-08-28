"""端到端集成测试：需要数据中台(:8000)与客服后端(:18082)均在运行。

若后端未启动则整模块跳过，避免本地单元测试被网络依赖阻断。
"""
import httpx
import pytest

BASE_URL = "http://127.0.0.1:18082"
DEMO_CUSTOMER = "CUS00000001"


def _backend_available() -> bool:
    try:
        return httpx.get(f"{BASE_URL}/health", timeout=3).status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _backend_available(), reason="客服后端未启动，跳过集成测试")


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=60) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_session(client):
    client.delete("/api/session", params={"sender_id": DEMO_CUSTOMER})


def _send_text(client, text):
    r = client.post("/api/chat", json={"sender_id": DEMO_CUSTOMER, "text": text})
    assert r.status_code == 200, r.text
    return r.json()


def _last_text(resp):
    return "".join(m["text"] for m in resp["messages"])


def test_chitchat_returns_greeting(client):
    resp = _send_text(client, "你好")

    assert resp["messages"]
    assert _last_text(resp).strip()


def test_knowledge_retrieval_loan_products(client):
    resp = _send_text(client, "你们有哪些贷款产品")

    text = _last_text(resp)
    # 数据中台 loan products 会返回真实产品信息，回复应非空且包含业务关键词
    assert text.strip()
    assert any(kw in text for kw in ("贷款", "经营", "消费", "利率"))


def test_session_endpoints_work(client):
    r = client.post("/api/session", json={"sender_id": DEMO_CUSTOMER})
    assert r.status_code == 200
    assert r.json()["session_id"]

    r = client.get("/api/session/state", params={"sender_id": DEMO_CUSTOMER})
    assert r.status_code == 200
    assert r.json()["sender_id"] == DEMO_CUSTOMER


def test_account_balance_flow_via_object_click(client):
    # 1. 发起余额查询任务
    resp = _send_text(client, "查一下我的账户余额")
    assert resp["messages"]

    # 2. 点击账户对象卡片，自动填槽并返回余额
    r = client.post("/api/chat", json={
        "sender_id": DEMO_CUSTOMER,
        "object": {
            "type": "account",
            "id": "ACC0000000001",
            "title": "账户 ACC0000000001",
            "attributes": {"account_no": "ACC0000000001", "balance_amount": "2125.00", "currency_code": "CNY"},
        },
    })
    assert r.status_code == 200, r.text

    text = _last_text(r.json())
    assert "ACC0000000001" in text


def test_sse_streaming_reconstructs_full_text(client):
    full = ""
    with client.stream("POST", "/api/chat/stream", json={"sender_id": DEMO_CUSTOMER, "text": "你好"}) as r:
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("text/event-stream")
        import json
        for line in r.iter_lines():
            if line.startswith("data: "):
                d = json.loads(line[6:])
                if d.get("type") == "bot_text":
                    full += d.get("delta", "")

    assert full.strip()
