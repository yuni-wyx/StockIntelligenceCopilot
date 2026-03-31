"""
compat.py — Zero-dependency shim
---------------------------------
Provides minimal stubs for `langchain_core` and `pydantic` so the project
can be imported and validated without running `pip install`.

In production, install the real packages (requirements.txt) and this file
becomes a no-op.

Import this module BEFORE any other project module:
    import compat  # noqa: F401
"""

from __future__ import annotations

import sys
import types
from typing import Any, Callable, Optional


def _already_installed(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


# ── Pydantic stub ─────────────────────────────────────────────────────────────

if not _already_installed("pydantic"):
    import dataclasses
    import json

    _pydantic = types.ModuleType("pydantic")

    class _FieldInfo:
        def __init__(self, default=dataclasses.MISSING, **kwargs):
            self.default = default
            self.metadata = kwargs

    def Field(default=dataclasses.MISSING, default_factory=None, **kwargs):
        fi = _FieldInfo(default, **kwargs)
        if default_factory is not None:
            fi.metadata["default_factory"] = default_factory
        return fi

    class _ModelMeta(type):
        """Metaclass that collects annotated fields and auto-generates __init__."""

        def __new__(mcs, name, bases, namespace, **kwargs):
            annotations = {}
            for base in bases:
                annotations.update(getattr(base, "__annotations__", {}))
            annotations.update(namespace.get("__annotations__", {}))

            defaults = {}
            for k, v in namespace.items():
                if isinstance(v, _FieldInfo):
                    defaults[k] = v  # store the whole FieldInfo
                elif not k.startswith("_") and not callable(v):
                    defaults[k] = v

            namespace["_annotations"] = annotations
            namespace["_defaults"] = defaults

            cls = super().__new__(mcs, name, bases, namespace)

            # Generate __init__
            def __init__(self, **kw):
                for field in annotations:
                    default = defaults.get(field, dataclasses.MISSING)
                    if field in kw:
                        object.__setattr__(self, field, kw[field])
                    elif isinstance(default, _FieldInfo):
                        factory = default.metadata.get("default_factory")
                        if factory is not None:
                            object.__setattr__(self, field, factory())
                        elif default.default is not dataclasses.MISSING:
                            object.__setattr__(self, field, default.default)
                        else:
                            raise TypeError(
                                f"{name}.__init__() missing required field: '{field}'"
                            )
                    elif default is not dataclasses.MISSING:
                        val = default() if callable(default) else default
                        object.__setattr__(self, field, val)
                    else:
                        raise TypeError(
                            f"{name}.__init__() missing required field: '{field}'"
                        )

            cls.__init__ = __init__

            def model_dump(self, exclude=None):
                exclude = exclude or set()
                result = {}
                for k in self._annotations:
                    if k in exclude:
                        continue
                    val = getattr(self, k, None)
                    if hasattr(val, "model_dump"):
                        result[k] = val.model_dump()
                    elif isinstance(val, list):
                        result[k] = [
                            v.model_dump() if hasattr(v, "model_dump") else v for v in val
                        ]
                    else:
                        result[k] = val
                return result

            cls.model_dump = model_dump
            cls.model_config = {}
            return cls

    class BaseModel(metaclass=_ModelMeta):
        pass

    _pydantic.BaseModel = BaseModel
    _pydantic.Field = Field
    sys.modules["pydantic"] = _pydantic


# ── langchain_core stubs ─────────────────────────────────────────────────────

if not _already_installed("langchain_core"):
    # Top-level package
    _lc_core = types.ModuleType("langchain_core")
    sys.modules["langchain_core"] = _lc_core

    # langchain_core.runnables
    _runnables = types.ModuleType("langchain_core.runnables")

    class _ConfiguredRunnable:
        def __init__(self, fn: Callable, run_name: str = ""):
            self._fn = fn
            self._run_name = run_name

        def invoke(self, inp: Any) -> Any:
            return self._fn(inp)

        def with_config(self, **kwargs) -> "_ConfiguredRunnable":
            return _ConfiguredRunnable(self._fn, run_name=kwargs.get("run_name", ""))

        def __or__(self, other: "_ConfiguredRunnable") -> "_ConfiguredRunnable":
            """Support pipe operator: chain1 | chain2"""
            def piped(inp):
                return other.invoke(self.invoke(inp))
            return _ConfiguredRunnable(piped, run_name=f"{self._run_name}|{other._run_name}")

    class RunnableLambda(_ConfiguredRunnable):
        def __init__(self, fn: Callable):
            super().__init__(fn)

        def with_config(self, **kwargs) -> "_ConfiguredRunnable":
            return _ConfiguredRunnable(self._fn, run_name=kwargs.get("run_name", ""))

    _runnables.RunnableLambda = RunnableLambda
    sys.modules["langchain_core.runnables"] = _runnables
    _lc_core.runnables = _runnables


# ── rich stub ─────────────────────────────────────────────────────────────────

if not _already_installed("rich"):
    import textwrap

    _rich = types.ModuleType("rich")
    _console_mod = types.ModuleType("rich.console")
    _panel_mod = types.ModuleType("rich.panel")
    _rule_mod = types.ModuleType("rich.rule")
    _table_mod = types.ModuleType("rich.table")
    _text_mod = types.ModuleType("rich.text")
    _box_mod = types.ModuleType("rich.box")

    # Minimal markup stripper
    import re as _re
    _MARKUP_RE = _re.compile(r"\[/?[^\]]*\]")

    def _strip(s: str) -> str:
        return _MARKUP_RE.sub("", str(s))

    class Console:
        def __init__(self, **kw): pass

        def print(self, *args, **kw):
            parts = " ".join(_strip(str(a)) for a in args)
            print(parts)

        def rule(self, title=""):
            t = _strip(title)
            line = "─" * max(0, (80 - len(t) - 2) // 2)
            print(f"{line} {t} {line}")

    class Panel:
        def __init__(self, content, title="", border_style="", box=None):
            self._content = _strip(content)
            self._title = _strip(title)

        def __rich_console__(self, *a, **k): pass
        def __str__(self):
            return f"┌─ {self._title} ─┐\n  {self._content}\n└{'─'*40}┘"

    class Rule:
        def __init__(self, title=""):
            self._title = _strip(title)
        def __str__(self):
            return f"── {self._title} " + "─" * max(0, 60 - len(self._title))

    class Table:
        def __init__(self, title="", **kw):
            self._title = _strip(title)
            self._cols: list = []
            self._rows: list = []
        def add_column(self, header, **kw): self._cols.append(_strip(header))
        def add_row(self, *cells): self._rows.append([_strip(c) for c in cells])
        def __str__(self):
            lines = [f"  [{self._title}]", "  " + "  |  ".join(self._cols)]
            for r in self._rows:
                lines.append("  " + "  |  ".join(r))
            return "\n".join(lines)

    class Text:
        def __init__(self, text=""): self._t = text
        def __str__(self): return self._t

    # Patch Console.print to handle Panel/Table/Rule objects
    _orig_print = Console.print
    def _smart_print(self, *args, **kw):
        parts = []
        for a in args:
            if isinstance(a, (Panel, Table, Rule)):
                parts.append(str(a))
            else:
                parts.append(_strip(str(a)))
        print("\n".join(parts) if len(parts) > 1 else (parts[0] if parts else ""))
    Console.print = _smart_print

    # Box sentinel
    class _BoxSentinel:
        ROUNDED = "ROUNDED"
        SIMPLE_HEAD = "SIMPLE_HEAD"
    box = _BoxSentinel()

    _console_mod.Console = Console
    _panel_mod.Panel = Panel
    _rule_mod.Rule = Rule
    _table_mod.Table = Table
    _text_mod.Text = Text
    _box_mod.box = box

    _rich.console = _console_mod
    _rich.panel = _panel_mod
    _rich.rule = _rule_mod
    _rich.table = _table_mod
    _rich.text = _text_mod
    _rich.box = box

    sys.modules["rich"] = _rich
    sys.modules["rich.console"] = _console_mod
    sys.modules["rich.panel"] = _panel_mod
    sys.modules["rich.rule"] = _rule_mod
    sys.modules["rich.table"] = _table_mod
    sys.modules["rich.text"] = _text_mod
    sys.modules["rich.box"] = _box_mod
