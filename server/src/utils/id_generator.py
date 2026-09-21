#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ID 生成模块

提供 UUID 与基于时间戳的唯一 ID 生成方法，便于在业务中快速生成标识符。
"""

import uuid
import time
import secrets


def gen_uuid() -> str:
    new_uuid = uuid.uuid4()
    return str(new_uuid)


def gen_timestamp_id() -> int:
    # microseconds since epoch (approx) + small random suffix
    micros = time.time_ns() // 1_000
    return int(micros) + secrets.randbelow(9000) + 1000


if __name__ == '__main__':
    print(gen_uuid())
    print(gen_timestamp_id())
