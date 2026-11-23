"""Структурное сопоставление схем формул и их экземпляров.

Это вспомогательная функция для регрессионных проверок первой лабораторной.
Она не реализует выводимость и не проверяет логическую общезначимость.
"""

from __future__ import annotations

from .ast import Binary, Formula, Negation, Variable


def match_schema(
    schema: Formula, instance: Formula, *,
    fixed_symbols: frozenset[str] = frozenset(),
) -> dict[str, Formula] | None:
    """Каждая переменная *схемы* -- метапеременная, заменяемая целой формулой.

    При повторном вхождении метапеременной подстановка обязана совпасть
    структурно. Никаких подстановок внутри имени переменной не допускается.

    fixed_symbols перечисляет символы схемы, которые нельзя заменять: например,
    f, если в принятом исчислении f является фиксированной константой ложности,
    а не метапеременной. По умолчанию сохраняется прежнее поведение.
    """
    bindings: dict[str, Formula] = {}
    pending: list[tuple[Formula, Formula]] = [(schema, instance)]
    while pending:
        pattern, actual = pending.pop()
        if isinstance(pattern, Variable):
            if pattern.name in fixed_symbols:
                if not isinstance(actual, Variable) or actual.name != pattern.name:
                    return None
                continue
            bound = bindings.get(pattern.name)
            if bound is None:
                bindings[pattern.name] = actual
            elif not structurally_equal(bound, actual):
                return None
        elif isinstance(pattern, Negation):
            if not isinstance(actual, Negation):
                return None
            pending.append((pattern.operand, actual.operand))
        elif isinstance(pattern, Binary):
            if not isinstance(actual, Binary) or pattern.operator != actual.operator:
                return None
            pending.append((pattern.right, actual.right))
            pending.append((pattern.left, actual.left))
        else:
            raise TypeError(f"Неизвестный тип узла схемы: {type(pattern).__name__}")
    return bindings


def structurally_equal(left: Formula, right: Formula) -> bool:
    """Сравнивает деревья итеративно, без глубокой рекурсии dataclass.__eq__."""
    pending = [(left, right)]
    while pending:
        a, b = pending.pop()
        if type(a) is not type(b):
            return False
        if isinstance(a, Variable):
            if a.name != b.name:
                return False
        elif isinstance(a, Negation):
            pending.append((a.operand, b.operand))
        elif isinstance(a, Binary):
            if a.operator != b.operator:
                return False
            pending.append((a.left, b.left))
            pending.append((a.right, b.right))
        else:
            raise TypeError(f"Неизвестный тип узла: {type(a).__name__}")
    return True
