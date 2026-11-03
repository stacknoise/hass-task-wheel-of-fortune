"""Scanner für Python-Quelltext auf Basis von `ast` und `tokenize`."""

from __future__ import annotations

import ast
import io
import tokenize
from typing import TYPE_CHECKING

from .constants import (
    DOT,
    EMPTY,
    INIT_FILE,
    KIND_CLASS,
    KIND_FUNCTION,
    KIND_METHOD,
    KIND_NAME,
    KIND_NUMBER,
    KIND_OP,
    KIND_STRING,
    LANG_PYTHON,
    PY_ASYNC_PREFIX,
    PY_KEYWORDS,
    PY_RETURN_ARROW,
    SUFFIX_PYTHON,
)
from .models import ModuleInfo, Token
from .segments import Source, module_metrics

if TYPE_CHECKING:
    from .models import MethodInfo, TypeInfo

BRANCH_NODES = (
    ast.If,
    ast.IfExp,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.ExceptHandler,
    ast.match_case,
)
FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
TOKEN_KINDS = {
    tokenize.NAME: KIND_NAME,
    tokenize.NUMBER: KIND_NUMBER,
    tokenize.STRING: KIND_STRING,
    tokenize.OP: KIND_OP,
}


def dotted_name(path: str) -> str:
    """Wandelt einen Dateipfad in den Python-Modulnamen um (`__init__.py` ⇒ Paket)."""
    parts = path.removesuffix(SUFFIX_PYTHON).split("/")
    if path.endswith(INIT_FILE):
        parts = parts[:-1]
    return DOT.join(parts)


def tokenize_python(text: str) -> list[Token]:
    """Zerlegt Python-Quelltext in Token (ohne Kommentare und Zeilenumbrüche)."""
    line_offsets = [0]
    for line in text.splitlines(keepends=True):
        line_offsets.append(line_offsets[-1] + len(line))
    tokens: list[Token] = []
    for item in tokenize.generate_tokens(io.StringIO(text).readline):
        kind = TOKEN_KINDS.get(item.type)
        if kind is None:
            continue
        (start_row, start_col), (end_row, end_col) = item.start, item.end
        tokens.append(
            Token(
                kind=kind,
                text=item.string,
                line=start_row,
                end_line=end_row,
                start=line_offsets[start_row - 1] + start_col,
                end=line_offsets[end_row - 1] + end_col,
            )
        )
    return tokens


def cyclomatic(node: ast.AST) -> int:
    """Zyklomatische Komplexität (McCabe) eines AST-Knotens."""
    return 1 + sum(_branches(child) for child in ast.walk(node))


def _branches(node: ast.AST) -> int:
    """Zusätzliche Pfade, die ein einzelner Knoten eröffnet."""
    if isinstance(node, BRANCH_NODES):
        return 1
    if isinstance(node, ast.BoolOp):
        return len(node.values) - 1
    if isinstance(node, ast.comprehension):
        return 1 + len(node.ifs)
    return 0


def _bounds(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> tuple[int, int]:
    """Zeilenbereich inklusive Dekoratoren."""
    first = min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)])
    return first, node.end_lineno or node.lineno


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Signatur als Text: `[async ]def name(args)[ -> ret]`."""
    prefix = PY_ASYNC_PREFIX if isinstance(node, ast.AsyncFunctionDef) else EMPTY
    returns = f"{PY_RETURN_ARROW}{ast.unparse(node.returns)}" if node.returns else EMPTY
    return f"{prefix}def {node.name}({ast.unparse(node.args)}){returns}"


def _function(
    source: Source, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str
) -> MethodInfo:
    """Baut die `MethodInfo` einer Funktion oder Methode."""
    return source.method(
        node.name,
        kind,
        _signature(node),
        ast.get_docstring(node) or EMPTY,
        _bounds(node),
        cyclomatic(node),
    )


def _class(source: Source, node: ast.ClassDef) -> TypeInfo:
    """Baut die `TypeInfo` einer Klasse samt Methoden."""
    methods = tuple(
        _function(source, child, KIND_METHOD)
        for child in node.body
        if isinstance(child, FUNCTION_NODES)
    )
    return source.type_info(
        node.name, KIND_CLASS, ast.get_docstring(node) or EMPTY, _bounds(node), methods
    )


def _resolve_from(module: str, level: int, own: str, is_package: bool) -> str:
    """Löst einen relativen `from`-Import in einen absoluten Namen auf."""
    if not level:
        return module
    package = own.split(DOT)
    if not is_package:
        package = package[:-1]
    base = package[: len(package) - (level - 1)]
    return DOT.join([*base, module] if module else base)


def collect_imports(tree: ast.AST, path: str) -> tuple[str, ...]:
    """Sammelt Kandidaten für importierte Module (absolute Namen, mit und ohne Untermodul)."""
    own = dotted_name(path)
    is_package = path.endswith(INIT_FILE)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_from(node.module or EMPTY, node.level, own, is_package)
            found.add(base)
            found.update(f"{base}{DOT}{alias.name}" for alias in node.names)
    return tuple(sorted(found))


def scan_python(path: str, text: str, layer: str) -> ModuleInfo:
    """Analysiert eine Python-Datei. Wirft `SyntaxError` bei ungültigem Quelltext."""
    tree = ast.parse(text, filename=path)
    tokens = tokenize_python(text)
    source = Source(text, tokens, PY_KEYWORDS)
    types = tuple(_class(source, node) for node in tree.body if isinstance(node, ast.ClassDef))
    functions = tuple(
        _function(source, node, KIND_FUNCTION)
        for node in tree.body
        if isinstance(node, FUNCTION_NODES)
    )
    methods = [*functions, *(m for t in types for m in t.methods)]
    return ModuleInfo(
        path=path,
        language=LANG_PYTHON,
        layer=layer,
        doc=ast.get_docstring(tree) or EMPTY,
        metrics=module_metrics(tokens, methods, PY_KEYWORDS),
        types=types,
        functions=functions,
        imports=collect_imports(tree, path),
    )
