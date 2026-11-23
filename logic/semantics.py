"""Точная семантика классической логики, K3 и L3.

ВНУТРЕННЕЕ представление: 0 = ложь, 1 = 1/2, 2 = истина.
Ввод пользователя '1' всегда означает истину и преобразуется в код 2.
Числа с плавающей точкой не используются.
"""
from __future__ import annotations

from enum import Enum
from typing import Mapping

from .ast import Binary, BinaryOperator, Formula, Negation, Variable, collect_variables


class LogicSystem(str, Enum):
    CLASSICAL = "classical"
    K3 = "k3"
    L3 = "l3"

    @property
    def values(self) -> tuple[int, ...]:
        return (0, 2) if self is LogicSystem.CLASSICAL else (0, 1, 2)

    @property
    def title(self) -> str:
        return {self.CLASSICAL: "Классическая", self.K3: "Клини K3", self.L3: "Лукасевича L3"}[self]


class ValuationError(ValueError):
    """Неполная или недопустимая оценка переменных."""


def logic_system(value: LogicSystem | str) -> LogicSystem:
    if isinstance(value, LogicSystem):
        return value
    if isinstance(value, str):
        aliases = {"1": LogicSystem.CLASSICAL, "2": LogicSystem.K3, "3": LogicSystem.L3,
                   "classic": LogicSystem.CLASSICAL, "classical": LogicSystem.CLASSICAL,
                   "k3": LogicSystem.K3, "l3": LogicSystem.L3}
        found = aliases.get(value.strip().lower())
        if found is not None:
            return found
    raise ValueError("Неизвестная логика: выберите classical, k3 или l3")


def format_value(value: int) -> str:
    if type(value) is not int or value not in (0, 1, 2):
        raise ValuationError(f"Недопустимый внутренний код истинности: {value!r}")
    return ("0", "1/2", "1")[value]


def parse_value(value: str, system: LogicSystem | str) -> int:
    """Интерфейсная конверсия; '1' => внутренний код 2, '1/2' => код 1."""
    logic = logic_system(system)
    if not isinstance(value, str):
        raise ValuationError("Значение должно быть строкой: 0, 1 или 1/2")
    normalized = value.strip()
    codes = {"0": 0, "1": 2, "1/2": 1, "0.5": 1, "½": 1}
    code = codes.get(normalized)
    if code is None:
        raise ValuationError(f"Недопустимое значение {value!r}: введите 0, 1" + (" или 1/2" if logic is not LogicSystem.CLASSICAL else ""))
    _check_code(code, logic)
    return code


def _check_code(value: int, system: LogicSystem) -> None:
    if type(value) is not int or value not in system.values:
        raise ValuationError(f"Значение {value!r} недопустимо для логики {system.title}; внутренние коды: {system.values}")


def check_valuation(variable_names: tuple[str, ...], valuation: Mapping[str, int],
                    system: LogicSystem | str) -> dict[str, int]:
    logic = logic_system(system)
    if not isinstance(valuation, Mapping):
        raise ValuationError("Оценка должна задаваться отображением переменная -> внутренний код")
    expected = set(variable_names)
    actual = set(valuation)
    absent = sorted(expected - actual)
    surplus = sorted((str(name) for name in actual - expected))
    if absent:
        raise ValuationError("Не заданы значения переменных: " + ", ".join(absent))
    if surplus:
        raise ValuationError("Неизвестные переменные в оценке: " + ", ".join(surplus))
    for name in variable_names:
        _check_code(valuation[name], logic)
    return dict(valuation)


def negate(value: int, system: LogicSystem | str) -> int:
    logic = logic_system(system)
    _check_code(value, logic)
    return 2 - value


def binary(operator: BinaryOperator, left: int, right: int,
           system: LogicSystem | str) -> int:
    logic = logic_system(system)
    _check_code(left, logic)
    _check_code(right, logic)
    return _binary_unchecked(operator, left, right, logic)


def _binary_unchecked(operator: BinaryOperator, left: int, right: int,
                      logic: LogicSystem) -> int:
    if operator == BinaryOperator.AND:
        return min(left, right)
    if operator == BinaryOperator.OR:
        return max(left, right)
    if operator == BinaryOperator.IMPLIES:
        if logic == LogicSystem.L3:
            return min(2, 2 - left + right)
        return max(2 - left, right)
    raise ValueError(f"Неизвестная логическая операция: {operator!r}")


# Постфиксный код для многократного вычисления одного AST без рекурсии.
Instruction = tuple[str, str | BinaryOperator | None]
Program = tuple[Instruction, ...]


def compile_formula(formula: Formula) -> Program:
    result: list[Instruction] = []
    pending: list[tuple[Formula, bool]] = [(formula, False)]
    while pending:
        node, ready = pending.pop()
        if isinstance(node, Variable):
            result.append(("var", node.name))
        elif isinstance(node, Negation):
            if ready:
                result.append(("not", None))
            else:
                pending.append((node, True))
                pending.append((node.operand, False))
        elif isinstance(node, Binary):
            if ready:
                result.append(("binary", node.operator))
            else:
                pending.append((node, True))
                pending.append((node.right, False))
                pending.append((node.left, False))
        else:
            raise TypeError(f"Неизвестный узел AST: {type(node).__name__}")
    return tuple(result)


def run_program(program: Program, valuation: Mapping[str, int], system: LogicSystem) -> int:
    """Быстрый внутренний интерпретатор; вызывающая функция проверяет оценку."""
    stack: list[int] = []
    for kind, argument in program:
        if kind == "var":
            assert isinstance(argument, str)
            stack.append(valuation[argument])
        elif kind == "not":
            stack[-1] = 2 - stack[-1]
        elif kind == "binary":
            right = stack.pop()
            left = stack.pop()
            assert isinstance(argument, BinaryOperator)
            stack.append(_binary_unchecked(argument, left, right, system))
        else:
            raise ValueError(f"Неизвестная инструкция: {kind!r}")
    if len(stack) != 1:
        raise ValueError("Некорректная программа вычисления")
    return stack[0]


def evaluate(formula: Formula, valuation: Mapping[str, int],
             system: LogicSystem | str) -> int:
    """Вычислить AST. Возвращает *внутренний* код (0, 1 или 2)."""
    logic = logic_system(system)
    checked = check_valuation(collect_variables(formula), valuation, logic)
    return run_program(compile_formula(formula), checked, logic)
