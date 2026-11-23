"""Структурное представление пропозициональных формул."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Union


class BinaryOperator(str, Enum):
    AND = "∧"
    OR = "∨"
    IMPLIES = "→"


@dataclass(frozen=True, slots=True)
class Variable:
    name: str


@dataclass(frozen=True, slots=True)
class Negation:
    operand: Formula


@dataclass(frozen=True, slots=True)
class Binary:
    operator: BinaryOperator
    left: Formula
    right: Formula


Formula = Union[Variable, Negation, Binary]


def collect_variables(formula: Formula) -> tuple[str, ...]:
    """Возвращает имена различных переменных в лексикографическом порядке."""
    names: set[str] = set()
    pending = [formula]
    while pending:
        node = pending.pop()
        if isinstance(node, Variable):
            names.add(node.name)
        elif isinstance(node, Negation):
            pending.append(node.operand)
        elif isinstance(node, Binary):
            pending.append(node.right)
            pending.append(node.left)
        else:
            raise TypeError(f"Неизвестный тип узла AST: {type(node).__name__}")
    return tuple(sorted(names))


def format_fully_parenthesized(formula: Formula) -> str:
    """Вывод со всеми скобками для наглядного отображения структуры AST.

    Для очень длинных плоских цепочек строка может превышать предел
    вложенности парсера: для машинного round-trip используйте format_formula.
    """
    parts: list[str] = []
    pending: list[Formula | str] = [formula]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, Variable):
            parts.append(item.name)
        elif isinstance(item, Negation):
            pending.extend((")", item.operand, "(", "¬"))
        elif isinstance(item, Binary):
            pending.extend((")", item.right, f" {item.operator.value} ", item.left, "("))
        else:
            raise TypeError(f"Неизвестный тип узла AST: {type(item).__name__}")
    return "".join(parts)


def format_tree(formula: Formula) -> str:
    """Читаемое дерево; глубина AST не ограничивает стек Python."""
    lines: list[str] = []
    pending = [(formula, 0)]
    while pending:
        node, level = pending.pop()
        if isinstance(node, Variable):
            label = node.name
        elif isinstance(node, Negation):
            label = "¬"
            pending.append((node.operand, level + 1))
        elif isinstance(node, Binary):
            label = node.operator.value
            pending.append((node.right, level + 1))
            pending.append((node.left, level + 1))
        else:
            raise TypeError(f"Неизвестный тип узла AST: {type(node).__name__}")
        lines.append("  " * level + label)
    return "\n".join(lines)


_PRECEDENCE = {
    BinaryOperator.IMPLIES: 1,
    BinaryOperator.OR: 2,
    BinaryOperator.AND: 3,
}


def format_formula(formula: Formula) -> str:
    """Компактная однозначная запись с сохранением *точной* структуры AST.

    Скобки нужны только там, где из-за приоритета или левой
    ассоциативности изменилось бы дерево. Работает без рекурсии
    даже для длинных левовложенных цепочек.
    """
    parts: list[str] = []
    # Кортеж: (узел, родительский оператор, является ли правым операндом).
    pending: list[tuple[Formula, BinaryOperator | str | None, bool] | str] = [
        (formula, None, False)
    ]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            parts.append(item)
            continue

        node, parent, is_right = item
        wrap = False
        if isinstance(node, Binary):
            if parent == "NOT":
                wrap = True
            elif isinstance(parent, BinaryOperator):
                child_priority = _PRECEDENCE[node.operator]
                parent_priority = _PRECEDENCE[parent]
                wrap = child_priority < parent_priority or (
                    child_priority == parent_priority and is_right
                )

        if wrap:
            pending.append(")")
        if isinstance(node, Variable):
            pending.append(node.name)
        elif isinstance(node, Negation):
            pending.append((node.operand, "NOT", False))
            pending.append("¬")
        elif isinstance(node, Binary):
            pending.append((node.right, node.operator, True))
            pending.append(f" {node.operator.value} ")
            pending.append((node.left, node.operator, False))
        else:
            raise TypeError(f"Неизвестный тип узла AST: {type(node).__name__}")
        if wrap:
            pending.append("(")
    return "".join(parts)
