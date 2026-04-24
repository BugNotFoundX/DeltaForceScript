# -*- coding: utf-8 -*-
"""运行时兼容与文本处理工具。"""

from enum import Enum
import re


def patch_numpy_asscalar():
    """为旧依赖兼容 numpy.asscalar。"""
    import numpy

    def _asscalar(value):
        return value.item()

    setattr(numpy, "asscalar", _asscalar)


def extract_and_merge_digits(text: str) -> str:
    """识别字符串中的所有数字并合并为一个新字符串。"""
    return "".join(re.findall(r"\d", text))


class PurchaseOutcome(Enum):
    """抽选/购买弹窗识别结果。"""

    SUCCESS = "success"
    JOINED_DRAW = "joined_draw"
    NOT_SELECTED = "not_selected"
    SOLD_OUT = "sold_out"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    UNKNOWN = "unknown"


def parse_countdown_text(text: str) -> tuple[int, int] | None:
    """从倒计时 OCR 文本中解析分、秒。"""
    match = re.search(r"(\d+)\s*分\s*(\d+)\s*秒", text or "")
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def normalize_ocr_text(text: str) -> str:
    """压缩 OCR 文本，减少空格和标点差异对关键词匹配的影响。"""
    return re.sub(r"[\s:：,，.。!！?？\[\]【】()（）]", "", text or "")


OUTCOME_KEYWORDS = {
    PurchaseOutcome.INSUFFICIENT_FUNDS: (
        "余额不足",
        "三角币不足",
        "货币不足",
        "资金不足",
    ),
    PurchaseOutcome.SOLD_OUT: (
        "已售罄",
        "售罄",
        "已抢完",
        "已下架",
        "商品已下架",
        "库存不足",
        "卖完",
    ),
    PurchaseOutcome.NOT_SELECTED: (
        "未中签",
        "未获得购买资格",
        "没有获得购买资格",
        "抽选失败",
        "未抽中",
        "很遗憾",
    ),
    PurchaseOutcome.SUCCESS: (
        "购买成功",
        "交易成功",
        "支付成功",
        "已购买",
        "获得成功",
    ),
    PurchaseOutcome.JOINED_DRAW: (
        "已参与抽选",
        "参与抽选成功",
        "已成功参与",
        "报名成功",
        "等待抽选",
        "抽选中",
        "已参与",
    ),
}


def classify_purchase_outcome(text: str) -> PurchaseOutcome:
    """根据弹窗 OCR 文本分类抽选/购买结果。"""
    normalized = normalize_ocr_text(text)
    if not normalized:
        return PurchaseOutcome.UNKNOWN

    for outcome, keywords in OUTCOME_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return outcome
    return PurchaseOutcome.UNKNOWN
