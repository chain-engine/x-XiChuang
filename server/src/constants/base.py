# -*- coding: utf-8 -*-
"""
枚举基类模块

提供可描述枚举基类，支持标记值和描述信息的枚举类型。
"""

from enum import Enum
from typing import Any


class BaseEnum(str, Enum):
    """
    可描述枚举基类

    支持标记值和描述信息的枚举类型。
    - mark: 唯一标识
    - desc: 描述信息
    """

    def __init__(self, mark: str | int, desc: str) -> None:
        self._mark = mark
        self._desc = desc

    @property
    def mark(self) -> str | int:
        """获取唯一标识"""
        return self._mark

    @property
    def value(self) -> str:
        """重写 value，使枚举可直接赋值给 str 类型字段"""
        return str(self._mark)

    @property
    def desc(self) -> str:
        """获取描述信息"""
        return self._desc

    def __str__(self) -> str:
        return str(self._mark)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Enum):
            return super().__eq__(other)
        if isinstance(other, str):
            return self._mark == other
        if isinstance(other, int):
            return self._mark == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._mark)

    @classmethod
    def get_all_marks(cls) -> list[str | int]:
        """获取所有标记值列表"""
        return [member.mark for member in cls]

    @classmethod
    def get_all_descs(cls) -> list[str]:
        """获取所有描述列表"""
        return [member.desc for member in cls]

    @classmethod
    def get_choices(cls) -> tuple[tuple[str | int, str], ...]:
        """获取选择项列表，用于表单选项"""
        return tuple((member.mark, member.desc) for member in cls)

    @classmethod
    def from_mark(cls, mark: str | int) -> "BaseEnum":
        """根据标记值获取枚举成员"""
        for member in cls:
            if member.mark == mark:
                return member
        raise ValueError(f"Invalid mark: {mark}")

    @classmethod
    def is_valid(cls, mark: str | int) -> bool:
        """检查标记值是否有效"""
        return any(member.mark == mark for member in cls)
