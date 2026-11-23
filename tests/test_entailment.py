"""Эталонные примеры, пограничные случаи и независимая проверка следования."""
import itertools
import random

import pytest

from logic import (AnalysisLimitError, Binary, BinaryOperator, LogicSystem,
                   Negation, Variable, analyze_formula, check_entailment,
                   collect_variables, evaluate, parse_formula)
from variants.variant2 import parsed_formulas, parsed_relations


EXPECTED_F = {
    'classical': [True, False, False, False, True],
    'k3': [False, False, False, False, False],
    'l3': [True, False, False, False, True],
}
EXPECTED_R = {
    'classical': [True, True, True, False],
    'k3': [True, True, False, False],
    'l3': [True, False, True, False],
}


@pytest.mark.parametrize('system', list(LogicSystem))
def test_f1_to_f5_reference(system):
    actual = [analyze_formula(ast, system).tautology for ast in parsed_formulas().values()]
    assert actual == EXPECTED_F[system.value]


@pytest.mark.parametrize('system', list(LogicSystem))
def test_r1_to_r4_reference(system):
    actual = [check_entailment(r.premises, r.conclusion, system).entails
              for r in parsed_relations().values()]
    assert actual == EXPECTED_R[system.value]


@pytest.mark.parametrize('system', list(LogicSystem))
def test_r4_counterexample_complete(system):
    relation = parsed_relations()['R4']
    result = check_entailment(relation.premises, relation.conclusion, system)
    assert result.counterexample is not None
    ex = result.counterexample
    assert dict(ex.valuation) == {'p': 2, 'q': 0, 'r': 2, 's': 2, 't': 2}
    assert ex.premise_values == (2, 2, 2, 2, 2)
    assert ex.conclusion_value == 0
    assert result.total_interpretations == len(system.values) ** 5
    assert not result.vacuous


def test_r2_l3_halves_are_counterexample():
    rel = parsed_relations()['R2']
    outcome = check_entailment(rel.premises, rel.conclusion, LogicSystem.L3)
    assert outcome.counterexample is not None
    assert dict(outcome.counterexample.valuation) == dict.fromkeys('pqrstu', 1)
    assert outcome.counterexample.premise_values == (2,) * 5
    assert outcome.counterexample.conclusion_value == 1


def test_r3_k3_half_self_implication():
    rel = parsed_relations()['R3']
    outcome = check_entailment(rel.premises, rel.conclusion, LogicSystem.K3)
    assert outcome.counterexample is not None
    assert dict(outcome.counterexample.valuation) == {'p': 2, 'q': 2, 'r': 1, 's': 2, 't': 2}
    assert outcome.counterexample.premise_values == (2,) * 5
    assert outcome.counterexample.conclusion_value == 1


@pytest.mark.parametrize('system', list(LogicSystem))
def test_empty_premises_match_tautology(system):
    for source in ('p -> p', 'p & !p', '!!p -> p'):
        ast = parse_formula(source)
        outcome = check_entailment((), ast, system)
        assert outcome.entails == analyze_formula(ast, system).tautology
        assert outcome.premise_models == len(system.values)
        assert not outcome.vacuous


@pytest.mark.parametrize('system', list(LogicSystem))
def test_inconsistent_premises_vacuous(system):
    contradiction = parse_formula('p & !p')
    outcome = check_entailment([contradiction], parse_formula('q'), system)
    assert outcome.entails
    assert outcome.vacuous
    assert outcome.premise_models == 0
    assert outcome.counterexample is None
    assert outcome.total_interpretations == len(system.values) ** 2


@pytest.mark.parametrize('system', list(LogicSystem))
def test_repeated_premises_and_identity(system):
    p = parse_formula('p')
    res = check_entailment([p, p, p], p, system)
    assert res.entails and not res.vacuous and res.counterexample is None
    assert res.premise_models == 1


@pytest.mark.parametrize('system', list(LogicSystem))
def test_counterexample_when_conclusion_is_half(system):
    if system is LogicSystem.CLASSICAL:
        assert not check_entailment([parse_formula('p')], parse_formula('q'), system).entails
    else:
        res = check_entailment([parse_formula('p')], parse_formula('q'), system)
        assert res.counterexample is not None
        assert res.counterexample.conclusion_value == 0  # первый контрпример детерминирован
        # В отдельной оценке заключение 1/2 тоже не считается выделенной истиной.
        half = {'p': 2, 'q': 1}
        assert evaluate(parse_formula('p'), {'p': half['p']}, system) == 2
        assert evaluate(parse_formula('q'), {'q': half['q']}, system) == 1


def test_no_premises_one_variable_not_tautology():
    res = check_entailment([], parse_formula('v'), LogicSystem.CLASSICAL)
    assert res.variables == ('v',)
    assert res.premise_models == 2
    assert res.counterexample.premise_values == ()
    assert res.counterexample.conclusion_value == 0


def test_empty_premises_half_is_not_classical_truth():
    assert check_entailment([], parse_formula('p -> p'), LogicSystem.K3).entails is False
    assert check_entailment([], parse_formula('p -> p'), LogicSystem.L3).entails is True


def test_resource_limit_checked_for_aggregate_program_cost():
    # 9 переменных => 3^9 = 19683 строк, 10*17*19683 > 3 млн.
    premise = parse_formula('p1 | p2 | p3 | p4 | p5 | p6 | p7 | p8 | p9')
    with pytest.raises(AnalysisLimitError, match='операций'):
        check_entailment([premise] * 10, parse_formula('p1'), LogicSystem.K3)


def test_row_limit_rejects_without_partial_claim():
    ast = parse_formula(' | '.join(f'p{i}' for i in range(11)))
    with pytest.raises(AnalysisLimitError, match='Полный анализ не проводился'):
        check_entailment([], ast, LogicSystem.K3)


def test_counterexample_requires_all_premises_true_not_half():
    # В K3 у p=1/2 нет модели посылки p (только p=1).
    res = check_entailment([parse_formula('p')], parse_formula('p -> p'), LogicSystem.K3)
    assert res.entails
    assert res.premise_models == 1


# Независимый эталон: не использует eval/run_program или бинарные операции ядра.
def independent_value(ast, valuation, system):
    if isinstance(ast, Variable):
        return valuation[ast.name]
    if isinstance(ast, Negation):
        return 2 - independent_value(ast.operand, valuation, system)
    left = independent_value(ast.left, valuation, system)
    right = independent_value(ast.right, valuation, system)
    if ast.operator == BinaryOperator.AND:
        return min(left, right)
    if ast.operator == BinaryOperator.OR:
        return max(left, right)
    if system is LogicSystem.L3:
        return min(2, 2 - left + right)
    return max(2 - left, right)


def independent_entails(premises, conclusion, system):
    names = tuple(sorted(set(collect_variables(conclusion)).union(
        *(collect_variables(f) for f in premises)
    )))
    models = 0
    first = None
    for values in itertools.product(system.values, repeat=len(names)):
        valuation = dict(zip(names, values))
        if all(independent_value(p, valuation, system) == 2 for p in premises):
            models += 1
            if independent_value(conclusion, valuation, system) != 2 and first is None:
                first = dict(valuation)
    return models, first


def random_ast(rng, depth):
    if depth <= 0 or rng.random() < 0.33:
        return Variable(rng.choice(('p', 'q', 'r')))
    if rng.random() < 0.27:
        return Negation(random_ast(rng, depth - 1))
    return Binary(rng.choice(list(BinaryOperator)),
                  random_ast(rng, depth - 1), random_ast(rng, depth - 1))


def test_randomized_independent_entailment_1500_cases():
    rng = random.Random(271828)
    for _ in range(500):
        premises = [random_ast(rng, 3) for _ in range(rng.randrange(5))]
        conclusion = random_ast(rng, 3)
        for logic in LogicSystem:
            outcome = check_entailment(premises, conclusion, logic)
            models, first = independent_entails(premises, conclusion, logic)
            assert outcome.premise_models == models
            assert outcome.entails is (first is None)
            if first is None:
                assert outcome.counterexample is None
            else:
                assert outcome.counterexample is not None
                assert dict(outcome.counterexample.valuation) == first
                assert all(v == 2 for v in outcome.counterexample.premise_values)
                assert outcome.counterexample.conclusion_value != 2


@pytest.mark.parametrize('system', list(LogicSystem))
def test_independent_reference_models_all_variant_relations(system):
    for relation in parsed_relations().values():
        outcome = check_entailment(relation.premises, relation.conclusion, system)
        models, first = independent_entails(relation.premises, relation.conclusion, system)
        assert outcome.premise_models == models
        assert outcome.entails == (first is None)
        assert (dict(outcome.counterexample.valuation) if outcome.counterexample else None) == first
