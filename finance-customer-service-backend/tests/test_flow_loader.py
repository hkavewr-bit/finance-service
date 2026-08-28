"""任务流配置加载测试：5 条金融任务流应完整加载。"""
from pathlib import Path

from jinrong.task.flows.loader import FlowsLoader

PROJECT_DIR = Path(__file__).resolve().parents[1]
FLOW_CONFIG_DIR = PROJECT_DIR / "flow_config"

EXPECTED_FLOWS = {
    "account_balance_query",
    "transaction_query",
    "loan_application",
    "card_loss_report",
    "complaint_ticket",
}


def test_user_flows_load_with_five_financial_flows():
    flow_list = FlowsLoader().load_single_yaml(FLOW_CONFIG_DIR / "user_flows.yml")

    flow_ids = {flow.id for flow in flow_list.flows}

    assert EXPECTED_FLOWS <= flow_ids


def test_loan_application_flow_collects_expected_slots():
    flow_list = FlowsLoader().load_single_yaml(FLOW_CONFIG_DIR / "user_flows.yml")

    loan_flow = flow_list.get_flow_by_id("loan_application")

    assert loan_flow is not None
    assert {"loan_product", "apply_amount", "apply_term_months", "loan_purpose"} <= set(loan_flow.slots.keys())


def test_card_loss_flow_collects_card_slots():
    flow_list = FlowsLoader().load_single_yaml(FLOW_CONFIG_DIR / "user_flows.yml")

    card_loss = flow_list.get_flow_by_id("card_loss_report")

    assert card_loss is not None
    assert {"card_no", "loss_reason"} <= set(card_loss.slots.keys())
