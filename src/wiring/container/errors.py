from __future__ import annotations
from dataclasses import dataclass
from itertools import chain
from typing import Union, Any, Type, cast, TYPE_CHECKING

from wiring.errors import HelpfulException, Text, qname, sname, rdef, point_to_definition, rname
from wiring.module.module_type import ModuleType
from wiring.resource import ModuleResource, ProviderResource, BoundResource
from wiring.provider.provider_type import ProviderType, ProviderMethod

if TYPE_CHECKING:
    from wiring.container import Container


class ModuleNotRegisteredForResource(HelpfulException):
    def __init__(
        self,
        resource: BoundResource[Any],
        registered_modules: set[ModuleType],
        known_modules: set[ModuleType],
    ):
        self.resource = resource
        self.registered_modules = registered_modules
        self.known_modules = known_modules

    def explanation(self) -> str:
        t = Text("Attempted to provide for resource:")
        t.indented_line(rdef(self.resource))
        t.newline("Which doesn't belong to any registered module. Registered modules are:")
        with t.indented_block(blank_before=False):
            for module in self.registered_modules:
                t.newline(f"- {sname(module)}")
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to provide for resource that does not belong to any registered module."


class ModuleAlreadyRegistered(HelpfulException):
    def __init__(self, module: ModuleType, registered_modules: set[ModuleType]):
        self.module = module
        self.registered_modules = registered_modules

    def explanation(self) -> str:
        t = Text(f"Attempted to register module {qname(self.module)}")
        t.sentence("which is already registered. Registered modules are:")
        with t.indented_block(blank_before=False):
            for module in self.registered_modules:
                t.newline(f"- {sname(module)}")
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to register module that is already registered."


class ProviderModuleMismatch(HelpfulException):
    def __init__(self, provider: ProviderType, module: ModuleType):
        self.provider = provider
        self.module = module

    def explanation(self) -> str:
        t = Text(
            f"Attempted to register({sname(self.module)}, provider={sname(self.provider)}) "
            f"but {qname(self.provider)} provides for module {qname(self.provider.module)} "
            f"instead."
        )
        t.blank()
        t.newline(point_to_definition(self.provider))
        t.newline(point_to_definition(self.module))
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "Attempted to register a provider alongside a module, "
            "but the provider provides for a different module."
        )


class CannotRegisterProviderToNotRegisteredModule(HelpfulException):
    def __init__(self, provider: ProviderType, registered_modules: set[ModuleType]):
        self.provider = provider
        self.registered_modules = registered_modules

    def explanation(self) -> str:
        t = Text(f"Attempted to register provider {qname(self.provider)}")
        t.sentence(
            f"which provides for {qname(self.provider.module)}, "
            f"which is not registered. Registered modules are:"
        )
        with t.indented_block(blank_before=False):
            for module in self.registered_modules:
                t.newline(f"- {sname(module)}")
        t.newline(
            "Registering providers for implicit modules is only meant to be used for "
            "testing and secondary scenarios, and can be enabled by calling:"
        )
        t.indented_line("container.reopen_registrations(allow_implicit_modules=True)")
        t.blank()
        t.newline(
            "If instead, the container is expected to provide resources for "
            f"{qname(self.provider.module)}, you can register both at once by calling:"
        )
        t.indented_line(
            f"container.register({sname(self.provider.module)}, provider={sname(self.provider)})"
        )
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to register a provider for a module that is not registered."


class CannotOverrideRegisteredProvider(HelpfulException):
    def __init__(self, module: ModuleType, *, registered: ProviderType, registering: ProviderType):
        self.module = module
        self.registered = registered
        self.registering = registering

    def explanation(self) -> str:
        t = Text(f"Attempted to register provider {qname(self.registering)}")
        if self.registered is self.registering:
            t.sentence("which is already registered.")
        else:
            t.sentence(
                f"which provides for {qname(self.module)}, "
                f"but {qname(self.registered)} was already registered as its provider."
            )

            t.blank()

            t.newline(
                "Overriding providers is not allowed. You can override a provider "
                "after the container closed registrations by reopening it as follows:"
            )
            t.indented_line("container.reopen_registrations(allow_overriding_providers=True)")
            t.blank()
            t.newline(
                "Keep in mind that overriding providers is mostly meant for testing "
                "and alternative running scenarios."
            )
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "Attempted to register a provider for a module that already "
            "has a registered provider."
        )


class ModuleWithoutRegisteredOrDefaultProvider(HelpfulException):
    def __init__(self, module: ModuleType):
        self.module = module

    def explanation(self) -> str:
        t = Text(f"Module {qname(self.module)} has no registered or default provider.")
        return str(t)

    def failsafe_explanation(self) -> str:
        return "A registered module has no registered or default provider."


class CannotProvideUntilRegistrationsAreClosed(HelpfulException):
    def explanation(self) -> str:
        t = Text(
            "Attempted to provide a resource before registrations were closed. "
            "You can close registrations by calling:"
        )
        t.indented_line("container.close_registrations()")
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to provide a resource before registrations were closed."


class RegistrationsAreClosed(HelpfulException):
    def __init__(self, registering: Union[ModuleType, ProviderType]):
        self.registering = registering

    def explanation(self) -> str:
        from wiring.module.module_type import ModuleType
        from wiring.provider.provider_type import ProviderType

        if isinstance(self.registering, ModuleType):
            t = Text(f"Attempted to register module {qname(self.registering)}")
        elif isinstance(self.registering, ProviderType):
            t = Text(f"Attempted to register provider {qname(self.registering)}")
        else:
            raise TypeError()
        t.sentence("after registrations were closed.")
        t.blank()
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to register a module or provider after registrations were closed."


class CannotProvideRawType(Exception):
    def __init__(self, t: type):
        self.type = t


@dataclass(frozen=True)
class ResolutionStep:
    target: BoundResource[Any]
    provider_method: ProviderMethod[Any]
    parameter_name: str
    depends_on: BoundResource[Any]

    @classmethod
    def from_types(
        cls,
        target: Type[Any],
        provider_method: ProviderMethod[Any],
        parameter_name: str,
        depends_on: Type[Any],
    ) -> ResolutionStep:
        return ResolutionStep(
            target=cast(BoundResource[Any], target),
            provider_method=provider_method,
            parameter_name=parameter_name,
            depends_on=cast(ModuleResource[Any], depends_on),
        )

    def __str__(self) -> str:
        m = self.provider_method
        return (
            f"{rname(self.target)} -> "
            f"{m.provider.__name__}.provide_{self.target.name}"
            f"(..., {self.parameter_name}: {rname(self.depends_on)})"
        )


class CircularDependency(HelpfulException):
    def __init__(self, loops: list[list[ResolutionStep]]):
        self.loops = loops

    def explanation(self) -> str:
        t = Text(wrap=False)
        if len(self.loops) == 1:
            t.newline("Circular dependency detected:")
            self.add_loop(t, self.loops[0])
        else:
            t.newline(f"Circular dependencies detected ({len(self.loops)}):")
            for i, loop in enumerate(self.loops):
                t.newline(f"{i + 1}:")
                self.add_loop(t, loop)

        providers = {step.provider_method.provider for step in chain(*self.loops)}
        t.blank()
        t.newline("Providers involved:")
        with t.indented_block(blank_before=False):
            for provider in providers:
                t.newline(f"- {point_to_definition(provider)}")
        return str(t)

    def add_loop(self, t: Text, loop: list[ResolutionStep]) -> None:
        with t.indented_block(blank_before=False):
            for step in loop:
                t.newline(str(step))

    def failsafe_explanation(self) -> str:
        return "Circular dependency detected."


class InvalidProviderInstanceAccess(Exception):
    # internal, see ProviderMethodsCantAccessProviderInstance
    pass


class ProviderMethodsCantAccessProviderInstance(HelpfulException):
    def __init__(
        self,
        resource: BoundResource[Any],
        provider_method: ProviderMethod[Any],
    ):
        self.resource = resource
        self.provider_method = provider_method

    def explanation(self) -> str:
        t = Text("Provider method:")
        with t.indented_block():
            t.newline(f"{sname(self.provider_method.provider)}.provide_{self.resource.name}()")
        t.newline("Attempted to access the provider instance 'self'.")
        t.sentence(
            "Provider methods can only access their parameters, " "but not the provider instance"
        )
        t.blank()
        t.newline(point_to_definition(self.provider_method.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "Provider method attempted to access the provider instance 'self', "
            "which is not allowed."
        )


class RegistrationMustBeClosedBeforeReopeningThem(Exception):
    def __init__(self, container: Container) -> None:
        self.container = container


class ContainerAlreadyReadyForProvisioning(Exception):
    def __init__(self, container: Container):
        self.container = container


class CannotReopenRegistrationsAfterHavingProvidedResources(Exception):
    def __init__(self, container: Container):
        self.container = container


class RegisteredProvidersNotUsed(Exception):
    def __init__(self, providers: set[ProviderType]):
        self.providers = providers


class ProviderNotProvidingForModule(Exception):
    def __init__(self, resource: ProviderResource[Any], provider_in_use: ProviderType):
        self.resource = resource
        self.provider_in_use = provider_in_use
