#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
可迭代对象工具模块

提供对可迭代对象/迭代器的类型判断与空判定能力，便于编写健壮的数据处理逻辑。
"""


from collections.abc import Iterable, Iterator, Sized
from typing import Any


def is_iterable_empty(iterable: Iterable[Any]) -> bool:
    """判断可迭代对象是否为空"""
    if isinstance(iterable, Sized):
        return len(iterable) == 0
    it = iter(iterable)
    sentinel = object()
    return next(it, sentinel) is sentinel


def is_iterable(variable: Any) -> bool:
    """判断是否为可迭代对象"""
    return isinstance(variable, Iterable)


def is_iterator_empty(iterator: Iterator[Any]) -> bool:
    """判断迭代器是否为空"""
    sentinel = object()
    return next(iterator, sentinel) is sentinel


def is_iterator(variable: Any) -> bool:
    """判断是否为迭代器"""
    return isinstance(variable, Iterator)


if __name__ == '__main__':
    print(is_iterator_empty(range(6)))
    print(is_iterator_empty(range(0)))
    print(is_iterator((x for x in range(6))))
    print(is_iterable((x for x in range(6))))
    print(is_iterable_empty(range(5)))
