from __future__ import annotations
from typing import Type, TypeVar

from .resource_type import ResourceType

T = TypeVar("T")


def Resource(t: Type[T]) -> ResourceType[T]:
    return ResourceType.make(t)


__all__ = ("Resource",)
