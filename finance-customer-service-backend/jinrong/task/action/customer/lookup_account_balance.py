from typing import Any

from jinrong.Infrastructure.finance_client import finance_get
from jinrong.domain.state import DialogueState
from jinrong.task.action.base import Action, ActionResult
from jinrong.task.action.customer.shared import _fmt_amount


class ActionLookupAccountBalance(Action):
    name = "action_lookup_account_balance"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        account_no = state.active_task.slots.get("account_no")
        try:
            data = await finance_get(f"/accounts/{account_no}", customer_no=state.sender_id)
        except Exception as exc:
            return ActionResult(updated_slots={
                "result_message": f"暂时无法查询到账户 {account_no} 的信息（{exc}），请核对账户号后重试。"
            })

        product = data.get("account_product") or {}
        product_name = product.get("product_name", "")
        message = (
            f"账户 {account_no}（{product_name}）当前状态 {data.get('account_status')}，"
            f"可用余额 {_fmt_amount(data.get('balance_amount'))} 元"
            f"（冻结 {_fmt_amount(data.get('frozen_amount'))} 元）。"
        )
        return ActionResult(updated_slots={"result_message": message})
