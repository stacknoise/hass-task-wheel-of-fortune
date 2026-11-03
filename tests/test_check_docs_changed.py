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


def test_changed_files_and_main(monkeypatch) -> None:
    monkeypatch.setattr(check, "changed_files", lambda base: ["README.md"])
    assert check.main() == check.EXIT_OK
    monkeypatch.setattr(check, "changed_files", lambda base: ["frontend/src/a.ts"])
    assert check.main() == check.EXIT_FAIL


def test_changed_files_calls_git(monkeypatch) -> None:
    class Result:
        stdout = "a\nb\n"

    monkeypatch.setattr(check.subprocess, "run", lambda *args, **kwargs: Result())
    assert check.changed_files("HEAD~1") == ["a", "b"]
