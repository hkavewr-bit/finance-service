from typing import Any

from jinrong.Infrastructure.finance_client import finance_post
from jinrong.domain.state import DialogueState
from jinrong.task.action.base import Action, ActionResult
from jinrong.task.action.customer.shared import _request_no


class ActionSubmitComplaint(Action):
    name = "action_submit_complaint"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        slots = state.active_task.slots
        customer_no = state.sender_id
        title = str(slots.get("ticket_title", "")).strip()
        content = str(slots.get("ticket_content", "")).strip()

        try:
            data = await finance_post("/support/tickets", {
                "request_no": _request_no("COMPL"),
                "customer_no": customer_no,
                "ticket_type": "complaint",
                "ticket_title": title,
                "ticket_content": content,
                "related_type": "none",
                "related_id": None,
            }, customer_no=customer_no)
        except Exception as exc:
            return ActionResult(updated_slots={
                "result_message": f"投诉工单未能提交（{exc}），请稍后重试。"
            })

        ticket_no = data.get("ticket_no")
        message = f"投诉已受理，工单号 {ticket_no}。我们会尽快安排专人跟进，感谢你的反馈。"
        return ActionResult(updated_slots={"result_message": message})
