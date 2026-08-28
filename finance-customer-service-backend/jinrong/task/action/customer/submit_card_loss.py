from typing import Any

from jinrong.Infrastructure.finance_client import finance_post
from jinrong.domain.state import DialogueState
from jinrong.task.action.base import Action, ActionResult
from jinrong.task.action.customer.shared import _request_no


class ActionSubmitCardLoss(Action):
    name = "action_submit_card_loss"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        slots = state.active_task.slots
        customer_no = state.sender_id
        card_no = str(slots.get("card_no", "")).strip()
        loss_reason = str(slots.get("loss_reason", "")).strip()
        identity = str(slots.get("identity", "")).strip()

        content = f"银行卡挂失申请。卡号：{card_no}；挂失原因：{loss_reason}；证件号后四位：{identity}。"
        try:
            data = await finance_post("/support/tickets", {
                "request_no": _request_no("LOSS"),
                "customer_no": customer_no,
                "ticket_type": "card_loss",
                "ticket_title": "银行卡挂失申请",
                "ticket_content": content,
                "related_type": "none",
                "related_id": None,
            }, customer_no=customer_no)
        except Exception as exc:
            return ActionResult(updated_slots={
                "result_message": f"挂失申请未能提交（{exc}），请稍后重试或致电客服热线。"
            })

        ticket_no = data.get("ticket_no")
        message = (
            f"银行卡 {card_no} 的挂失申请已受理，挂失工单号 {ticket_no}，请妥善保管该回执。"
            "挂失生效后该卡不可再使用，补卡或销卡请咨询人工客服。"
        )
        return ActionResult(updated_slots={"result_message": message})
