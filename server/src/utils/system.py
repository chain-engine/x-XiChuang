#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
系统信息模块

提供获取当前 Python 解释器版本等基础系统信息的轻量工具方法。
"""

import sys


def get_python_version() -> sys._version_info:
    return sys.version_info


if __name__ == '__main__':
    print(get_python_version())
