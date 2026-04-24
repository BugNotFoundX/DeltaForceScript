from deltaforcescript.runtime_utils import (
    PurchaseOutcome,
    classify_purchase_outcome,
    extract_and_merge_digits,
    parse_countdown_text,
)


def test_extract_and_merge_digits():
    assert extract_and_merge_digits("12分 03秒") == "1203"


def test_parse_countdown_text():
    assert parse_countdown_text("0分 03秒") == (0, 3)
    assert parse_countdown_text("剩余 1 分 20 秒") == (1, 20)
    assert parse_countdown_text("1小时") is None


def test_classify_purchase_outcome_success():
    assert classify_purchase_outcome("购买成功") == PurchaseOutcome.SUCCESS
    assert classify_purchase_outcome("支付成功，商品已入库") == PurchaseOutcome.SUCCESS


def test_classify_purchase_outcome_joined_draw():
    assert classify_purchase_outcome("已参与抽选，请等待结果") == PurchaseOutcome.JOINED_DRAW
    assert classify_purchase_outcome("参与抽选成功") == PurchaseOutcome.JOINED_DRAW


def test_classify_purchase_outcome_not_selected():
    assert classify_purchase_outcome("很遗憾，未中签") == PurchaseOutcome.NOT_SELECTED
    assert classify_purchase_outcome("未获得购买资格") == PurchaseOutcome.NOT_SELECTED


def test_classify_purchase_outcome_sold_out():
    assert classify_purchase_outcome("商品已售罄") == PurchaseOutcome.SOLD_OUT
    assert classify_purchase_outcome("商品已下架") == PurchaseOutcome.SOLD_OUT


def test_classify_purchase_outcome_insufficient_funds():
    assert classify_purchase_outcome("余额不足") == PurchaseOutcome.INSUFFICIENT_FUNDS
    assert classify_purchase_outcome("三角币不足") == PurchaseOutcome.INSUFFICIENT_FUNDS


def test_classify_purchase_outcome_unknown():
    assert classify_purchase_outcome("请稍后再试") == PurchaseOutcome.UNKNOWN
    assert classify_purchase_outcome("") == PurchaseOutcome.UNKNOWN
