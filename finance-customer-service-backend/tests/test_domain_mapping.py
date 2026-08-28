"""金融业务对象 -> 任务流槽位名映射测试。"""
from jinrong.domain.messages import OBJECT_TYPE_TO_SLOT


def test_financial_object_types_map_to_slots():
    assert OBJECT_TYPE_TO_SLOT["account"] == "account_no"
    assert OBJECT_TYPE_TO_SLOT["card"] == "card_no"
    assert OBJECT_TYPE_TO_SLOT["loan_product"] == "loan_product"
    assert OBJECT_TYPE_TO_SLOT["wealth_product"] == "wealth_product"


def test_mapping_covers_all_sidebar_object_types():
    # 前端侧栏只会发送这四种对象类型，映射必须齐全
    sidebar_types = {"account", "card", "loan_product", "wealth_product"}
    assert sidebar_types <= set(OBJECT_TYPE_TO_SLOT.keys())
