"""Tests von Abhängigkeiten, Schwellwerten, Prüfung, Ausgabe und Kommandozeile."""

# ruff: noqa: RUF001
import hashlib
import json
from pathlib import Path

import pytest

from tools.code_doku import constants as c
from tools.code_doku.check import find_violations
from tools.code_doku.cli import run
from tools.code_doku.project import ScanError, build_report
from tools.code_doku.render import TemplateError, render, to_json, verify_template
from tools.code_doku.schema import build_schema
from tools.code_doku.thresholds import Threshold, load_thresholds, parse_thresholds

DOC = """# Doku
### 1.1 Schwellwerte

| Messgröße | grün | gelb | rot |
|---|---|---|---|
| CC je Methode | ≤ 1 | 2 | > 2 |
| MI je Modul | ≥ 55 | 35–54 | < 35 |
| Instabilität Domäne | ≤ 0,3 | 0,31–0,5 | > 0,5 |
| Duplikate | 0 | – | > 0 |
| Unbekannt | ≤ 1 | – | > 2 |
"""


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    pkg = c.SRC_PYTHON
    write(tmp_path, f"{pkg}/manifest.json", json.dumps({"version": "1.2.3"}))
    write(tmp_path, f"{pkg}/__init__.py", "")
    write(tmp_path, f"{pkg}/const/__init__.py", "NAME = 'x'\n")
    write(
        tmp_path,
        f"{pkg}/domain/models.py",
        "from ..const import NAME\nfrom ..application import svc\n\nclass Model:\n"
        "    def go(self, a):\n        if a:\n            if a > 1:\n                return NAME\n"
        "        return 0\n",
    )
    write(
        tmp_path,
        f"{pkg}/application/svc.py",
        "from ..domain.models import Model\n\nclass Svc(Model):\n    pass\n",
    )
    write(tmp_path, f"{pkg}/application/__init__.py", "")
    write(
        tmp_path,
        "frontend/src/a.ts",
        "import { b } from './b.ts';\nexport class A { run() { return b; } }\n",
    )
    write(tmp_path, "frontend/src/b.ts", "export const b = 1;\n")
    write(tmp_path, "frontend/src/a.test.ts", "import { A } from './a.ts';\nnew A();\n")
    write(
        tmp_path,
        "tests/test_x.py",
        "from custom_components.task_wheel.domain.models import Model\nModel()\n",
    )
    write(tmp_path, "docs/CODE_DOKU.md", DOC)
    template = (
        f"<title>{c.PLACEHOLDER_TITLE}</title><script>{c.PLACEHOLDER_DATA}</script>"
        f"<script>{c.PLACEHOLDER_FILES}</script>"
    )
    write(tmp_path, "docs/code-doku/template.html", template)
    digest = hashlib.sha256(template.encode("utf-8")).hexdigest()
    write(tmp_path, "docs/code-doku/template.sha256", f"{digest}  template.html\n")
    return tmp_path


def test_parse_thresholds() -> None:
    rules = {t.scope: t for t in parse_thresholds(DOC)}
    assert set(rules) == {c.SCOPE_METHOD_CC, c.SCOPE_MODULE_MI, c.SCOPE_DOMAIN_INSTABILITY}
    assert rules[c.SCOPE_DOMAIN_INSTABILITY].green == 0.3
    assert parse_thresholds("keine Tabelle") == ()


def test_threshold_status() -> None:
    cc = Threshold("s", c.DIRECTION_MAX, 5, 8)
    assert [cc.status(v) for v in (5, 6, 9)] == [c.STATUS_GREEN, c.STATUS_YELLOW, c.STATUS_RED]
    mi = Threshold("s", c.DIRECTION_MIN, 55, 35)
    assert [mi.status(v) for v in (60, 40, 10)] == [c.STATUS_GREEN, c.STATUS_YELLOW, c.STATUS_RED]


def test_real_doc_has_all_scopes() -> None:
    rules = load_thresholds(Path(c.DEFAULT_DOC))
    assert {t.scope for t in rules} == set(c.THRESHOLD_LABELS.values())


def test_build_report(project: Path) -> None:
    report = build_report(project)
    assert report.version == "1.2.3"
    by_path = {m.path: m for m in report.modules}
    models = by_path[f"{c.SRC_PYTHON}/domain/models.py"]
    assert models.tested and models.types[0].tested
    assert set(models.deps) == {
        f"{c.SRC_PYTHON}/const/__init__.py",
        f"{c.SRC_PYTHON}/application/svc.py",
    }
    assert models.types[0].methods[0].metrics.cc == 3
    svc = by_path[f"{c.SRC_PYTHON}/application/svc.py"]
    assert svc.types[0].uses == ("Model",) and svc.types[0].ce == 1
    assert models.types[0].ca == 1
    disallowed = {(e.source, e.target) for e in report.edges if not e.allowed}
    assert (models.path, svc.path) in disallowed
    assert by_path["frontend/src/a.ts"].tested
    assert by_path["frontend/src/a.ts"].deps == ("frontend/src/b.ts",)
    assert {layer["id"] for layer in report.layers} >= {c.LAYER_DOMAIN, c.LAYER_PANEL}


def test_report_without_manifest(tmp_path: Path) -> None:
    assert build_report(tmp_path).version == c.UNKNOWN_VERSION


def test_syntax_error_is_reported(project: Path) -> None:
    write(project, f"{c.SRC_PYTHON}/broken.py", "def (:\n")
    with pytest.raises(ScanError):
        build_report(project)


def test_json_escapes_markup() -> None:
    text = to_json({"doc": "</script><b>"})
    assert "</" not in text
    assert json.loads(text.replace("<\\/", "</")) == {"doc": "</script><b>"}


def test_schema_types_props_and_dependencies(project: Path) -> None:
    write(
        project,
        f"{c.SRC_PYTHON}/domain/enums.py",
        "from enum import Enum\n\nclass Color(Enum):\n    RED = 1\n    BLUE = 2\n",
    )
    write(
        project,
        f"{c.SRC_PYTHON}/domain/util.py",
        "LIMIT: int = 3\n\ndef helper():\n    return LIMIT\n",
    )
    document, files = build_schema(project, build_report(project))
    by_name = {item.name: item for item in document.types}
    assert document.schema == c.SCHEMA_VERSION and document.meta.tests
    assert by_name["Color"].kind == c.KIND_ENUM
    assert [p.n for p in by_name["Color"].props] == ["RED", "BLUE"]
    assert by_name["util"].static and by_name["util"].props[0].kind == c.PROP_CONST
    assert [m.n for m in by_name["util"].meths] == ["helper"]
    assert by_name["Svc"].deps == [by_name["Model"].id]
    assert by_name["Model"].ca == 1 and by_name["Svc"].ce == 1
    assert by_name["Model"].file in files and by_name["Model"].id.startswith("Domain|")
    assert document.meta.layers[0] == c.LAYER_CONST
    assert document.projdeps[c.LAYER_APP] == [c.LAYER_DOMAIN]


def test_template_must_match_checksum(project: Path) -> None:
    template = project / "docs/code-doku/template.html"
    assert verify_template(template).startswith("<title>")
    template.write_text("<b>geändert</b>", encoding="utf-8")
    with pytest.raises(TemplateError):
        render(template, project / "out.html", build_report(project), project)
    assert run(["--root", str(project)], project) == c.EXIT_ERROR


def test_cli_writes_and_checks(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = ["--root", str(project), "--check"]
    assert run(args, project) == c.EXIT_VIOLATIONS  # CC 3 > 2 und Instabilität 0,67 > 0,5
    err = capsys.readouterr().err
    assert "method.cc" in err and "domain.instability" in err
    html = (project / c.DEFAULT_OUTPUT).read_text(encoding="utf-8")
    assert "1.2.3" in html and c.PLACEHOLDER_DATA not in html
    assert run(["--root", str(project)], project) == c.EXIT_OK


def test_cli_ok_and_errors(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(
        project,
        "docs/CODE_DOKU.md",
        DOC.replace("≤ 1", "≤ 5").replace("> 2", "> 8").replace("> 0,5", "> 1"),
    )
    assert run(["--root", str(project), "--check"], project) == c.EXIT_OK
    assert c.MSG_CHECK_OK in capsys.readouterr().out
    write(project, "docs/CODE_DOKU.md", "leer")
    assert run(["--root", str(project), "--check"], project) == c.EXIT_ERROR
    (project / "docs/CODE_DOKU.md").unlink()
    assert run(["--root", str(project)], project) == c.EXIT_ERROR


def test_factories_are_exempt_from_instability(project: Path) -> None:
    pkg = c.SRC_PYTHON
    write(
        project,
        f"{pkg}/domain/thing_factory.py",
        "from .models import Model\nfrom ..const import NAME\n",
    )
    write(project, f"{pkg}/domain/user.py", "from .thing_factory import Model\n")
    report = build_report(project)
    factory = next(m for m in report.modules if m.path.endswith("thing_factory.py"))
    assert factory.ca and factory.instability > 0.5
    findings = find_violations(report, load_thresholds(project / c.DEFAULT_DOC))
    assert all("thing_factory" not in f.location for f in findings)
