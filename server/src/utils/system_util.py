#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys


class SystemUtil:

    @classmethod
    def get_python_version(cls) -> sys.version_info:
        return sys.version_info


if __name__ == '__main__':
    print(SystemUtil.get_python_version())
