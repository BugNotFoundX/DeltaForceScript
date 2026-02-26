# -*- coding: utf-8 -*-
"""运行时兼容与文本处理工具。"""

import re

import numpy


def patch_numpy_asscalar():
    """为旧依赖兼容 numpy.asscalar。"""

    def _asscalar(value):
        return value.item()

    setattr(numpy, "asscalar", _asscalar)


def extract_and_merge_digits(text: str) -> str:
    """识别字符串中的所有数字并合并为一个新字符串。"""
    return "".join(re.findall(r"\d", text))
