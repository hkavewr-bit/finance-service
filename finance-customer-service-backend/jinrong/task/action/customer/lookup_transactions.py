from typing import Any

from jinrong.Infrastructure.finance_client import finance_get
from jinrong.domain.state import DialogueState
from jinrong.task.action.base import Action, ActionResult
from jinrong.task.action.customer.shared import _fmt_amount


class ActionLookupTransactions(Action):
    name = "action_lookup_transactions"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        account_no = state.active_task.slots.get("account_no")
        try:
            data = await finance_get(f"/accounts/{account_no}/transactions", customer_no=state.sender_id)
        except Exception as exc:
            return ActionResult(updated_slots={
                "result_message": f"暂时无法查询到账户 {account_no} 的交易流水（{exc}），请核对账户号后重试。"
            })

        transactions = (data or {}).get("list", [])
        if not transactions:
            return ActionResult(updated_slots={
                "result_message": f"账户 {account_no} 暂无交易流水记录。"
            })

        lines = []
        for txn in transactions[:5]:
            lines.append(
                f"{txn.get('transaction_at', '')} {txn.get('transaction_type', '')} "
                f"{_fmt_amount(txn.get('transaction_amount'))} 元（{txn.get('transaction_status', '')}）"
            )
        more = f"，共 {len(transactions)} 笔" if len(transactions) > 5 else ""
        message = f"账户 {account_no} 的最近交易流水：\n" + "\n".join(lines) + more + "。"
        return ActionResult(updated_slots={"result_message": message})
