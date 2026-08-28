import json
from typing import Any

from jinrong.Infrastructure.finance_client import finance_get
from jinrong.domain.state import DialogueState
from jinrong.knowledge.provider.provider import Provider, KnowledgeChunk


class ApiAccountProvider(Provider):
    provider_id = "api.account"

    async def retrival(self, state: DialogueState) -> list[KnowledgeChunk]:
        data: Any = await finance_get(f"/customers/{state.sender_id}/accounts")
        return [KnowledgeChunk(content="客户账户信息：\n" + json.dumps(data, ensure_ascii=False, indent=2))]


class ApiCardProvider(Provider):
    provider_id = "api.card"

    async def retrival(self, state: DialogueState) -> list[KnowledgeChunk]:
        data: Any = await finance_get(f"/customers/{state.sender_id}/cards")
        return [KnowledgeChunk(content="客户银行卡信息：\n" + json.dumps(data, ensure_ascii=False, indent=2))]


class ApiTransactionProvider(Provider):
    provider_id = "api.transaction"

    async def retrival(self, state: DialogueState) -> list[KnowledgeChunk]:
        account_no = state.focused_object.id
        data: Any = await finance_get(f"/accounts/{account_no}/transactions")
        return [
            KnowledgeChunk(content=f"账户 {account_no} 交易流水：\n" + json.dumps(data, ensure_ascii=False, indent=2))
        ]


class ApiLoanProductProvider(Provider):
    provider_id = "api.loan_product"

    async def retrival(self, state: DialogueState) -> list[KnowledgeChunk]:
        data: Any = await finance_get("/loan/products")
        return [KnowledgeChunk(content="贷款产品信息：\n" + json.dumps(data, ensure_ascii=False, indent=2))]


class ApiWealthProductProvider(Provider):
    provider_id = "api.wealth_product"

    async def retrival(self, state: DialogueState) -> list[KnowledgeChunk]:
        data: Any = await finance_get("/wealth/products")
        return [KnowledgeChunk(content="理财产品信息：\n" + json.dumps(data, ensure_ascii=False, indent=2))]


class RagDefaultProvider(Provider):
    provider_id = "rag.default"

    async def retrival(self, state: DialogueState) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(content="未检索到相关开放知识（向量知识库暂未接入）")]


_FINANCE_FAQ = """金融业务常见问题（FAQ）：
1. 存款利率：人民币活期结算账户（ACC_DEMAND_CNY）为活期利率，具体以账户产品页面为准。
2. 转账手续费：本行转账免费；跨行转账按金额 0.1% 收取，最低 1 元、最高 50 元（示例，以银行公告为准）。
3. 银行卡挂失流程：请提供卡号、挂失原因和证件号后四位，客服将为您生成挂失工单，工单号作为挂失回执；挂失后卡片不可再使用。
4. 销卡规则：账户需无欠款、无冻结、无未结清理财持仓方可申请销卡；销卡前请确认账户余额已清零。
5. 贷款申请：标准个人消费贷（LOAN_CONSUMER_STD）额度区间 3000-300000 元、期限 3-36 个月、年化利率 7.2%（示例），最终以审批结果为准。
6. 风险提示：理财非存款，产品有风险，投资须谨慎。"""


class FaqDefaultProvider(Provider):
    provider_id = "faq.default"

    async def retrival(self, state: DialogueState) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(content=_FINANCE_FAQ)]
