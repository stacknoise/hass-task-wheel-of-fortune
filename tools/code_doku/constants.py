"""Konstanten des Code-Doku-Generators. Keine Logik."""

from __future__ import annotations

import keyword
import re
from typing import Final

ENCODING: Final = "utf-8"
NEWLINE: Final = "\n"
SPACE: Final = " "
EMPTY: Final = ""
DOT: Final = "."
SLASH: Final = "/"

# --- Sprachen und Dateien ---
LANG_PYTHON: Final = "python"
LANG_TYPESCRIPT: Final = "typescript"
SUFFIX_PYTHON: Final = ".py"
SUFFIX_TS: Final = ".ts"
SUFFIX_TS_TEST: Final = ".test.ts"
SUFFIX_JS: Final = ".js"
INIT_FILE: Final = "__init__.py"
INDEX_FILE: Final = "index.ts"
SRC_PYTHON: Final = "custom_components/task_wheel"
SRC_TS: Final = "frontend/src"
TESTS_PYTHON: Final = "tests"
MANIFEST_PATH: Final = "custom_components/task_wheel/manifest.json"
MANIFEST_VERSION_KEY: Final = "version"
UNKNOWN_VERSION: Final = "unbekannt"
DEFAULT_OUTPUT: Final = "docs/code-doku/index.html"
DEFAULT_TEMPLATE: Final = "docs/code-doku/template.html"
DEFAULT_DOC: Final = "docs/CODE_DOKU.md"
TEMPLATE_HASH_FILE: Final = "template.sha256"
SCHEMA_VERSION: Final = 2
PRODUCT_NAME: Final = "Task Wheel"
PLACEHOLDER_TITLE: Final = "__TITLE__"
PLACEHOLDER_DATA: Final = '{"__DATA__":1}'
PLACEHOLDER_FILES: Final = '{"__FILES__":1}'
JSON_CLOSE_ESCAPE: Final = "<\\/"
JSON_CLOSE: Final = "</"

# --- Schichten (CODE_DOKU.md §2) ---
LAYER_CONST: Final = "Const"
LAYER_ENTRY: Final = "Entry"
LAYER_API: Final = "Api"
LAYER_APP: Final = "App"
LAYER_DOMAIN: Final = "Domain"
LAYER_INFRA: Final = "Infra"
LAYER_PANEL: Final = "Panel"
LAYER_OTHER: Final = "Other"
LAYER_ORDER: Final = (
    (LAYER_ENTRY, "1 Einstieg"),
    (LAYER_API, "2 Schnittstellen"),
    (LAYER_APP, "3 Anwendung"),
    (LAYER_DOMAIN, "4 Domäne"),
    (LAYER_INFRA, "5 Infrastruktur"),
    (LAYER_CONST, "0 Konstanten"),
    (LAYER_PANEL, "Frontend"),
    (LAYER_OTHER, "Sonstiges"),
)
_PKG: Final = f"{SRC_PYTHON}/"
# Reihenfolge zählt: erste passende Vorsilbe gewinnt.
LAYER_RULES: Final = (
    (f"{_PKG}const/", LAYER_CONST),
    (f"{_PKG}domain/", LAYER_DOMAIN),
    (f"{_PKG}application/", LAYER_APP),
    (f"{_PKG}infrastructure/", LAYER_INFRA),
    (f"{_PKG}websocket/", LAYER_API),
    (f"{_PKG}entities/", LAYER_API),
    (f"{_PKG}services.py", LAYER_API),
    (f"{_PKG}__init__.py", LAYER_ENTRY),
    (f"{_PKG}config_flow.py", LAYER_ENTRY),
    (f"{_PKG}runtime.py", LAYER_ENTRY),
    (f"{_PKG}entry_lookup.py", LAYER_ENTRY),
    (f"{_PKG}sensor.py", LAYER_ENTRY),
    (f"{_PKG}todo.py", LAYER_ENTRY),
    (f"{_PKG}button.py", LAYER_ENTRY),
    (f"{SRC_TS}/", LAYER_PANEL),
)
LAYER_ALLOWED: Final = {
    LAYER_ENTRY: frozenset({LAYER_API, LAYER_APP, LAYER_DOMAIN, LAYER_INFRA, LAYER_CONST}),
    LAYER_API: frozenset({LAYER_ENTRY, LAYER_APP, LAYER_DOMAIN, LAYER_CONST}),
    LAYER_APP: frozenset({LAYER_DOMAIN, LAYER_CONST}),
    LAYER_DOMAIN: frozenset({LAYER_CONST}),
    LAYER_INFRA: frozenset({LAYER_DOMAIN, LAYER_APP, LAYER_CONST}),
    LAYER_CONST: frozenset(),
    LAYER_PANEL: frozenset(),
    LAYER_OTHER: frozenset(),
}

# --- Messgrößen (CODE_DOKU.md §1) ---
MI_OFFSET: Final = 171.0
MI_VOLUME_WEIGHT: Final = 5.2
MI_CC_WEIGHT: Final = 0.23
MI_LOC_WEIGHT: Final = 16.2
MI_SCALE: Final = 100.0
MI_EMPTY: Final = 100.0
MI_DIGITS: Final = 1
INSTABILITY_DIGITS: Final = 2
MIN_VOCABULARY: Final = 2
BASE_COMPLEXITY: Final = 1

# --- Python-Scanner ---
PY_KEYWORDS: Final = frozenset(keyword.kwlist) | frozenset(keyword.softkwlist)
KIND_NAME: Final = "NAME"
KIND_NUMBER: Final = "NUMBER"
KIND_STRING: Final = "STRING"
KIND_OP: Final = "OP"
KIND_CLASS: Final = "class"
KIND_INTERFACE: Final = "interface"
KIND_ENUM: Final = "enum"
KIND_FUNCTION: Final = "function"
KIND_METHOD: Final = "method"
PY_ASYNC_PREFIX: Final = "async "
PY_PRIVATE_PREFIX: Final = "_"
PY_ABSTRACT_DECORATOR: Final = "abstractmethod"
PY_DUNDER: Final = "__"
PY_ENUM_MARKER: Final = "Enum"
PY_FLAG_MARKER: Final = "Flag"
PY_FINAL_MARKER: Final = "Final"
PY_CLASSVAR_MARKER: Final = "ClassVar"
PY_FROZEN_MARKER: Final = "frozen=True"
PY_NAMEDTUPLE_MARKER: Final = "NamedTuple"
PROP_PROPERTY: Final = "property"
PROP_FIELD: Final = "field"
PROP_CONST: Final = "const"
PROP_ENUM: Final = "enum"
ACCESS_GET_SET: Final = "get; set"
ACCESS_READONLY: Final = "readonly"
VIS_PUBLIC: Final = "public"
VIS_PRIVATE: Final = "private"
INIT_MAX_LENGTH: Final = 60
ELLIPSIS: Final = "…"
PY_RETURN_ARROW: Final = " -> "

# --- TypeScript-Scanner ---
TS_KEYWORDS: Final = frozenset(
    [
        "abstract",
        "any",
        "as",
        "async",
        "await",
        "boolean",
        "break",
        "case",
        "catch",
        "class",
        "const",
        "constructor",
        "continue",
        "debugger",
        "declare",
        "default",
        "delete",
        "do",
        "else",
        "enum",
        "export",
        "extends",
        "false",
        "finally",
        "for",
        "from",
        "function",
        "get",
        "if",
        "implements",
        "import",
        "in",
        "infer",
        "instanceof",
        "interface",
        "is",
        "keyof",
        "let",
        "namespace",
        "never",
        "new",
        "null",
        "number",
        "of",
        "override",
        "private",
        "protected",
        "public",
        "readonly",
        "return",
        "satisfies",
        "set",
        "static",
        "string",
        "super",
        "switch",
        "this",
        "throw",
        "true",
        "try",
        "type",
        "typeof",
        "undefined",
        "unique",
        "unknown",
        "var",
        "void",
        "while",
        "with",
        "yield",
    ]
)
TS_OP_PATTERN: Final = (
    r">>>=|\.\.\.|===|!==|\*\*=|<<=|>>=|>>>|&&=|\|\|=|\?\?=|=>|==|!=|<=|>=|&&|\|\||\?\?|\?\."
    r"|\+\+|--|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<|>>|\*\*|[{}()\[\];,<>=+\-*/%&|^!~?:.@]"
)
TS_TOKEN_REGEX: Final = re.compile(
    r"(?P<ws>\s+)"
    r"|(?P<line>//[^\n]*)"
    r"|(?P<block>/\*.*?\*/)"
    r"|(?P<string>'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\")"
    r"|(?P<template>`)"
    r"|(?P<number>\d[\w.]*)"
    r"|(?P<name>\#?[A-Za-z_$][\w$]*)"
    rf"|(?P<op>{TS_OP_PATTERN})",
    re.DOTALL,
)
TS_REGEX_LITERAL: Final = re.compile(r"/(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^/\\\[\n])+/[a-z]*")
TS_TEMPLATE_CHUNK: Final = re.compile(r"(?:\\.|[^`\\$]|\$(?!\{))*", re.DOTALL)
TS_TEMPLATE_QUOTE: Final = "`"
TS_TEMPLATE_OPEN: Final = "${"
GROUP_WS: Final = "ws"
GROUP_LINE: Final = "line"
GROUP_BLOCK: Final = "block"
GROUP_STRING: Final = "string"
GROUP_TEMPLATE: Final = "template"
GROUP_NUMBER: Final = "number"
GROUP_NAME: Final = "name"
JSDOC_START: Final = "/**"
JSDOC_STRIP: Final = re.compile(r"^\s*(?:/\*\*|\*/|\*)?\s?", re.MULTILINE)
REGEX_PRECEDERS: Final = frozenset("(,=:[!&|?{};") | {"return", "=>", "&&", "||", "??"}
OPEN_BRACKETS: Final = {"(": ")", "[": "]", "{": "}"}
CLOSE_BRACKETS: Final = frozenset(OPEN_BRACKETS.values())
TOK_BRACE_OPEN: Final = "{"
TOK_BRACE_CLOSE: Final = "}"
TOK_PAREN_OPEN: Final = "("
TOK_SEMICOLON: Final = ";"
TOK_ASSIGN: Final = "="
TOK_ARROW: Final = "=>"
TOK_AT: Final = "@"
TOK_DOT: Final = "."
TOK_COLON: Final = ":"
TS_DECL_MODIFIERS: Final = frozenset({"export", "default", "declare", "abstract"})
TS_MEMBER_MODIFIERS: Final = frozenset(
    [
        "static",
        "async",
        "public",
        "private",
        "protected",
        "override",
        "readonly",
        "get",
        "set",
        "abstract",
        "declare",
        "accessor",
    ]
)
TS_TYPE_KEYWORDS: Final = {"class": KIND_CLASS, "interface": KIND_INTERFACE, "enum": KIND_ENUM}
TS_VARIABLE_KEYWORDS: Final = frozenset({"const", "let", "var"})
TS_PROPERTY_FOLLOWERS: Final = frozenset({":", "?", "=", ";", ",", "!"})
TS_VISIBILITIES: Final = frozenset({"public", "private", "protected"})
TS_READONLY: Final = "readonly"
TS_STATIC: Final = "static"
TOK_COLON_TEXT: Final = ":"
TOK_COMMA: Final = ","
TS_CONST: Final = "const"
TS_STATEMENT_END_PREFIX: Final = frozenset(";})]")
TS_NOT_MEMBER_NAMES: Final = frozenset({"if", "for", "while", "switch", "catch", "return", "new"})
TS_IMPORT_KEYWORD: Final = "import"
TS_FROM_KEYWORD: Final = "from"
TS_RELATIVE_PREFIX: Final = "."
TS_BRANCH_WORDS: Final = frozenset({"if", "for", "while", "case", "catch"})
TS_BRANCH_OPS: Final = frozenset({"&&", "||", "??"})
TS_TERNARY: Final = "?"
TS_TERNARY_NOT_BEFORE: Final = frozenset({":", ")", ",", "="})

# --- Kopplung ---
DEPTH_NONE: Final = 0

# --- Schwellwerte (CODE_DOKU.md §1.1) ---
THRESHOLD_ROW_PREFIX: Final = "|"
THRESHOLD_SECTION: Final = "### 1.1 Schwellwerte"
SCOPE_METHOD_CC: Final = "method.cc"
SCOPE_METHOD_LOC: Final = "method.loc"
SCOPE_MODULE_MI: Final = "module.mi"
SCOPE_MODULE_LOC: Final = "module.loc"
SCOPE_DOMAIN_INSTABILITY: Final = "domain.instability"
THRESHOLD_LABELS: Final = {
    "CC je Methode": SCOPE_METHOD_CC,
    "LOC je Methode": SCOPE_METHOD_LOC,
    "MI je Modul": SCOPE_MODULE_MI,
    "LOC je Modul": SCOPE_MODULE_LOC,
    "Instabilität Domäne": SCOPE_DOMAIN_INSTABILITY,
}
THRESHOLD_CELL: Final = re.compile(r"^\s*([≤≥<>])\s*(\d+(?:,\d+)?)")
OP_MAX: Final = "≤"
OP_MIN: Final = "≥"
DIRECTION_MAX: Final = "max"
DIRECTION_MIN: Final = "min"
CELL_SEPARATOR: Final = "|"
COLUMN_LABEL: Final = 0
COLUMN_GREEN: Final = 1
COLUMN_RED: Final = 3
THRESHOLD_COLUMNS: Final = 4
DECIMAL_COMMA: Final = ","
STATUS_GREEN: Final = "green"
STATUS_YELLOW: Final = "yellow"
STATUS_RED: Final = "red"

# --- Ausgabe ---
EXIT_OK: Final = 0
EXIT_VIOLATIONS: Final = 1
EXIT_ERROR: Final = 2
MSG_WRITTEN: Final = (
    "Code-Doku geschrieben: {path} ({types} Typen, {methods} Methoden, "
    "{props} Properties/Felder, {files} Dateien)"
)
MSG_CHECK_OK: Final = "Schwellwerte eingehalten."
MSG_VIOLATION: Final = "{location}: {scope} = {value} überschreitet den Grenzwert {limit}"
MSG_ERROR: Final = "Fehler: {error}"
MSG_NO_THRESHOLDS: Final = "Keine Schwellwerte in {path} gefunden."

# --- weitere Token-Texte ---
TOK_FUNCTION: Final = "function"
TOK_ASYNC: Final = "async"
TOK_BRACKETS_OPEN: Final = "([{"
TS_MODULE_DOC_MAX_LINE: Final = 2

FACTORY_MARKER: Final = "factory"

# --- Schema 2 (Leitfaden) ---
KIND_CTOR: Final = "ctor"
CTOR_NAMES: Final = frozenset({"__init__", "constructor"})
DOC_PARAGRAPH_BREAK: Final = "\n\n"
STEM_FILES: Final = frozenset({"__init__", "index"})
NAMESPACE_ROOTS: Final = (SRC_PYTHON + "/", SRC_TS + "/")
LAYER_INNER_TO_OUTER: Final = (
    LAYER_CONST,
    LAYER_DOMAIN,
    LAYER_APP,
    LAYER_INFRA,
    LAYER_API,
    LAYER_ENTRY,
    LAYER_PANEL,
    LAYER_OTHER,
)
DUPLICATE_MARK: Final = "#"
ID_SEPARATOR: Final = "|"
MI_ROUND_DIGITS: Final = 0
