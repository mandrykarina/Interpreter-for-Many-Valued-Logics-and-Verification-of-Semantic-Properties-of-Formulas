"""Синтаксический анализ формул с явно левой ассоциативностью бинарных связок.

Грамматика (итеративные цепочки операторов соответствуют левому связыванию):

formula     := implication EOF
implication := disjunction (('->' | '→') disjunction)*
disjunction := conjunction (('|' | '∨') conjunction)*
conjunction := unary (('&' | '∧') unary)*
unary       := ('!' | '¬') unary | VARIABLE | '(' implication ')'

Приоритеты: ¬ > ∧ > ∨ > →. Приоритеты -- соглашение интерфейса
этой программы, не дополнительная аксиома из лекций.
"""

from __future__ import annotations

from .ast import Binary, BinaryOperator, Formula, Negation, Variable
from .lexer import FormulaSyntaxError, Token, TokenKind, tokenize

MAX_NESTING = 128
MAX_AST_NODES = 4096


class _Parser:
    def __init__(self, source: str):
        self.source = source
        self.tokens = tokenize(source)
        self.index = 0
        self.node_count = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def _consume(self, expected: TokenKind) -> Token:
        token = self.current
        if token.kind != expected:
            if expected == TokenKind.RPAREN:
                message = "Ожидалась закрывающая скобка ')'"
            else:
                message = f"Ожидался токен {expected.name}"
            raise FormulaSyntaxError(self.source, token.position, message)
        self.index += 1
        return token

    def _new(self, node: Formula) -> Formula:
        self.node_count += 1
        if self.node_count > MAX_AST_NODES:
            raise FormulaSyntaxError(
                self.source, self.current.position,
                f"Формула содержит более {MAX_AST_NODES} узлов AST",
            )
        return node

    def parse(self) -> Formula:
        if self.current.kind == TokenKind.EOF:
            raise FormulaSyntaxError(self.source, 0, "Пустая формула")
        formula = self._implication(0)
        if self.current.kind != TokenKind.EOF:
            if self.current.kind == TokenKind.RPAREN:
                problem = "Лишняя закрывающая скобка ')'"
            else:
                problem = "Лишние символы после окончания формулы; возможно, пропущена операция"
            raise FormulaSyntaxError(self.source, self.current.position, problem)
        return formula

    def _implication(self, nesting: int) -> Formula:
        left = self._disjunction(nesting)
        while self.current.kind == TokenKind.IMPLIES:
            self.index += 1
            right = self._disjunction(nesting)
            left = self._new(Binary(BinaryOperator.IMPLIES, left, right))
        return left

    def _disjunction(self, nesting: int) -> Formula:
        left = self._conjunction(nesting)
        while self.current.kind == TokenKind.OR:
            self.index += 1
            right = self._conjunction(nesting)
            left = self._new(Binary(BinaryOperator.OR, left, right))
        return left

    def _conjunction(self, nesting: int) -> Formula:
        left = self._unary(nesting)
        while self.current.kind == TokenKind.AND:
            self.index += 1
            right = self._unary(nesting)
            left = self._new(Binary(BinaryOperator.AND, left, right))
        return left

    def _unary(self, nesting: int) -> Formula:
        token = self.current
        if token.kind == TokenKind.VARIABLE:
            self.index += 1
            return self._new(Variable(token.lexeme))

        if token.kind in (TokenKind.NOT, TokenKind.LPAREN):
            if nesting >= MAX_NESTING:
                raise FormulaSyntaxError(
                    self.source, token.position,
                    f"Превышена допустимая глубина скобок/отрицаний ({MAX_NESTING})",
                )
            self.index += 1
            if token.kind == TokenKind.NOT:
                return self._new(Negation(self._unary(nesting + 1)))
            value = self._implication(nesting + 1)
            self._consume(TokenKind.RPAREN)
            return value

        if token.kind == TokenKind.EOF:
            reason = "Ожидалась переменная или подформула, но строка закончилась"
        elif token.kind == TokenKind.RPAREN:
            reason = "Неожиданная закрывающая скобка или пустые скобки"
        else:
            reason = f"Ожидалась переменная, отрицание или '(', получено {token.lexeme!r}"
        raise FormulaSyntaxError(self.source, token.position, reason)


def parse_formula(source: str) -> Formula:
    """Разобрать формулу; ошибки ввода сообщаются через FormulaSyntaxError."""
    return _Parser(source).parse()
