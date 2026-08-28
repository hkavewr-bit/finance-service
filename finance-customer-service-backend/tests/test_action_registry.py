"""Action 自动注册测试：customer 包内所有 Action 子类应被扫描注册。"""
from jinrong.task.action.builder import build_action_runner


EXPECTED_CUSTOMER_ACTIONS = {
    "action_lookup_account_balance",
    "action_lookup_transactions",
    "action_submit_loan_application",
    "action_submit_card_loss",
    "action_submit_complaint",
}

EXPECTED_BUILTIN_ACTIONS = {
    "action_response",
    "action_listen",
}


def test_customer_actions_are_auto_registered():
    runner = build_action_runner()

    registered = set(runner.registry._actions.keys())

    assert EXPECTED_CUSTOMER_ACTIONS <= registered
    assert EXPECTED_BUILTIN_ACTIONS <= registered


def test_registry_get_returns_expected_action():
    runner = build_action_runner()

    assert runner.registry.get("action_submit_loan_application").name == "action_submit_loan_application"
    assert runner.registry.get("action_submit_card_loss").name == "action_submit_card_loss"
