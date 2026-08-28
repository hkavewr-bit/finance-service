"""数据中台 finance-data 的 HTTP 客户端封装。

统一注入鉴权头（Authorization/X-Channel-Code/X-Operator-No/X-Request-Id），
并解包 finance-data 的统一响应信封 {code, message, request_id, data}。
"""
import uuid
from typing import Any

from jinrong.Infrastructure import http_client
from jinrong.config.settings import settings


def _base() -> str:
    return settings.finance_api_base_url.rstrip("/")


def _headers(customer_no: str | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {customer_no or settings.demo_customer_no}",
        "X-Channel-Code": settings.channel_code,
        "X-Operator-No": settings.operator_no,
        "X-Request-Id": uuid.uuid4().hex,
        "Content-Type": "application/json",
    }


def make_request_no(prefix: str = "JINRONG") -> str:
    """生成写接口幂等用的 request_no。"""
    return f"{prefix}{uuid.uuid4().hex}"


def _unwrap(body: Any) -> Any:
    if not isinstance(body, dict):
        return body
    if body.get("code") != 0:
        raise RuntimeError(f"finance-data 业务错误 {body.get('code')}: {body.get('message')}")
    return body.get("data")


async def finance_get(path: str, *, customer_no: str | None = None) -> Any:
    url = f"{_base()}/api/v1{path}"
    response = await http_client.http_client.get(url, headers=_headers(customer_no))
    response.raise_for_status()
    return _unwrap(response.json())


async def finance_post(path: str, payload: dict[str, Any], *, customer_no: str | None = None) -> Any:
    url = f"{_base()}/api/v1{path}"
    response = await http_client.http_client.post(url, json=payload, headers=_headers(customer_no))
    response.raise_for_status()
    return _unwrap(response.json())
