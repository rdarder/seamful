from __future__ import annotations
from typing import Type

from .resource_type import T, ResourceType


def Resource(t: Type[T]) -> ResourceType[T]:
    return ResourceType.make(t)


__all__ = Resource, ResourceType
