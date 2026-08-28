from dataclasses import dataclass


@dataclass(slots=True)
class KnowledgeIntent:
    id: str
    description: str
    provider_ids: list[str]
    requires_object_type: str | None = None


# 系统支持的所有金融知识意图
KNOWLEDGE_INTENTS: dict[str, KnowledgeIntent] = {
    "account_info": KnowledgeIntent(
        id="account_info", description="账户信息咨询（账户列表/余额/状态）",
        provider_ids=["api.account"],
    ),
    "card_info": KnowledgeIntent(
        id="card_info", description="银行卡信息咨询（卡号/卡等级/状态）",
        provider_ids=["api.card"],
    ),
    "transaction_info": KnowledgeIntent(
        id="transaction_info", description="交易流水咨询（针对某个账户）",
        provider_ids=["api.transaction"], requires_object_type="account",
    ),
    "loan_product_info": KnowledgeIntent(
        id="loan_product_info", description="贷款产品咨询（额度区间/期限/年化利率/还款方式）",
        provider_ids=["api.loan_product"],
    ),
    "wealth_product_info": KnowledgeIntent(
        id="wealth_product_info", description="理财产品咨询（起购金额/收益率/风险等级）",
        provider_ids=["api.wealth_product"],
    ),
    "policy_faq": KnowledgeIntent(
        id="policy_faq", description="政策规则 FAQ（利率/手续费/挂失流程/销卡规则）",
        provider_ids=["faq.default"],
    ),
    "open_knowledge": KnowledgeIntent(
        id="open_knowledge", description="开放式金融知识咨询",
        provider_ids=["rag.default", "faq.default"],
    ),
}
