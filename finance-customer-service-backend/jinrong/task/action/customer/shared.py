"""金融 Action 共用辅助：幂等请求号、金额格式化等。"""

from jinrong.Infrastructure.finance_client import make_request_no


def _request_no(prefix: str = "JINRONG") -> str:
    return make_request_no(prefix)


def _fmt_amount(amount) -> str:
    """把金额统一格式化为两位小数字符串。"""
    try:
        return f"{float(amount):,.2f}"
    except (TypeError, ValueError):
        return str(amount)
