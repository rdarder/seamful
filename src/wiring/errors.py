import inspect
import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from textwrap import wrap
from typing import Optional, Any, Iterator, TYPE_CHECKING

if TYPE_CHECKING:
    from wiring.resource import ResourceTypes


class Text:
    def __init__(self, title: str):
        self._lines: list[str] = []
        self._current_paragraph: list[str] = []
        self._add_blank = False
        self._indent = 0
        self.newline(title)

    def sentence(self, content: str) -> None:
        self._current_paragraph.append(content)

    def newline(self, content: Optional[str] = None) -> None:
        self._flush_paragraph()
        if content is None:
            self._add_blank = True
        else:
            self.sentence(content)

    def blank(self) -> None:
        self._flush_paragraph()
        self._add_blank = True

    def _flush_paragraph(self) -> None:
        if self._add_blank:
            self._lines.append("")
            self._add_blank = False
        wrapped = wrap(" ".join(self._current_paragraph), 80 - self._indent)
        self._lines.extend([" " * self._indent + line for line in wrapped])
        self._current_paragraph = []

    def indented_line(self, content: str) -> None:
        with self.indented_block(blank_before=False, blank_after=False):
            self.newline(content)

    @contextmanager
    def indented_block(self, blank_before: bool = True, blank_after: bool = True) -> Iterator[None]:
        if blank_before:
            self.blank()
        self._flush_paragraph()
        self._indent += 4
        yield
        self._flush_paragraph()
        self._indent -= 4
        if blank_after:
            self.blank()

    def __str__(self) -> str:
        self._add_blank = False
        self._flush_paragraph()
        return "\n".join(self._lines)


class HelpfulException(Exception, ABC):
    def __str__(self) -> str:
        message: str
        try:
            message = self.explanation()
        except Exception:
            message = self.failsafe_explanation()

        if message[-1] == "\n":
            return message
        else:
            return message + "\n"

    @abstractmethod
    def explanation(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def failsafe_explanation(self) -> str:
        raise NotImplementedError()


def qname(value: Any) -> str:
    return f"'{sname(value)}'"


def rdef(resource: "ResourceTypes[Any]") -> str:
    from wiring.resource import ModuleResource, OverridingResource, PrivateResource

    if isinstance(resource, ModuleResource):
        return f"{sname(resource.module)}.{resource.name} = Resource({sname(resource.type)})"
    elif isinstance(resource, OverridingResource):
        return (
            f"{sname(resource.provider)}.{resource.name} = "
            f"Resource({sname(resource.type)}, ResourceKind.OVERRIDE)"
        )
    elif isinstance(resource, PrivateResource):
        return (
            f"{sname(resource.provider)}.{resource.name} = "
            f"Resource({sname(resource.type)}, ResourceKind.PRIVATE)"
        )
    else:
        raise TypeError()


def sname(value: type) -> str:
    if isinstance(value, type):
        return value.__name__
    else:
        return repr(value)


def fname(value: Any) -> str:
    if isinstance(value, type):
        return f"{value.__module__}.{sname(value)}"
    else:
        return str(value)


def location(value: type) -> Optional[str]:
    root = Path(os.getcwd())
    module_filename = inspect.getsourcefile(value)
    if root is None or module_filename is None:
        return None
    path = Path(module_filename)
    relative = path.relative_to(root)
    lineno = inspect.getsourcelines(value)[1]
    return f"{relative}:{lineno}"


def point_to_definition(value: type) -> Optional[str]:
    definition = location(value)
    return f"{sname(value)}: {definition}" if definition is not None else None
