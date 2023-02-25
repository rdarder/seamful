import inspect
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from textwrap import wrap
from typing import Optional, Any, Iterator

import wiring


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
        with self.indented_block():
            self.newline(content)

    @contextmanager
    def indented_block(self) -> Iterator[None]:
        self._flush_paragraph()
        self._indent += 4
        yield
        self._flush_paragraph()
        self._indent -= 4

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
    root_filename = inspect.getsourcefile(wiring)
    module_filename = inspect.getsourcefile(value)
    if root_filename is None or module_filename is None:
        return None
    root = Path(root_filename).parent.parent
    path = Path(module_filename)
    relative = path.relative_to(root)
    lineno = inspect.getsourcelines(value)[1]
    return f"{relative}:{lineno}"


def point_to_definition(value: type) -> Optional[str]:
    definition = location(value)
    return f"See {definition}" if definition is not None else None
