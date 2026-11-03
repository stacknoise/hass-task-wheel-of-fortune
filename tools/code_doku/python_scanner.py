"""Scanner für Python-Quelltext auf Basis von `ast` und `tokenize`."""

from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import replace
from typing import TYPE_CHECKING

from .constants import (
    ACCESS_GET_SET,
    ACCESS_READONLY,
    DOT,
    ELLIPSIS,
    EMPTY,
    INIT_FILE,
    INIT_MAX_LENGTH,
    KIND_CLASS,
    KIND_FUNCTION,
    KIND_METHOD,
    KIND_NAME,
    KIND_NUMBER,
    KIND_OP,
    KIND_STRING,
    LANG_PYTHON,
    PROP_CONST,
    PROP_ENUM,
    PROP_FIELD,
    PROP_PROPERTY,
    PY_ABSTRACT_DECORATOR,
    PY_ASYNC_PREFIX,
    PY_CLASSVAR_MARKER,
    PY_DUNDER,
    PY_ENUM_MARKER,
    PY_FINAL_MARKER,
    PY_FLAG_MARKER,
    PY_FROZEN_MARKER,
    PY_KEYWORDS,
    PY_NAMEDTUPLE_MARKER,
    PY_PRIVATE_PREFIX,
    PY_RETURN_ARROW,
    SUFFIX_PYTHON,
    VIS_PRIVATE,
    VIS_PUBLIC,
)
from .models import ModuleInfo, PropertyInfo, Token
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


def _is_abstract(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Wahr ohne Rumpf: `@abstractmethod` oder nur Docstring und `...` (Protokoll-Member)."""
    if any(PY_ABSTRACT_DECORATOR in ast.unparse(item) for item in node.decorator_list):
        return True
    body = [
        item
        for item in node.body
        if not (isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant))
        or item.value.value is Ellipsis
    ]
    return (
        len(body) == 1 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
    )


def _function(
    source: Source, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str
) -> MethodInfo:
    """Baut die `MethodInfo` einer Funktion oder Methode."""
    method = source.method(
        node.name,
        kind,
        _signature(node),
        ast.get_docstring(node) or EMPTY,
        _bounds(node),
        cyclomatic(node),
    )
    return replace(method, abstract=_is_abstract(node))


def _declaration(node: ast.stmt) -> tuple[str, str, str] | None:
    """Name, Typ und Initialwert einer Zuweisung an einen einfachen Namen."""
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        value = ast.unparse(node.value) if node.value else EMPTY
        return node.target.id, ast.unparse(node.annotation), value
    if (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    ):
        return node.targets[0].id, EMPTY, ast.unparse(node.value)
    return None


def _shorten(text: str) -> str:
    """Kürzt einen Initialwert auf `INIT_MAX_LENGTH` Zeichen."""
    flat = " ".join(text.split())
    return flat if len(flat) <= INIT_MAX_LENGTH else f"{flat[: INIT_MAX_LENGTH - 1]}{ELLIPSIS}"


def _member_kind(name: str, annotation: str, *, enum: bool) -> str:
    """Art der Eigenschaft: Aufzählungswert, Konstante, Feld oder Eigenschaft."""
    if enum:
        return PROP_ENUM
    if annotation.startswith(PY_FINAL_MARKER) or name.isupper():
        return PROP_CONST
    if annotation and not annotation.startswith(PY_CLASSVAR_MARKER):
        return PROP_PROPERTY
    return PROP_FIELD


def _access(kind: str, value: str, *, readonly: bool) -> str:
    """Zugriff laut Leitfaden: Wert bei Aufzählungen, `readonly` bei Konstanten/gesperrten Typen."""
    if kind == PROP_ENUM:
        return _shorten(value)
    if kind == PROP_CONST or (kind == PROP_PROPERTY and readonly):
        return ACCESS_READONLY
    return ACCESS_GET_SET if kind == PROP_PROPERTY else EMPTY


def _properties(
    body: list[ast.stmt], *, enum: bool = False, readonly: bool = False
) -> tuple[PropertyInfo, ...]:
    """Eigenschaften, Felder, Konstanten und Aufzählungswerte einer Anweisungsliste."""
    found: list[PropertyInfo] = []
    for node in body:
        declared = _declaration(node)
        if declared is None or (
            declared[0].startswith(PY_DUNDER) and declared[0].endswith(PY_DUNDER)
        ):
            continue
        name, annotation, value = declared
        kind = _member_kind(name, annotation, enum=enum)
        found.append(
            PropertyInfo(
                name=name,
                kind=kind,
                type=EMPTY if annotation == PY_FINAL_MARKER else annotation,
                access=_access(kind, value, readonly=readonly),
                init=EMPTY if kind == PROP_ENUM else _shorten(value),
                visibility=VIS_PRIVATE if name.startswith(PY_PRIVATE_PREFIX) else VIS_PUBLIC,
                static=annotation.startswith(PY_CLASSVAR_MARKER),
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
            )
        )
    return tuple(found)


def _is_enum(bases: tuple[str, ...]) -> bool:
    """Wahr, wenn eine Basisklasse eine Aufzählung (`Enum`, `StrEnum`, `Flag`) ist."""
    return any(base.rsplit(DOT, 1)[-1].endswith((PY_ENUM_MARKER, PY_FLAG_MARKER)) for base in bases)


def _is_readonly(node: ast.ClassDef, bases: tuple[str, ...]) -> bool:
    """Wahr bei eingefrorenen Datenklassen und `NamedTuple`."""
    return PY_NAMEDTUPLE_MARKER in bases or any(
        PY_FROZEN_MARKER in ast.unparse(decorator) for decorator in node.decorator_list
    )


def _class(source: Source, node: ast.ClassDef) -> TypeInfo:
    """Baut die `TypeInfo` einer Klasse samt Methoden und Eigenschaften."""
    methods = tuple(
        _function(source, child, KIND_METHOD)
        for child in node.body
        if isinstance(child, FUNCTION_NODES)
    )
    bases = tuple(ast.unparse(base) for base in node.bases)
    info = source.type_info(
        node.name, KIND_CLASS, ast.get_docstring(node) or EMPTY, _bounds(node), methods
    )
    props = _properties(node.body, enum=_is_enum(bases), readonly=_is_readonly(node, bases))
    return replace(info, props=props, bases=bases)


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
        constants=_properties(tree.body),
        refs=source.names_between(1, len(source.lines)),
        imports=collect_imports(tree, path),
    )
