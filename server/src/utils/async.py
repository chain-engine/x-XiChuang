#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
异步与并发工具模块

提供将同步函数批量提交到线程池执行的封装（基于 asyncio + ThreadPoolExecutor），用于简化并发任务收集与结果聚合。
"""

import asyncio
from functools import partial
from concurrent import futures
from typing import Any, Callable, TypeVar, ParamSpec, Union, Self
from collections.abc import Sequence

P = ParamSpec('P')
R = TypeVar('R')
T = TypeVar('T')


def pool_runner(
    func: Callable[P, R],
    arg_list: Sequence[tuple[Sequence[Any], dict[str, Any]]],
    max_workers: int = 4
) -> list[Union[R, BaseException]]:
    """ run task in thread pool
    arg_list should contains args and kwargs stored in a tuple, eg:
    [
        (
            [1,2,3],
            {'zone': 'beta'}
        ),
        (
            [4,5,6],
            {'zone': 'delta'}
        ),
    ]
    set args to blank list [] if not used
    set kwargs to blank dict {} if not used
    """

    if not arg_list:
        return []

    executor = futures.ThreadPoolExecutor(max_workers=max_workers)
    loop = asyncio.new_event_loop()

    future_list: list[asyncio.Future[Union[R, BaseException]]] = []
    for args, kwargs in arg_list:
        func_to_run: Callable[[], R] = partial(func, *args, **kwargs)
        future_list.append(loop.run_in_executor(executor, func_to_run))

    result_list = loop.run_until_complete(asyncio.gather(*future_list, return_exceptions=True))
    loop.close()

    return result_list
