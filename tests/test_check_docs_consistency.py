"""Tests der Dokumentationsprüfung (Versionen, Modultabelle, Protokollreihenfolge)."""

from pathlib import Path

from tools import check_docs_consistency as check

DOC = """\
## 3. Modulübersicht

| Modul | Schicht | Verantwortung | Nutzt | Test |
|---|---|---|---|---|
| `a.py` | App | x | - | - |
| `sub/` | App | y | - | - |

### 3.1 Extern

| Paket | Version |
|---|---|
| lit | 3 |

## 4. Änderungsprotokoll

| Datum | Version | AP | Module | Änderung | Metriken |
|---|---|---|---|---|---|
| 2026-11-04 | 0.2.0 | x | m | c | - |
| 2026-11-03 | 0.1.0 | x | m | c | - |
"""
DASH = "\N{EN DASH}"


def log_row(date: str, version: str) -> list[str]:
    return [date, version, "", "", "", ""]


def test_section_rows_skip_headers_and_subsections() -> None:
    assert [row[0] for row in check.section_rows(DOC, check.SECTION_MODULES)] == [
        "`a.py`",
        "`sub/`",
    ]
    assert len(check.section_rows(DOC, check.SECTION_LOG)) == 2


def test_repository_docs_are_consistent() -> None:
    assert check.problems_of(check.ROOT) == []


def test_log_order_and_versions() -> None:
    assert check.log_problems(check.section_rows(DOC, check.SECTION_LOG)) == []
    wrong_date = [log_row("2026-11-03", "0.1.0"), log_row("2026-11-04", "0.1.0")]
    assert "neueste oben" in check.log_problems(wrong_date)[0]
    wrong_version = [log_row("2026-11-04", "0.1.0"), log_row("2026-11-04", "0.2.0")]
    assert "höher" in check.log_problems(wrong_version)[0]
    dash = [log_row("2026-11-04", DASH), log_row("2026-11-03", "0.1.0")]
    assert check.log_problems(dash) == []


def test_log_shape() -> None:
    assert "Spalten" in check.log_problems([["2026-11-04", "0.1.0"]])[0]
    assert "kein Datum" in check.log_problems([log_row("heute", "0.1.0")])[0]
    assert "weder" in check.log_problems([log_row("2026-11-04", "v1")])[0]


def test_module_table_rejects_log_rows() -> None:
    row = ["2026-11-04", "0.4.0", "x", "`m.py`", "y", "z"]
    assert check.module_table_problems([row])
    assert not check.module_table_problems(check.section_rows(DOC, check.SECTION_MODULES))


def test_missing_and_stale_modules(tmp_path: Path) -> None:
    paths = {"a.py", "sub/"}
    assert check.missing_modules(["a.py", "sub/x.py", "b.py"], paths) == ["b.py"]
    package = tmp_path / check.PACKAGE
    package.mkdir(parents=True)
    (package / "a.py").write_text("", encoding="utf-8")
    assert check.stale_modules(tmp_path, {"a.py", "gone.py", "frontend/src/x/"}) == ["gone.py"]


def test_version_problems() -> None:
    manifest = f"{check.PACKAGE}/manifest.json"
    assert check.version_problems({manifest: "1.0.0", "x": "1.0.0"}) == []
    assert "0.9.0" in check.version_problems({manifest: "1.0.0", "x": "0.9.0"})[0]


def test_package_files_skip_subpackage_inits() -> None:
    files = check.package_files(check.ROOT)
    assert "runtime.py" in files
    assert "__init__.py" in files
    assert "domain/__init__.py" not in files


def test_main_reports_success(capsys) -> None:
    assert check.main() == check.EXIT_OK
    assert check.MESSAGE_OK in capsys.readouterr().out
