#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
字典工具模块

提供字典快速构造、字典合并与数值累加等常用操作，简化数据处理代码。
"""

from typing import TypeVar


T = TypeVar("T")


def fast_gen_dict() -> dict[str, int]:
    """快速生成字典"""
    return dict(zip("abcd", range(4)))


def sum_dict(dict_1: dict[T, int | float], dict_2: dict[T, int | float]) -> dict[T, int | float]:
    """将两个字典合并，相同key的值相加，不同key值保留"""
    temp: dict[T, int | float] = {}
    for key in dict_1.keys() | dict_2.keys():
        temp[key] = sum([d.get(key, 0) for d in (dict_1, dict_2)])
    return temp
