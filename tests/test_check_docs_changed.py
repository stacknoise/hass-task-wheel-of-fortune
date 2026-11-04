"""Tests der Code-Doku-Prüfung."""

from tools import check_docs_changed as check


def test_base_ref_from_pull_request() -> None:
    assert check.base_ref({check.ENV_BASE_REF: "main"}) == "origin/main"


def test_base_ref_fallback() -> None:
    assert check.base_ref({}) == check.FALLBACK_BASE


def test_missing_docs_detected() -> None:
    assert check.docs_missing(["custom_components/task_wheel/__init__.py"])
    assert check.docs_missing(["frontend/src/a.ts"])


def test_docs_present_or_no_code() -> None:
    assert not check.docs_missing(["custom_components/x.py", check.DOC_FILE])
    assert not check.docs_missing(["README.md"])


def test_tools_e2e_and_pipeline_count_as_code() -> None:
    for name in ("tools/x.py", "e2e/tests/flow.spec.ts", ".github/workflows/release.yml"):
        assert check.docs_missing([name])
    assert not check.docs_missing(["e2e/package-lock.json", ".github/CODEOWNERS"])


def test_touching_the_file_is_not_enough() -> None:
    files = ["custom_components/x.py", check.DOC_FILE]
    assert check.docs_missing(files, ["+Text ohne Tabelle"])
    assert not check.docs_missing(files, ["+| 2026-11-04 | 0.5.0 | AP | m | c | - |"])
    assert not check.docs_missing(["README.md"], [])
    assert not check.has_new_row(["+| `modul.py` | App | x | - | - |"])


def test_changed_files_and_main(monkeypatch) -> None:
    monkeypatch.delenv(check.ENV_ACTOR, raising=False)
    monkeypatch.setattr(check, "doc_diff", lambda base: [])
    monkeypatch.setattr(check, "changed_files", lambda base: ["README.md"])
    assert check.main() == check.EXIT_OK
    monkeypatch.setattr(check, "changed_files", lambda base: ["frontend/src/a.ts"])
    assert check.main() == check.EXIT_FAIL
    monkeypatch.setattr(check, "doc_diff", lambda base: ["+| 2026-11-04 | 0.5.0 | a | b | c | d |"])
    assert check.main() == check.EXIT_OK


def test_dependency_bot_is_exempt(monkeypatch) -> None:
    monkeypatch.setenv(check.ENV_ACTOR, "dependabot[bot]")
    monkeypatch.setattr(check, "changed_files", lambda base: ["frontend/src/a.ts"])
    assert check.main() == check.EXIT_OK


def test_changed_files_calls_git(monkeypatch) -> None:
    class Result:
        stdout = "a\nb\n"

    monkeypatch.setattr(check.subprocess, "run", lambda *args, **kwargs: Result())
    assert check.changed_files("HEAD~1") == ["a", "b"]
    assert check.doc_diff("HEAD~1") == ["a", "b"]
