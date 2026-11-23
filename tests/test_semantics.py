"""Исчерпывающие таблицы операций, проверки ввода и вычисления AST."""
from itertools import product
import random

import pytest

from logic import (Binary, BinaryOperator, LogicSystem, Negation, ValuationError, Variable,
                   binary, check_valuation, collect_variables, evaluate, format_value, negate,
                   parse_formula, parse_value)
from logic.semantics import compile_formula, run_program


def ref_binary(op, a, b, system):
    # независимый табличный эталон операций над 0,1/2,1 (внутренние коды)
    AND = ((0, 0, 0), (0, 1, 1), (0, 1, 2))
    OR = ((0, 1, 2), (1, 1, 2), (2, 2, 2))
    KIMPL = ((2, 2, 2), (1, 1, 2), (0, 1, 2))
    LIMPL = ((2, 2, 2), (1, 2, 2), (0, 1, 2))
    lookup = {BinaryOperator.AND: AND, BinaryOperator.OR: OR,
              BinaryOperator.IMPLIES: LIMPL if system == LogicSystem.L3 else KIMPL}
    return lookup[op][a][b]


@pytest.mark.parametrize('system', list(LogicSystem))
@pytest.mark.parametrize('op', list(BinaryOperator))
def test_all_binary_truth_table_cells(system, op):
    for a, b in product(system.values, repeat=2):
        assert binary(op, a, b, system) == ref_binary(op, a, b, system)


@pytest.mark.parametrize('system', list(LogicSystem))
def test_negation_all_cells(system):
    expected = {0: 2, 1: 1, 2: 0}
    for value in system.values:
        assert negate(value, system) == expected[value]


@pytest.mark.parametrize('system', list(LogicSystem))
def test_completeness_of_valuation(system):
    expr = parse_formula('p | q')
    assert evaluate(expr, {'p': 0, 'q': 2}, system) == 2
    with pytest.raises(ValuationError, match='Не заданы'):
        evaluate(expr, {'p': 2}, system)
    with pytest.raises(ValuationError, match='Неизвестные'):
        evaluate(expr, {'p': 0, 'q': 2, 'r': 0}, system)
    with pytest.raises(ValuationError):
        evaluate(expr, {'p': True, 'q': 2}, system)
    with pytest.raises(ValuationError):
        evaluate(expr, {'p': 0.0, 'q': 2}, system)
    with pytest.raises(ValuationError):
        evaluate(expr, {'p': '1', 'q': 2}, system)
    with pytest.raises(ValuationError):
        evaluate(expr, [], system)
    with pytest.raises(ValuationError):
        evaluate(expr, {'p': 3, 'q': 0}, system)


def test_classical_rejects_half_code():
    assert 1 not in LogicSystem.CLASSICAL.values
    for op in BinaryOperator:
        with pytest.raises(ValuationError):
            binary(op, 1, 2, LogicSystem.CLASSICAL)
    with pytest.raises(ValuationError):
        negate(1, LogicSystem.CLASSICAL)
    with pytest.raises(ValuationError):
        evaluate(parse_formula('p'), {'p': 1}, LogicSystem.CLASSICAL)


@pytest.mark.parametrize('raw,expected', [
    ('0', 0), (' 0 ', 0), ('1', 2), (' 1 ', 2), ('1/2', 1),
    ('0.5', 1), ('½', 1), ('  ½ ', 1),
])
def test_user_value_conversions(raw, expected):
    assert parse_value(raw, LogicSystem.K3) == expected
    assert parse_value(raw, LogicSystem.L3) == expected
    if expected == 1:
        with pytest.raises(ValuationError):
            parse_value(raw, LogicSystem.CLASSICAL)
    else:
        assert parse_value(raw, LogicSystem.CLASSICAL) == expected


@pytest.mark.parametrize('invalid', ['', '2', '-1', '1.0', '0,5', '0.50', 'NaN', 'nan',
                                     'inf', 'True', 'false', '1 / 2', '1.5', '0.3', 'one'])
def test_bad_user_value_rejected(invalid):
    with pytest.raises(ValuationError):
        parse_value(invalid, LogicSystem.K3)


def test_user_display_conversion_is_distinct_from_internal_codes():
    assert format_value(0) == '0'
    assert format_value(1) == '1/2'
    assert format_value(2) == '1'
    for value in ('1', 1.0, True, -1, 4, None):
        with pytest.raises(ValuationError):
            format_value(value)


@pytest.mark.parametrize('system,expected', [
    (LogicSystem.CLASSICAL, 2), (LogicSystem.K3, 1), (LogicSystem.L3, 2)
])
def test_p_implies_p(system, expected):
    valuation = {'p': 1 if system != LogicSystem.CLASSICAL else 2}
    assert evaluate(parse_formula('p -> p'), valuation, system) == expected


def test_required_partial_examples():
    v = {'p': 1, 'q': 1}
    samples = [('p -> q', 1, 2), ('p -> p', 1, 2),
               ('p & !p', 1, 1), ('p | !p', 1, 1)]
    for expr, expected_k3, expected_l3 in samples:
        ast = parse_formula(expr)
        relevant = {name: v[name] for name in collect_variables(ast)}
        assert evaluate(ast, relevant, LogicSystem.K3) == expected_k3
        assert evaluate(ast, relevant, LogicSystem.L3) == expected_l3


def test_implication_associativity_semantically_observable():
    left = parse_formula('p -> q -> r')
    explicit_left = parse_formula('(p -> q) -> r')
    right = parse_formula('p -> (q -> r)')
    for system in LogicSystem:
        for parts in product(system.values, repeat=3):
            v = dict(zip(('p', 'q', 'r'), parts))
            assert evaluate(left, v, system) == evaluate(explicit_left, v, system)
        # классическая оценка p=0, q=0, r=0: (p->q)->r=0, p->(q->r)=1
    assert evaluate(left, {'p': 0, 'q': 0, 'r': 0}, LogicSystem.CLASSICAL) == 0
    assert evaluate(right, {'p': 0, 'q': 0, 'r': 0}, LogicSystem.CLASSICAL) == 2


def recursive_reference(ast, valuation, system):
    """Независимая рекурсивная оценка AST (только для маленькой глубины)."""
    if isinstance(ast, Variable):
        return valuation[ast.name]
    if isinstance(ast, Negation):
        return (2, 1, 0)[recursive_reference(ast.operand, valuation, system)]
    if isinstance(ast, Binary):
        a = recursive_reference(ast.left, valuation, system)
        b = recursive_reference(ast.right, valuation, system)
        return ref_binary(ast.operator, a, b, system)
    raise AssertionError(type(ast))


def random_ast(rng, depth):
    if depth == 0 or rng.random() < .18:
        return Variable(rng.choice(('p', 'q', 'r')))
    if rng.random() < .24:
        return Negation(random_ast(rng, depth - 1))
    return Binary(rng.choice(tuple(BinaryOperator)), random_ast(rng, depth - 1),
                  random_ast(rng, depth - 1))


def test_2000_random_ast_evaluations_against_independent_tables():
    rng = random.Random(128519)
    for _ in range(2000):
        ast = random_ast(rng, rng.randrange(1, 7))
        names = collect_variables(ast)
        for system in LogicSystem:
            val = {name: rng.choice(system.values) for name in names}
            assert evaluate(ast, val, system) == recursive_reference(ast, val, system)


def test_deep_left_chain_no_recursion_error():
    ast = parse_formula(' -> '.join('p' for _ in range(1800)))
    program = compile_formula(ast)
    assert len(program) == 3599
    for system in LogicSystem:
        for value in system.values:
            assert evaluate(ast, {'p': value}, system) == run_program(program, {'p': value}, system)


def test_unknown_logic_and_operator():
    with pytest.raises(ValueError):
        evaluate(parse_formula('p'), {'p': 2}, 'unknown')
    with pytest.raises(ValueError):
        binary('xor', 0, 2, LogicSystem.K3)
