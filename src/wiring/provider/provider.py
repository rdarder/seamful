from typing import TypeVar, Generic

from wiring.provider.provider_type import ProviderType

M = TypeVar("M")


class Provider(Generic[M], metaclass=ProviderType):
    pass
