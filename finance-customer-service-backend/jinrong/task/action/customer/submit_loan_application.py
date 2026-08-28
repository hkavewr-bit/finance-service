from typing import Any

from jinrong.Infrastructure.finance_client import finance_get, finance_post
from jinrong.domain.state import DialogueState
from jinrong.task.action.base import Action, ActionResult
from jinrong.task.action.customer.shared import _request_no


class ActionSubmitLoanApplication(Action):
    name = "action_submit_loan_application"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        slots = state.active_task.slots
        customer_no = state.sender_id
        product_code = slots.get("loan_product")
        apply_amount = str(slots.get("apply_amount", "")).strip()
        apply_term = slots.get("apply_term_months")
        loan_purpose = (slots.get("loan_purpose") or "consume").strip()

        try:
            apply_term_int = int(apply_term)
        except (TypeError, ValueError):
            apply_term_int = 12

        try:
            # 1) 选择与产品匹配的授信额度号
            limit_no = await self._resolve_limit_no(customer_no, product_code)
            # 2) 从产品详情读取还款方式
            repayment_method = await self._resolve_repayment_method(product_code)
            # 3) 提交贷款申请
            data = await finance_post("/loan/applications", {
                "request_no": _request_no("LOAN"),
                "customer_no": customer_no,
                "limit_no": limit_no,
                "apply_amount": apply_amount,
                "apply_term_months": apply_term_int,
                "repayment_method": repayment_method,
                "loan_purpose": loan_purpose,
            }, customer_no=customer_no)
        except Exception as exc:
            return ActionResult(updated_slots={
                "result_message": f"贷款申请未能提交（{exc}）。请确认金额未超过可用额度、期限在允许范围内后重试。"
            })

        application_no = data.get("application_no") or data.get("loan_application_no")
        message = (
            f"贷款申请已提交，申请单号 {application_no}。"
            f"产品 {product_code}、金额 {apply_amount} 元、期限 {apply_term_int} 个月、用途 {loan_purpose}。"
            "后续将进入审批环节，请留意审批结果。"
        )
        return ActionResult(updated_slots={"result_message": message})

    async def _resolve_limit_no(self, customer_no: str, product_code: str | None) -> str:
        limits = await finance_get(f"/customers/{customer_no}/credit-limits", customer_no=customer_no)
        limit_list = (limits or {}).get("list", [])
        for limit in limit_list:
            if limit.get("product_code") == product_code:
                return limit["limit_no"]
        if limit_list:
            return limit_list[0]["limit_no"]
        raise RuntimeError("未找到可用授信额度")

    async def _resolve_repayment_method(self, product_code: str | None) -> str:
        if not product_code:
            return "equal_principal_interest"
        product = await finance_get(f"/loan/products/{product_code}")
        return (product or {}).get("repayment_method") or "equal_principal_interest"
