# -*- coding: utf-8 -*-
"""
字典工具类单元测试
"""

from src.utils.dict_util import DictUtil


class TestFastGenDict:
    """快速生成字典测试"""

    def test_generates_correct_dict(self):
        result = DictUtil.fast_gen_dict()
        assert result == {"a": 0, "b": 1, "c": 2, "d": 3}

    def test_returns_dict_type(self):
        assert isinstance(DictUtil.fast_gen_dict(), dict)


class TestSumDict:
    """字典合并求和测试"""

    def test_overlapping_keys(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"a": 3, "c": 4}
        result = DictUtil.sum_dict(d1, d2)
        assert result == {"a": 4, "b": 2, "c": 4}

    def test_disjoint_keys(self):
        d1 = {"a": 1}
        d2 = {"b": 2}
        result = DictUtil.sum_dict(d1, d2)
        assert result == {"a": 1, "b": 2}

    def test_empty_dicts(self):
        result = DictUtil.sum_dict({}, {})
        assert result == {}

    def test_one_empty_dict(self):
        result = DictUtil.sum_dict({"a": 10}, {})
        assert result == {"a": 10}

    def test_float_values(self):
        d1 = {"a": 1.5}
        d2 = {"a": 2.5}
        result = DictUtil.sum_dict(d1, d2)
        assert result == {"a": 4.0}
