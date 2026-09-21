#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
多进程任务编排模块

提供生产者-消费者模式的多进程执行封装，用于提升批量任务处理吞吐，并支持可选的进度输出。
"""

from __future__ import annotations

from collections.abc import Callable
from multiprocessing import Pool, Process, Queue
from typing import Any, Generic, TypeVar, cast


TIn = TypeVar("TIn")
TOut = TypeVar("TOut")


def _create_job(produce_func: Callable[..., TOut], args: tuple[Any, ...], i: int) -> tuple[int, TOut]:
    res = produce_func(*args)
    return i, res


def run_multi(
    producer_func: Callable[..., TOut],
    consumer_func: Callable[[TOut], Any],
    producer_args: list[tuple[Any, ...]],
    producer_num: int = 1,
    consumer_num: int = 1,
    debug: bool = False,
) -> None:
    """
    多进程处理, 加快处理速度

    example

    def porducer_func(i):
        time.sleep(0.5)
        return i

    def consumer_func(i):
        print(i)

    producer_args = [(i,) for i in range(100)]

    run_multi(producer_func, consumer_func, producer_args, debug=True)

    :param: producer_func: 生产者方法, 比如: lambda x: x
    :param: consumer_func: 消费者方法, 比如: lambda x: x
    :param: producer_args: 生产者任务, 比如 [(1,), (2,), (3,), (4,)]
    :param: producer_num:  生产者数量, 默认1, 建议限制6以下, 根据实际的测试情况来选择
    :param: consumer_num:  消费者数量, 默认1, 建议限制6以下, 根据实际的测试情况来选择
    :param: debug:         是否进行任务执行情况的打印, 默认不输出

    producer_func 的输出是 consumer_func 的输入
    session 需要使用 scop_session

    """
    if producer_num <= 0:
        raise ValueError("producer_num must be > 0")
    if consumer_num <= 0:
        raise ValueError("consumer_num must be > 0")

    jobs_q: Queue = Queue()
    producer_pool = Pool(processes=producer_num)
    consumers: list[Process] = []

    def consume_jobs(func: Callable) -> None:
        total = len(producer_args) or 1
        while True:
            item = jobs_q.get()
            if item is None:
                return
            i, job = item
            if debug:
                print(f"---{round(i / total * 100, 2)}%---", end="\r")
            func(job)

    # create jobs
    for i, args in enumerate(producer_args):
        producer_pool.apply_async(
            func=_create_job,
            args=(producer_func, args, i),
            callback=lambda item: jobs_q.put(cast(tuple[int, TOut], item)),
        )

    # start consumers
    for _ in range(consumer_num):
        p = Process(target=consume_jobs, args=(consumer_func,))
        consumers.append(p)

    for c in consumers:
        c.start()

    # wait for producers to finish
    producer_pool.close()
    producer_pool.join()
    for _ in range(consumer_num):
        jobs_q.put(None)

    # wait for consumers to finish
    for c in consumers:
        c.join()
