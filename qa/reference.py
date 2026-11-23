"""Независимый эталон: фиксированные таблицы операций, без импорта semantics.

Внутренние коды: 0 => 0, 1 => 1/2, 2 => 1. Таблицы выписаны
непосредственно по математическим определениям лабораторной работы.
"""
from __future__ import annotations

from itertools import product
from logic.ast import Binary, BinaryOperator, Negation, Variable

VALUES = {'classical': (0, 2), 'k3': (0, 1, 2), 'l3': (0, 1, 2)}
NOT = {0: 2, 1: 1, 2: 0}
AND = ((0, 0, 0), (0, 1, 1), (0, 1, 2))
OR = ((0, 1, 2), (1, 1, 2), (2, 2, 2))
IMPLIES = {
    'classical': ((2, None, 2), (None, None, None), (0, None, 2)),
    'k3': ((2, 2, 2), (1, 1, 2), (0, 1, 2)),
    'l3': ((2, 2, 2), (1, 2, 2), (0, 1, 2)),
}


def oracle(formula, valuation, system: str):
    if isinstance(formula, Variable):
        return valuation[formula.name]
    if isinstance(formula, Negation):
        return NOT[oracle(formula.operand, valuation, system)]
    if isinstance(formula, Binary):
        left = oracle(formula.left, valuation, system)
        right = oracle(formula.right, valuation, system)
        if formula.operator is BinaryOperator.AND:
            return AND[left][right]
        if formula.operator is BinaryOperator.OR:
            return OR[left][right]
        if formula.operator is BinaryOperator.IMPLIES:
            return IMPLIES[system][left][right]
    raise TypeError(type(formula))


def independent_rows(names, system):
    for values in product(VALUES[system], repeat=len(names)):
        yield dict(zip(names, values))


def oracle_entails(premises, conclusion, names, system):
    models = 0
    counterexample = None
    for valuation in independent_rows(names, system):
        premise_values = tuple(oracle(p, valuation, system) for p in premises)
        if all(v == 2 for v in premise_values):
            models += 1
            conclusion_value = oracle(conclusion, valuation, system)
            if conclusion_value != 2 and counterexample is None:
                counterexample = (valuation, premise_values, conclusion_value)
    return models, counterexample
