"""Scanner für TypeScript: Typen, Methoden, Funktionen, Importe, Komplexität (Token-basiert)."""

from __future__ import annotations

import posixpath
import re
from typing import TYPE_CHECKING

from .constants import (
    BASE_COMPLEXITY,
    EMPTY,
    INDEX_FILE,
    KIND_CLASS,
    KIND_FUNCTION,
    KIND_METHOD,
    KIND_NAME,
    KIND_OP,
    KIND_STRING,
    LANG_TYPESCRIPT,
    SLASH,
    SPACE,
    SUFFIX_JS,
    SUFFIX_TS,
    TOK_ARROW,
    TOK_ASSIGN,
    TOK_ASYNC,
    TOK_AT,
    TOK_BRACE_OPEN,
    TOK_BRACKETS_OPEN,
    TOK_DOT,
    TOK_FUNCTION,
    TOK_PAREN_OPEN,
    TOK_SEMICOLON,
    TS_BRANCH_OPS,
    TS_BRANCH_WORDS,
    TS_DECL_MODIFIERS,
    TS_FROM_KEYWORD,
    TS_IMPORT_KEYWORD,
    TS_KEYWORDS,
    TS_MEMBER_MODIFIERS,
    TS_MODULE_DOC_MAX_LINE,
    TS_NOT_MEMBER_NAMES,
    TS_RELATIVE_PREFIX,
    TS_STATEMENT_END_PREFIX,
    TS_TERNARY,
    TS_TERNARY_NOT_BEFORE,
    TS_TYPE_KEYWORDS,
    TS_VARIABLE_KEYWORDS,
)
from .models import ModuleInfo
from .segments import Source, module_metrics
from .ts_tokens import Comment, match_brackets, tokenize_typescript

if TYPE_CHECKING:
    from .models import MethodInfo, Token, TypeInfo

WHITESPACE = re.compile(r"\s+")
DOC_SUFFIX = "*/"
DOC_PREFIX = re.compile(r"^\s*(?:/\*\*|\*/|\*)?[ \t]?", re.MULTILINE)
QUOTES = "'\"`"


def cyclomatic_tokens(tokens: list[Token]) -> int:
    """Zyklomatische Komplexität eines Token-Abschnitts."""
    return BASE_COMPLEXITY + sum(
        _is_branch(token, following)
        for token, following in zip(tokens, [*tokens[1:], None], strict=True)
    )


def _is_branch(token: Token, following: Token | None) -> bool:
    """Wahr, wenn das Token einen zusätzlichen Pfad eröffnet."""
    if token.kind == KIND_NAME:
        return token.text in TS_BRANCH_WORDS
    if token.kind != KIND_OP:
        return False
    if token.text in TS_BRANCH_OPS:
        return True
    return token.text == TS_TERNARY and (
        following is None or following.text not in TS_TERNARY_NOT_BEFORE
    )


class _Analyzer:
    """Findet Deklarationen anhand von Token-Mustern und Klammerpaaren."""

    def __init__(self, path: str, text: str) -> None:
        self.path = path
        self.tokens, self.comments = tokenize_typescript(text)
        self.pairs = match_brackets(self.tokens)
        self.source = Source(text, self.tokens, TS_KEYWORDS)
        self.types: list[TypeInfo] = []
        self.functions: list[MethodInfo] = []

    # --- Hilfen -------------------------------------------------------------------------------
    def _doc(self, line: int) -> str:
        """JSDoc, das in der Zeile unmittelbar vor `line` endet."""
        for comment in self.comments:
            if comment.end_line == line - 1:
                return _clean_doc(comment)
        return EMPTY

    def _skip(self, index: int) -> int:
        """Springt hinter eine Klammergruppe, sonst um ein Token weiter."""
        return (
            self.pairs.get(index, index) + 1
            if self.tokens[index].text in TOK_BRACKETS_OPEN
            else index + 1
        )

    def _first_before(self, index: int, wanted: set[str] | frozenset[str], stop: int) -> int | None:
        """Index des ersten Tokens ab `index` mit Text aus `wanted` (Klammern übersprungen)."""
        while index < stop:
            if self.tokens[index].kind == KIND_OP and self.tokens[index].text in wanted:
                return index
            index = self._skip(index)
        return None

    def _signature(self, first: int, last: int) -> str:
        """Quelltext von Token `first` bis vor Token `last`, Leerraum zusammengefasst."""
        text = self.source_text[self.tokens[first].start : self.tokens[last].start]
        return WHITESPACE.sub(SPACE, text).strip()

    def _emit_method(self, name: str, kind: str, span: tuple[int, int, int]) -> MethodInfo:
        """Baut eine `MethodInfo` aus Start-, Körperbeginn- und Endindex."""
        first, body, last = span
        bounds = (self.tokens[first].line, self.tokens[last].end_line)
        cc = cyclomatic_tokens(self.tokens[body : last + 1])
        return self.source.method(
            name, kind, self._signature(first, body), self._doc(bounds[0]), bounds, cc
        )

    # --- Mitglieder einer Klasse ----------------------------------------------------------------
    def _is_member_start(self, index: int, opener: int) -> bool:
        """Wahr, wenn vor dem Namen eine Anweisungsgrenze oder ein Modifikator steht."""
        token, previous = self.tokens[index], self.tokens[index - 1]
        if index - 1 == opener or previous.text in TS_MEMBER_MODIFIERS:
            return True
        if previous.text in (TOK_DOT, TOK_AT) or token.text in TS_NOT_MEMBER_NAMES:
            return False
        return previous.text in TS_STATEMENT_END_PREFIX or (
            previous.end_line < token.line and previous.kind != KIND_OP
        )

    def _member(self, index: int, opener: int, closer: int) -> tuple[MethodInfo | None, int]:
        """Liefert die Methode, die an `index` beginnt (falls vorhanden), und den nächsten Index."""
        token = self.tokens[index]
        follows = self.tokens[index + 1] if index + 1 < closer else None
        if (
            token.kind != KIND_NAME
            or follows is None
            or follows.text != TOK_PAREN_OPEN
            or not self._is_member_start(index, opener)
        ):
            return None, self._skip(index)
        params_end = self.pairs.get(index + 1, closer)
        body = self._first_before(
            params_end + 1, {TOK_BRACE_OPEN, TOK_SEMICOLON, TOK_ASSIGN}, closer
        )
        if body is None or self.tokens[body].text != TOK_BRACE_OPEN or body not in self.pairs:
            return None, params_end + 1
        first = index
        while first - 1 > opener and self.tokens[first - 1].text in TS_MEMBER_MODIFIERS:
            first -= 1
        last = self.pairs[body]
        return self._emit_method(token.text, KIND_METHOD, (first, body, last)), last + 1

    def _members(self, opener: int, closer: int) -> tuple[MethodInfo, ...]:
        methods: list[MethodInfo] = []
        index = opener + 1
        while index < closer:
            method, index = self._member(index, opener, closer)
            if method:
                methods.append(method)
        return tuple(methods)

    # --- Deklarationen auf oberster Ebene ---------------------------------------------------------
    def _declaration(self, index: int, end: int) -> int:
        """Verarbeitet eine Deklaration ab `index` und liefert den Index dahinter."""
        first = index
        while index < end - 1 and self.tokens[index].text in TS_DECL_MODIFIERS | {TOK_ASYNC}:
            index += 1
        token = self.tokens[index]
        if token.text in TS_TYPE_KEYWORDS and index + 1 < end:
            return self._type(first, index, end)
        if token.text == TOK_FUNCTION and index + 1 < end:
            return self._function(first, index + 1, end)
        if token.text in TS_VARIABLE_KEYWORDS and index + 1 < end:
            return self._variable_function(first, index + 1, end)
        return self._skip(first if index == first else index)

    def _type(self, first: int, keyword: int, end: int) -> int:
        name = self.tokens[keyword + 1]
        opener = self._first_before(keyword + 2, {TOK_BRACE_OPEN}, end)
        if opener is None or opener not in self.pairs:
            return keyword + 1
        closer = self.pairs[opener]
        kind = TS_TYPE_KEYWORDS[self.tokens[keyword].text]
        bounds = (self.tokens[first].line, self.tokens[closer].end_line)
        methods = self._members(opener, closer) if kind == KIND_CLASS else ()
        self.types.append(
            self.source.type_info(name.text, kind, self._doc(bounds[0]), bounds, methods)
        )
        return closer + 1

    def _function(self, first: int, name_index: int, end: int) -> int:
        name = self.tokens[name_index]
        params = self._first_before(name_index + 1, {TOK_PAREN_OPEN}, end)
        if params is None or params not in self.pairs:
            return name_index + 1
        body = self._first_before(self.pairs[params] + 1, {TOK_BRACE_OPEN, TOK_SEMICOLON}, end)
        if body is None or self.tokens[body].text != TOK_BRACE_OPEN or body not in self.pairs:
            return self.pairs[params] + 1
        last = self.pairs[body]
        self.functions.append(self._emit_method(name.text, KIND_FUNCTION, (first, body, last)))
        return last + 1

    def _variable_function(self, first: int, name_index: int, end: int) -> int:
        """`const name = (…) => { … }` bzw. `= function`: als Funktion erfassen."""
        assign = name_index + 1
        if assign + 1 >= end or self.tokens[assign].text != TOK_ASSIGN:
            return self._skip(name_index)
        after = assign + 1
        if self.tokens[after].text == TOK_ASYNC:
            after += 1
        if self.tokens[after].text != TOK_PAREN_OPEN or after not in self.pairs:
            return self._skip(name_index)
        arrow = self._first_before(self.pairs[after] + 1, {TOK_ARROW, TOK_SEMICOLON}, end)
        if arrow is None or self.tokens[arrow].text != TOK_ARROW:
            return self.pairs[after] + 1
        body = arrow + 1
        last = (
            self.pairs[body]
            if self.tokens[body].text == TOK_BRACE_OPEN and body in self.pairs
            else (self._first_before(body, {TOK_SEMICOLON}, end) or end - 1)
        )
        name = self.tokens[name_index].text
        self.functions.append(
            self._emit_method(name, KIND_FUNCTION, (first, arrow, min(last, end - 1)))
        )
        return last + 1

    def run(self) -> None:
        """Durchläuft die oberste Ebene der Datei."""
        index = 0
        while index < len(self.tokens):
            index = self._declaration(index, len(self.tokens))

    @property
    def source_text(self) -> str:
        """Gesamter Quelltext."""
        return "\n".join(self.source.lines)

    # --- Importe ---------------------------------------------------------------------------------
    def imports(self) -> tuple[str, ...]:
        """Kandidaten-Pfade der relativen Importe (`from '…'`, `import '…'`, `import('…')`)."""
        found: set[str] = set()
        for index, token in enumerate(self.tokens[:-1]):
            specifier = self._specifier(index, token)
            if specifier and specifier.startswith(TS_RELATIVE_PREFIX):
                found.update(import_candidates(self.path, specifier))
        return tuple(sorted(found))

    def _specifier(self, index: int, token: Token) -> str | None:
        """Textwert des Modulbezeichners, falls an `index` ein Import beginnt."""
        following = self.tokens[index + 1]
        if token.text not in (TS_FROM_KEYWORD, TS_IMPORT_KEYWORD):
            return None
        candidate = following
        if (
            token.text == TS_IMPORT_KEYWORD
            and following.text == TOK_PAREN_OPEN
            and index + 2 < len(self.tokens)
        ):
            candidate = self.tokens[index + 2]
        return candidate.text.strip(QUOTES) if candidate.kind == KIND_STRING else None


def _clean_doc(comment: Comment) -> str:
    """Entfernt Kommentar-Rahmen und Sternchen aus einem JSDoc-Block."""
    return DOC_PREFIX.sub(EMPTY, comment.text).removesuffix(DOC_SUFFIX).strip()


def import_candidates(path: str, specifier: str) -> tuple[str, ...]:
    """Mögliche Zieldateien eines relativen Imports (mit/ohne Endung, als Verzeichnis-Index)."""
    target = posixpath.normpath(posixpath.join(posixpath.dirname(path), specifier))
    stem = target.removesuffix(SUFFIX_JS)
    return (target, f"{stem}{SUFFIX_TS}", f"{target}{SLASH}{INDEX_FILE}")


def scan_typescript(path: str, text: str, layer: str) -> ModuleInfo:
    """Analysiert eine TypeScript-Datei."""
    analyzer = _Analyzer(path, text)
    analyzer.run()
    methods = [*analyzer.functions, *(m for t in analyzer.types for m in t.methods)]
    head = [c for c in analyzer.comments if c.end_line <= TS_MODULE_DOC_MAX_LINE]
    return ModuleInfo(
        path=path,
        language=LANG_TYPESCRIPT,
        layer=layer,
        doc=_clean_doc(head[0]) if head else EMPTY,
        metrics=module_metrics(analyzer.tokens, methods, TS_KEYWORDS),
        types=tuple(analyzer.types),
        functions=tuple(analyzer.functions),
        imports=analyzer.imports(),
    )
