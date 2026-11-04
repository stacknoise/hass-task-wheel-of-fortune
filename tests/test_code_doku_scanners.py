"""Tests der Scanner, Metriken und Schichtzuordnung des Code-Doku-Generators."""

import pytest

from tools.code_doku import constants as c
from tools.code_doku.layers import is_allowed, layer_of
from tools.code_doku.metrics import (
    code_lines,
    halstead_volume,
    instability,
    maintainability,
    weighted_maintainability,
)
from tools.code_doku.models import Metrics
from tools.code_doku.python_scanner import (
    cyclomatic,
    dotted_name,
    scan_python,
    tokenize_python,
)
from tools.code_doku.ts_scanner import import_candidates, scan_typescript
from tools.code_doku.ts_tokens import match_brackets, tokenize_typescript

PY_SOURCE = '''"""Modul."""
from __future__ import annotations
from .sibling import helper
from . import other

class Box:
    """Behälter."""
    def get(self, key: str) -> int:
        """Holt."""
        if key and key != "x":
            return 1
        return [i for i in range(3) if i][0]

async def run(value: int) -> None:
    for _ in range(value):
        pass
'''

TS_SOURCE = """/** Modul-Doku. */
import { a } from './a.ts';
import './side.js';
const lazy = () => import('./views/index.ts');
export const ratio = (x: number): number => x > 1 ? x / 2 : x;
const re = /ab[/]c/g;

/** Eine Klasse. */
export class Panel extends Base {
  @property({ type: String }) name = '';
  static override properties = { language: { type: String } };

  constructor() {
    super();
  }

  /** Zeichnet. */
  protected override render(): string {
    const text = `x ${a ? `${b}` : ''} y`;
    if (a && b || c) { return text; }
    return text ?? 'none';
  }
}

export interface Shape { size: number }
export function plain(n?: number): number { while (n) { n--; } return 0; }
declare function external(): void;
"""


def test_python_scan_structure() -> None:
    module = scan_python("pkg/mod.py", PY_SOURCE, c.LAYER_DOMAIN)
    assert module.doc == "Modul."
    assert [t.name for t in module.types] == ["Box"]
    method = module.types[0].methods[0]
    assert method.signature == "def get(self, key: str) -> int"
    assert method.metrics.cc == 5  # 1 + if + and + comprehension (for + if)
    assert module.functions[0].signature.startswith("async def run")
    assert "pkg.sibling" in module.imports and "pkg.other" in module.imports
    assert module.metrics.cc == 5 + 2


def test_python_helpers() -> None:
    assert dotted_name("a/b/__init__.py") == "a.b"
    assert dotted_name("a/b.py") == "a.b"
    assert cyclomatic(__import__("ast").parse("x = 1")) == 1
    tokens = tokenize_python("a = 1\n# c\n\nb = 'x'\n")
    assert code_lines(tokens) == 2


def test_typescript_scan_structure() -> None:
    module = scan_typescript("frontend/src/p.ts", TS_SOURCE, c.LAYER_PANEL)
    assert module.doc == "Modul-Doku."
    assert [(t.name, t.kind) for t in module.types] == [
        ("Panel", c.KIND_CLASS),
        ("Shape", c.KIND_INTERFACE),
    ]
    panel = module.types[0]
    assert [m.name for m in panel.methods] == ["constructor", "render"]
    render = panel.methods[1]
    assert render.doc == "Zeichnet."
    assert render.metrics.cc == 1 + 1 + 1 + 1 + 1 + 1  # if, &&, ||, ?, ??
    assert panel.doc == "Eine Klasse."
    names = {f.name: f for f in module.functions}
    assert set(names) == {"lazy", "ratio", "plain"}
    assert names["ratio"].metrics.cc == 2
    assert names["plain"].metrics.cc == 2  # while; optionales `?:` zählt nicht
    assert "frontend/src/a.ts" in module.imports
    assert "frontend/src/side.ts" in module.imports
    assert "frontend/src/views/index.ts" in module.imports


def test_typescript_tokenizer_handles_templates_and_regex() -> None:
    tokens, comments = tokenize_typescript(
        "/** d */ const r = /a`b/; const t = `a${`b${1}`}c`; x / 2;"
    )
    texts = [t.text for t in tokens]
    assert "/a`b/" in texts
    assert "x" in texts and "/" in texts
    assert comments[0].text == "/** d */"
    pairs = match_brackets(tokenize_typescript("f(a[1]) {}")[0])
    assert pairs[1] == 6 and pairs[6] == 1


def test_typescript_unknown_character_and_unclosed() -> None:
    tokens, _ = tokenize_typescript("a \\ b")
    assert [t.text for t in tokens] == ["a", "\\", "b"]
    module = scan_typescript("frontend/src/x.ts", "export class", c.LAYER_PANEL)
    assert module.types == ()


def test_import_candidates() -> None:
    assert import_candidates("fe/src/a/b.ts", "../c.js") == (
        "fe/src/c.js",
        "fe/src/c.ts",
        "fe/src/c.js/index.ts",
    )


def test_metrics() -> None:
    tokens = tokenize_python("a = b + 1\n")
    assert halstead_volume(tokens, c.PY_KEYWORDS) > 0
    assert halstead_volume(tokenize_python("a\n"), c.PY_KEYWORDS) == 0.0
    assert maintainability(0, 0, 0) == c.MI_EMPTY
    assert maintainability(10**12, 500, 5000) == 0.0
    assert 0 < maintainability(100.0, 2, 10) < c.MI_SCALE
    assert instability(0, 0) == 0.0
    assert instability(1, 3) == 0.75


@pytest.mark.parametrize(
    ("path", "layer"),
    [
        ("custom_components/task_wheel/domain/models.py", c.LAYER_DOMAIN),
        ("custom_components/task_wheel/services.py", c.LAYER_API),
        ("custom_components/task_wheel/__init__.py", c.LAYER_ENTRY),
        ("custom_components/task_wheel/runtime.py", c.LAYER_ENTRY),
        ("custom_components/task_wheel/entry_lookup.py", c.LAYER_ENTRY),
        ("custom_components/task_wheel/sensor.py", c.LAYER_ENTRY),
        ("custom_components/task_wheel/infrastructure/panel.py", c.LAYER_INFRA),
        ("frontend/src/views/index.ts", c.LAYER_PANEL),
        ("elsewhere/x.py", c.LAYER_OTHER),
    ],
)
def test_layer_of(path: str, layer: str) -> None:
    assert layer_of(path) == layer


def test_is_allowed() -> None:
    assert is_allowed(c.LAYER_APP, c.LAYER_DOMAIN)
    assert is_allowed(c.LAYER_APP, c.LAYER_APP)
    assert is_allowed(c.LAYER_API, c.LAYER_ENTRY)
    assert is_allowed(c.LAYER_ENTRY, c.LAYER_DOMAIN)
    assert not is_allowed(c.LAYER_DOMAIN, c.LAYER_APP)
    assert not is_allowed("unbekannt", c.LAYER_APP)


def test_weighted_maintainability() -> None:
    assert weighted_maintainability([]) is None
    assert weighted_maintainability([Metrics(0, 1, 50.0)]) is None
    parts = [Metrics(10, 1, 80.0), Metrics(30, 1, 40.0)]
    assert weighted_maintainability(parts) == 50.0


def test_module_mi_is_weighted_over_methods() -> None:
    source = "A = 1\n\n\ndef f(x):\n    return x + 1\n"
    module = scan_python("pkg/m.py", source, c.LAYER_DOMAIN)
    assert module.metrics.mi == module.functions[0].metrics.mi
    assert scan_python("pkg/k.py", "A = 1\n", c.LAYER_CONST).metrics.mi < c.MI_EMPTY


def test_python_properties_and_constants() -> None:
    module = scan_python(
        "m.py",
        "from dataclasses import dataclass\nLIMIT: int = 3\n_hidden = []\n\n"
        "@dataclass(frozen=True)\nclass Point:\n    x: int = 0\n    y: float = 1.5\n",
        "Domain",
    )
    assert [(p.name, p.kind, p.visibility) for p in module.constants] == [
        ("LIMIT", c.PROP_CONST, c.VIS_PUBLIC),
        ("_hidden", c.PROP_FIELD, c.VIS_PRIVATE),
    ]
    point = module.types[0]
    assert [(p.name, p.type, p.access, p.init) for p in point.props] == [
        ("x", "int", c.ACCESS_READONLY, "0"),
        ("y", "float", c.ACCESS_READONLY, "1.5"),
    ]


def test_typescript_properties_and_constants() -> None:
    module = scan_typescript(
        "m.ts",
        "export const A = 1;\nexport const f = (x: number) => x;\n"
        "export interface I { a: string; readonly b?: number; run(): void; }\n"
        "export enum E { X = 'x', Y, Z = 3 }\n"
        "export class K { static s = 3; private readonly p: Map<string, number> = new Map();"
        " go() { return 1; } }\n",
        "Panel",
    )
    assert [p.name for p in module.constants] == ["A"]
    types = {t.name: t for t in module.types}
    assert [(p.name, p.access) for p in types["I"].props] == [
        ("a", c.ACCESS_GET_SET),
        ("b", c.ACCESS_READONLY),
    ]
    assert [p.name for p in types["E"].props] == ["X", "Y", "Z"]
    assert types["E"].props[0].access == "'x'"
    fields = {p.name: p for p in types["K"].props}
    assert fields["s"].static and fields["s"].init == "3"
    assert fields["p"].visibility == "private" and fields["p"].type == "Map<string, number>"
    assert [m.name for m in types["K"].methods] == ["go"]


def test_python_protocol_members_are_abstract() -> None:
    module = scan_python(
        "m.py",
        'class P:\n    def go(self) -> int:\n        """Doc."""\n        ...\n'
        "    def run(self):\n        work()\n    def real(self):\n        return 1\n",
        "Domain",
    )
    assert [(m.name, m.abstract) for m in module.types[0].methods] == [
        ("go", True),
        ("run", False),
        ("real", False),
    ]
