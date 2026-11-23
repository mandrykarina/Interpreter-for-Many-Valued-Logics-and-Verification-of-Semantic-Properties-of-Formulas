"""Синтаксическая регрессия всех выражений 2-го варианта из задания."""

import pytest

from logic import collect_variables, parse_formula, structurally_equal

FORMULAS = {
    "F1": "¬¬p → p",
    "F2": "(p ∨ ¬p) → q",
    "F3": "(p → q) ∧ (q → p)",
    "F4": "p ∧ ¬p",
    "F5": "((p ∧ q) → r) → (p → (q → r))",
}

ENTAILMENTS = {
    "R1": (["(p ∧ q) ∨ r", "(p ∧ q) → s", "r → s", "s → t", "t → u"], "u"),
    "R2": (["p → ¬q", "¬q → r", "r → s", "s → t", "t → u"], "¬p ∨ u"),
    "R3": (["(p → q) ∨ r", "p", "r → q", "q → s", "s → t"], "t ∧ (r → r)"),
    "R4": (["(p → q) ∨ (r → s)", "p", "r", "q → t", "s → t"], "t ∧ q"),
}


@pytest.mark.parametrize("name,expression", list(FORMULAS.items()))
def test_all_variant_formulas_accepted(name, expression):
    assert collect_variables(parse_formula(expression))


@pytest.mark.parametrize("name,case", list(ENTAILMENTS.items()))
def test_all_variant_entailments_accepted(name, case):
    premises, conclusion = case
    assert len(premises) == 5
    parsed = [parse_formula(text) for text in (*premises, conclusion)]
    assert collect_variables(parsed[-1])


def test_f5_right_nested_implications_preserved():
    f5 = parse_formula(FORMULAS["F5"])
    wrong = parse_formula("((p & q) -> r) -> p -> q -> r")
    assert not structurally_equal(f5, wrong)


def test_f1_multiple_negations():
    assert structurally_equal(parse_formula(FORMULAS["F1"]), parse_formula("(!(!p)) -> p"))
