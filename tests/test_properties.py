"""Свойства всех формул варианта 2 и сравнение логик."""

import pytest

from logic import (AnalysisLimitError, LogicSystem, ValuationError,
                   analyze_formula, compare_logics, evaluate, parse_formula)

FORMULAS = (
    '!!p -> p',
    '(p | !p) -> q',
    '(p -> q) & (q -> p)',
    'p & !p',
    '((p & q) -> r) -> (p -> (q -> r))',
)

EXPECTED_TAUTOLOGIES = {
    LogicSystem.CLASSICAL: (True, False, False, False, True),
    LogicSystem.K3: (False, False, False, False, False),
    LogicSystem.L3: (True, False, False, False, True),
}


@pytest.mark.parametrize('system', list(LogicSystem))
@pytest.mark.parametrize('i', range(5))
def test_variant2_formulas_expected_properties(system, i):
    ast = parse_formula(FORMULAS[i])
    result = analyze_formula(ast, system)
    assert result.tautology is EXPECTED_TAUTOLOGIES[system][i]
    assert result.total == len(system.values) ** len(result.variables)
    assert sum((result.true_count, result.half_count, result.false_count)) == result.total
    assert result.satisfiable == (result.true_count > 0)
    assert result.identically_false == (result.false_count == result.total)
    if result.witness is not None:
        assert evaluate(ast, result.witness.valuation, system) == 2
    if result.counterexample is not None:
        assert evaluate(ast, result.counterexample.valuation, system) != 2
    if result.nonzero_example is not None:
        assert evaluate(ast, result.nonzero_example.valuation, system) != 0


@pytest.mark.parametrize('system', list(LogicSystem))
def test_unsatisfiable_vs_identically_false(system):
    result = analyze_formula(parse_formula('p & !p'), system)
    assert not result.satisfiable
    assert result.true_count == 0
    assert result.identically_false == (system == LogicSystem.CLASSICAL)
    assert result.half_count == (0 if system == LogicSystem.CLASSICAL else 1)


@pytest.mark.parametrize('system', list(LogicSystem))
def test_tautology_p_implies_p(system):
    result = analyze_formula(parse_formula('p -> p'), system)
    assert result.tautology == (system != LogicSystem.K3)
    assert result.counterexample is None if result.tautology else result.counterexample is not None


def test_comparison_for_half_valuation_classical_is_na():
    c = compare_logics(parse_formula('p -> p'), {'p': 1})
    assert c.values_equal is None
    assert c.entries[0].value is None
    assert 'недопустима' in c.entries[0].note
    assert c.entries[1].value == 1
    assert c.entries[2].value == 2
    assert not c.properties_equal
    assert c.k3_l3_difference_count == 1
    assert c.first_difference.valuation == {'p': 1}
    assert (c.first_difference.k3_value, c.first_difference.l3_value) == (1, 2)


def test_comparison_classic_valuation_all_equal():
    c = compare_logics(parse_formula('p -> q'), {'p': 0, 'q': 2})
    assert c.values_equal is True
    assert c.k3_l3_difference_count == 1
    assert c.first_difference is not None


def test_comparison_same_props_when_k3_l3_same_function():
    c = compare_logics(parse_formula('p & !p'))
    assert c.values_equal is None
    assert not c.properties_equal  # тождественно ложная только в классике
    assert c.k3_l3_equal_on_all
    assert c.k3_l3_difference_count == 0
    assert c.first_difference is None


def test_comparison_on_literal_variable_no_differences():
    c = compare_logics(parse_formula('p'), {'p': 2})
    assert c.values_equal is True
    assert c.properties_equal
    assert c.k3_l3_equal_on_all


def test_missing_and_extra_valuation_comparison_rejected():
    ast = parse_formula('p -> q')
    for v in ({'p': 1}, {'p': 1, 'q': 2, 'r': 1}, {'p': 3, 'q': 2}):
        with pytest.raises(ValuationError):
            compare_logics(ast, v)


def test_analysis_exceeds_limit_no_partial_property_claim():
    ast = parse_formula(' | '.join('p' + str(i) for i in range(15)))
    with pytest.raises(AnalysisLimitError):
        analyze_formula(ast, LogicSystem.K3)
    with pytest.raises(AnalysisLimitError):
        compare_logics(ast)
