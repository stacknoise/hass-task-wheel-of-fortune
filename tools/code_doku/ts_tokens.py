"""Lexer für TypeScript: Token, JSDoc-Kommentare und Klammerpaare."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

from .constants import (
    CLOSE_BRACKETS,
    GROUP_BLOCK,
    GROUP_LINE,
    GROUP_NAME,
    GROUP_NUMBER,
    GROUP_STRING,
    GROUP_TEMPLATE,
    GROUP_WS,
    JSDOC_START,
    KIND_NAME,
    KIND_NUMBER,
    KIND_OP,
    KIND_STRING,
    NEWLINE,
    OPEN_BRACKETS,
    REGEX_PRECEDERS,
    TOK_BRACE_CLOSE,
    TOK_BRACE_OPEN,
    TS_REGEX_LITERAL,
    TS_TEMPLATE_CHUNK,
    TS_TEMPLATE_OPEN,
    TS_TEMPLATE_QUOTE,
    TS_TOKEN_REGEX,
)
from .models import Token

GROUP_KINDS = {GROUP_STRING: KIND_STRING, GROUP_NUMBER: KIND_NUMBER, GROUP_NAME: KIND_NAME}
SLASH_OP = "/"


@dataclass(frozen=True, slots=True)
class Comment:
    """JSDoc-Kommentar mit der Zeile, in der er endet."""

    end_line: int
    text: str


class _Lexer:
    """Zeichenweiser Scanner; Vorlagen-Literale (`${…}`) werden rekursiv gelesen."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.tokens: list[Token] = []
        self.comments: list[Comment] = []
        self._line_starts = [0]
        for index, char in enumerate(text):
            if char == NEWLINE:
                self._line_starts.append(index + 1)

    def line_of(self, offset: int) -> int:
        """1-basierte Zeilennummer eines Zeichen-Offsets."""
        return bisect_right(self._line_starts, offset)

    def _emit(self, kind: str, start: int, end: int) -> None:
        self.tokens.append(
            Token(
                kind, self.text[start:end], self.line_of(start), self.line_of(end - 1), start, end
            )
        )

    def _regex_allowed(self) -> bool:
        if not self.tokens:
            return True
        return self.tokens[-1].text in REGEX_PRECEDERS

    def _template(self) -> None:
        """Liest ein Vorlagen-Literal ab dem öffnenden Hochkomma."""
        self.pos += 1
        while True:
            chunk = TS_TEMPLATE_CHUNK.match(self.text, self.pos)
            end = chunk.end() if chunk else self.pos
            if end > self.pos:
                self._emit(KIND_STRING, self.pos, end)
            self.pos = end
            if self.text.startswith(TS_TEMPLATE_OPEN, self.pos):
                self.pos += len(TS_TEMPLATE_OPEN)
                self.scan(nested=True)
                continue
            self.pos += len(TS_TEMPLATE_QUOTE)
            return

    def _comment(self, group: str, start: int, end: int) -> None:
        if group == GROUP_BLOCK and self.text.startswith(JSDOC_START, start):
            self.comments.append(Comment(self.line_of(end - 1), self.text[start:end]))

    def scan(self, *, nested: bool = False) -> None:
        """Liest Code bis zum Ende; verschachtelt bis zur schließenden `}` des `${`."""
        depth = 0
        while self.pos < len(self.text):
            match = TS_TOKEN_REGEX.match(self.text, self.pos)
            if match is None:
                self._emit(KIND_OP, self.pos, self.pos + 1)
                self.pos += 1
                continue
            group, start, end = match.lastgroup or GROUP_WS, match.start(), match.end()
            if group == GROUP_TEMPLATE:
                self._template()
                continue
            if group in (GROUP_WS, GROUP_LINE, GROUP_BLOCK):
                self._comment(group, start, end)
            elif group in GROUP_KINDS:
                self._emit(GROUP_KINDS[group], start, end)
            elif match.group() == SLASH_OP and self._regex_allowed():
                regex = TS_REGEX_LITERAL.match(self.text, start)
                end = regex.end() if regex else end
                self._emit(KIND_STRING if regex else KIND_OP, start, end)
            else:
                if nested and match.group() == TOK_BRACE_CLOSE and depth == 0:
                    self.pos = end
                    return
                depth += (match.group() == TOK_BRACE_OPEN) - (match.group() == TOK_BRACE_CLOSE)
                self._emit(KIND_OP, start, end)
            self.pos = end


def tokenize_typescript(text: str) -> tuple[list[Token], list[Comment]]:
    """Zerlegt TypeScript in Token und sammelt JSDoc-Kommentare."""
    lexer = _Lexer(text)
    lexer.scan()
    return lexer.tokens, lexer.comments


def match_brackets(tokens: list[Token]) -> dict[int, int]:
    """Ordnet jeder Klammer (Index) ihre Gegenklammer zu, in beide Richtungen."""
    pairs: dict[int, int] = {}
    stack: list[int] = []
    for index, token in enumerate(tokens):
        if token.kind != KIND_OP:
            continue
        if token.text in OPEN_BRACKETS:
            stack.append(index)
        elif token.text in CLOSE_BRACKETS and stack:
            opener = stack.pop()
            pairs[opener], pairs[index] = index, opener
    return pairs
