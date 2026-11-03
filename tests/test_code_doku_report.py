"""Tests von Abhängigkeiten, Schwellwerten, Prüfung, Ausgabe und Kommandozeile."""

# ruff: noqa: RUF001
import json
from pathlib import Path

import pytest

from tools.code_doku import constants as c
from tools.code_doku.check import find_violations
from tools.code_doku.cli import run
from tools.code_doku.project import ScanError, build_report
from tools.code_doku.render import to_json
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
    write(tmp_path, "docs/code-doku/template.html", f"<script>{c.DATA_PLACEHOLDER}</script>")
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


def test_json_escapes_markup(project: Path) -> None:
    write(project, f"{c.SRC_PYTHON}/domain/doc.py", '"""</script><b>"""\n')
    text = to_json(build_report(project), ())
    assert "<" not in text
    assert json.loads(text.replace("\\u003c", "<"))["modules"]


def test_cli_writes_and_checks(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = ["--root", str(project), "--check"]
    assert run(args, project) == c.EXIT_VIOLATIONS  # CC 3 > 2 und Instabilität 0,67 > 0,5
    err = capsys.readouterr().err
    assert "method.cc" in err and "domain.instability" in err
    html = (project / c.DEFAULT_OUTPUT).read_text(encoding="utf-8")
    assert "1.2.3" in html and c.DATA_PLACEHOLDER not in html
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
