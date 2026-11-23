"""Лексический анализ выражений; каждый токен хранит смещение в исходном тексте."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

MAX_SOURCE_LENGTH = 20_000
MAX_TOKENS = 8192


class TokenKind(Enum):
    VARIABLE = auto()
    NOT = auto()
    AND = auto()
    OR = auto()
    IMPLIES = auto()
    LPAREN = auto()
    RPAREN = auto()
    EOF = auto()


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    lexeme: str
    position: int
    end: int


class FormulaSyntaxError(ValueError):
    """Диагностическое сообщение с исходной позицией, строкой и столбцом."""

    def __init__(self, source: str, position: int, message: str):
        self.source = source
        self.position = max(0, min(position, len(source)))
        self.message = message
        super().__init__(self._build_message())

    @property
    def line(self) -> int:
        return self.source.count("\n", 0, self.position) + 1

    @property
    def column(self) -> int:
        start = self.source.rfind("\n", 0, self.position) + 1
        return self.position - start + 1

    def _build_message(self) -> str:
        start = self.source.rfind("\n", 0, self.position) + 1
        end = self.source.find("\n", self.position)
        if end < 0:
            end = len(self.source)
        snippet = self.source[start:end]
        prefix = snippet[: self.position - start]
        caret_spaces = len(prefix.expandtabs(4))
        return (
            f"{self.message} (строка {self.line}, столбец {self.column})\n"
            f"{snippet.expandtabs(4)}\n{' ' * caret_spaces}^"
        )


_SYMBOLS = {
    "!": TokenKind.NOT, "¬": TokenKind.NOT,
    "&": TokenKind.AND, "∧": TokenKind.AND,
    "|": TokenKind.OR, "∨": TokenKind.OR,
    "→": TokenKind.IMPLIES,
    "(": TokenKind.LPAREN, ")": TokenKind.RPAREN,
}


def tokenize(source: str) -> tuple[Token, ...]:
    """Переменные: буква, затем буквы/десятичные цифры/подчёркивание.

    Допустимы Unicode-буквы; имена регистрозависимы. Символ 'v' -- переменная.
    """
    if not isinstance(source, str):
        raise TypeError("Формула должна быть строкой")
    if len(source) > MAX_SOURCE_LENGTH:
        raise FormulaSyntaxError(source, MAX_SOURCE_LENGTH, f"Формула длиннее {MAX_SOURCE_LENGTH} символов")

    result: list[Token] = []
    offset = 0
    size = len(source)

    while offset < size:
        char = source[offset]
        if char.isspace():
            offset += 1
            continue
        start = offset
        if char.isalpha():
            offset += 1
            while offset < size and (
                source[offset].isalpha() or source[offset].isdecimal() or source[offset] == "_"
            ):
                offset += 1
            result.append(Token(TokenKind.VARIABLE, source[start:offset], start, offset))
        elif source.startswith("->", offset):
            offset += 2
            result.append(Token(TokenKind.IMPLIES, "->", start, offset))
        elif char in _SYMBOLS:
            offset += 1
            result.append(Token(_SYMBOLS[char], char, start, offset))
        else:
            raise FormulaSyntaxError(source, start, f"Недопустимый символ {char!r}")

        if len(result) > MAX_TOKENS:
            raise FormulaSyntaxError(source, start, f"Превышен лимит {MAX_TOKENS} токенов")

    result.append(Token(TokenKind.EOF, "", size, size))
    return tuple(result)
