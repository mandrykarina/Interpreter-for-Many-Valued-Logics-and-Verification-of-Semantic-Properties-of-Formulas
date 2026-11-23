"""Проверка перебора и ограничителей ресурсов."""
from itertools import product

import pytest

from logic import (AnalysisLimitError, LogicSystem, count_interpretations,
                   iter_interpretations, parse_formula, truth_table)
from logic.truth_tables import DEFAULT_MAX_ROWS, HARD_MAX_ROWS, ensure_capacity


@pytest.mark.parametrize('system,expected', [
    (LogicSystem.CLASSICAL, 4), (LogicSystem.K3, 9), (LogicSystem.L3, 9)])
def test_interpretations_complete_and_deterministic(system, expected):
    all_vals = list(iter_interpretations(('p', 'q'), system))
    assert len(all_vals) == expected
    assert all_vals == [dict(zip(('p', 'q'), vals)) for vals in product(system.values, repeat=2)]
    assert len({tuple(v.items()) for v in all_vals}) == expected


@pytest.mark.parametrize('system', list(LogicSystem))
def test_truth_table_p_and_q(system):
    ast = parse_formula('p & q')
    rows = list(truth_table(ast, system))
    assert len(rows) == len(system.values) ** 2
    assert list(rows[0].valuation) == ['p', 'q']
    for row in rows:
        assert row.result == min(row.valuation.values())


def test_table_order_is_sorted_by_variable_names():
    rows = list(truth_table(parse_formula('q | P & p'), LogicSystem.CLASSICAL))
    assert list(rows[0].valuation) == ['P', 'p', 'q']
    assert len(rows) == 8
    assert rows[0].result == 0
    assert rows[-1].result == 2


@pytest.mark.parametrize('system', list(LogicSystem))
def test_table_uses_each_variable_once(system):
    rows = list(truth_table(parse_formula('p & p | p -> p'), system))
    assert len(rows) == len(system.values)
    assert tuple(rows[0].valuation) == ('p',)


def test_truth_table_is_lazy():
    iterator = truth_table(parse_formula('p'), LogicSystem.K3)
    assert not isinstance(iterator, list)
    assert [r.result for r in iterator] == [0, 1, 2]


def test_count_valid_and_invalid():
    assert count_interpretations(0, LogicSystem.K3) == 1
    assert count_interpretations(4, LogicSystem.CLASSICAL) == 16
    assert count_interpretations(4, LogicSystem.L3) == 81
    for invalid in (-1, 1.0, True):
        with pytest.raises(ValueError):
            count_interpretations(invalid, LogicSystem.K3)


def test_resource_limits_on_12_variables_before_enumeration():
    ast = parse_formula(' | '.join('p' + str(i) for i in range(12)))
    with pytest.raises(AnalysisLimitError, match='интерпретаций'):
        list(truth_table(ast, LogicSystem.L3))
    with pytest.raises(AnalysisLimitError, match='интерпретаций'):
        ensure_capacity(12, 30, LogicSystem.L3)


def test_resource_work_guard_independent_of_row_guard():
    ast = parse_formula(' -> '.join('p' for _ in range(1800)))
    # Большая формула + много переменных: количество шагов превысит лимит.
    long_formula = parse_formula(' -> '.join('p' for _ in range(1800)) + ' -> ' + ' | '.join('v' + str(i) for i in range(8)))
    with pytest.raises(AnalysisLimitError, match='операций'):
        list(truth_table(long_formula, LogicSystem.K3))
    assert len(list(truth_table(ast, LogicSystem.CLASSICAL))) == 2


def test_limit_and_bad_variable_names():
    for bad in (0, -1, True, 1.5, HARD_MAX_ROWS+1):
        with pytest.raises(AnalysisLimitError):
            list(iter_interpretations(('p',), LogicSystem.K3, max_rows=bad))
    with pytest.raises(ValueError, match='дубликаты'):
        list(iter_interpretations(('p', 'p'), LogicSystem.K3))
    with pytest.raises(ValueError, match='Имена'):
        list(iter_interpretations(('',), LogicSystem.K3))


def test_small_max_rows_denies_without_partial_results():
    with pytest.raises(AnalysisLimitError, match='Полный анализ не проводился'):
        list(truth_table(parse_formula('p | q'), LogicSystem.K3, max_rows=8))
