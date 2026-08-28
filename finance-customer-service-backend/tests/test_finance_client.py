"""数据中台响应信封 {code, message, request_id, data} 解包逻辑测试。"""
import pytest

from jinrong.Infrastructure.finance_client import _unwrap, make_request_no


def test_unwrap_returns_data_on_success():
    body = {"code": 0, "message": "ok", "request_id": "r1", "data": {"list": [1, 2, 3]}}

    assert _unwrap(body) == {"list": [1, 2, 3]}


def test_unwrap_raises_on_business_error():
    body = {"code": 4001, "message": "账户不存在", "request_id": "r1", "data": None}

    with pytest.raises(RuntimeError, match="4001"):
        _unwrap(body)


def test_unwrap_passes_through_non_dict():
    assert _unwrap([1, 2, 3]) == [1, 2, 3]
    assert _unwrap(None) is None


def test_make_request_no_has_prefix_and_is_unique():
    a = make_request_no("JINRONG")
    b = make_request_no("JINRONG")

    assert a.startswith("JINRONG")
    assert b.startswith("JINRONG")
    assert a != b
