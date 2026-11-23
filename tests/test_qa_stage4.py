"""Дополнительные независимые QA-проверки на базе эталонных таблиц."""
from __future__ import annotations

from itertools import product
import random
import subprocess
import sys
from pathlib import Path

import pytest

from logic import (AnalysisLimitError, Binary, BinaryOperator, FormulaSyntaxError,
                   LogicSystem, Negation, Variable, analyze_formula, binary, check_entailment,
                   collect_variables, compare_logics, evaluate, format_formula,
                   format_fully_parenthesized, match_schema, negate, parse_formula,
                   structurally_equal, truth_table)
from qa.reference import AND, IMPLIES, NOT, OR, VALUES, independent_rows, oracle, oracle_entails

ROOT = Path(__file__).resolve().parents[1]


def make_ast(rng, depth, names=('p','q','r','s')):
    if depth == 0 or rng.random() < .25:
        return Variable(rng.choice(names))
    if rng.random() < .27:
        return Negation(make_ast(rng, depth-1, names))
    return Binary(rng.choice(tuple(BinaryOperator)),
                  make_ast(rng, depth-1, names), make_ast(rng, depth-1, names))


@pytest.mark.parametrize('system', list(LogicSystem))
def test_truth_tables_against_independent_constants(system):
    values = VALUES[system.value]
    for value in values:
        assert negate(value, system) == NOT[value]
    for a, b in product(values, repeat=2):
        assert binary(BinaryOperator.AND, a, b, system) == AND[a][b]
        assert binary(BinaryOperator.OR, a, b, system) == OR[a][b]
        assert binary(BinaryOperator.IMPLIES, a, b, system) == IMPLIES[system.value][a][b]


@pytest.mark.parametrize('system', list(LogicSystem))
def test_exhaustive_all_small_ast_shapes(system):
    # Все AST из переменных p/q, одноуровневых отрицаний и бинарных операций.
    atoms = [Variable('p'), Variable('q')]
    nodes = atoms + [Negation(x) for x in atoms] + [
        Binary(op, x, y) for op in BinaryOperator for x in atoms for y in atoms]
    nodes += [Negation(node) for node in nodes[2:]]
    for node in nodes:
        for valuation in independent_rows(('p', 'q'), system.value):
            sliced = {n: valuation[n] for n in collect_variables(node)}
            assert evaluate(node, sliced, system) == oracle(node, sliced, system.value)


def test_12000_generated_roundtrip_and_reference_evaluations():
    rng = random.Random(20261104)
    for index in range(12_000):
        ast = make_ast(rng, index % 7, names=('p', 'q', 'r', 'v', 'x_42', 'α'))
        printed = format_formula(ast)
        restored = parse_formula(printed)
        assert structurally_equal(ast, restored), (index, printed)
        assert collect_variables(ast) == collect_variables(restored)
        system = tuple(LogicSystem)[index % 3]
        names = collect_variables(ast)
        candidates = list(independent_rows(names, system.value)) if index % 31 == 0 and len(names) <= 4 else [
            {name: rng.choice(VALUES[system.value]) for name in names} for _ in range(3)]
        for valuation in candidates:
            expected = oracle(ast, valuation, system.value)
            assert evaluate(restored, valuation, system) == expected, (index, printed, valuation)


def test_4000_invalid_mutations_no_crashes():
    rng = random.Random(20261105)
    edits = (
        lambda s: s + ' ->', lambda s: '-> ' + s, lambda s: '(' + s,
        lambda s: s + ')', lambda s: '(' + s + ' &)',
        lambda s: '!' + s + '&', lambda s: s + ' @',
        lambda s: s + ' ? q', lambda s: '(' + s + ' | | q)',
        lambda s: '(' + s + ' q)',
    )
    for index in range(4_000):
        source = format_formula(make_ast(rng, index % 6))
        invalid = edits[index % len(edits)](source)
        with pytest.raises(FormulaSyntaxError):
            parse_formula(invalid)


def test_six_requested_implications_ast_equivalence_classes():
    sources = ('p -> q -> r', '(p -> q) -> r', 'p -> (q -> r)',
               'p -> q -> (q -> q)', '(p -> q) -> (q -> q)',
               'p -> (q -> (q -> q))')
    trees = [parse_formula(s) for s in sources]
    assert structurally_equal(trees[0], trees[1])
    assert not structurally_equal(trees[0], trees[2])
    assert structurally_equal(trees[3], trees[4])
    assert not structurally_equal(trees[3], trees[5])
    for original in trees:
        assert structurally_equal(original, parse_formula(format_formula(original)))


@pytest.mark.parametrize('system', list(LogicSystem))
def test_invariants_at_every_valuation(system):
    vals = VALUES[system.value]
    checks = ('!!p', 'p & p', 'p | p', 'p & q', 'q & p', 'p | q', 'q | p',
              '!(p & q)', '!p | !q', '!(p | q)', '!p & !q')
    expressions = [parse_formula(s) for s in checks]
    for a, b in product(vals, repeat=2):
        v = {'p': a, 'q': b}
        f = lambda idx: oracle(expressions[idx], v, system.value)
        assert f(0) == a and f(1) == a and f(2) == a
        assert f(3) == f(4) and f(5) == f(6)
        assert f(7) == f(8) and f(9) == f(10)
        for expression in expressions:
            assert evaluate(expression, {k: v[k] for k in collect_variables(expression)}, system) in vals


def test_threevalued_nonclassical_middle_truth():
    for system in (LogicSystem.K3, LogicSystem.L3):
        for source in ('p | !p', 'p & !p'):
            assert evaluate(parse_formula(source), {'p': 1}, system) == 1
    assert evaluate(parse_formula('p -> p'), {'p': 1}, LogicSystem.K3) == 1
    assert evaluate(parse_formula('p -> p'), {'p': 1}, LogicSystem.L3) == 2


@pytest.mark.parametrize('system', list(LogicSystem))
def test_entailment_oracle_edge_cases(system):
    pairs = [([], 'p'), ([], 'p -> p'), (['p'], 'p'),
             (['p', 'p'], 'p'), (['p & !p'], 'q'),
             (['p -> q','p'], 'q'), (['p', 'q'], 'p & q'),
             (['p'], 'q'), (['p -> p'], 'p'),
             (['p -> !q','!q -> r'], 'r')]
    for sources, target in pairs:
        premises = [parse_formula(x) for x in sources]
        conclusion = parse_formula(target)
        result = check_entailment(premises, conclusion, system)
        names = tuple(sorted(set(collect_variables(conclusion)).union(
            *(collect_variables(x) for x in premises))))
        models, ce = oracle_entails(premises, conclusion, names, system.value)
        assert result.premise_models == models
        assert result.entails == (ce is None)
        assert result.vacuous == (models == 0)
        if ce is not None:
            assert dict(result.counterexample.valuation) == ce[0]
            assert result.counterexample.premise_values == ce[1]
            assert result.counterexample.conclusion_value == ce[2]


def test_independent_1000_random_entailments():
    rng = random.Random(20261106)
    for i in range(1000):
        system = tuple(LogicSystem)[i % 3]
        premises = [make_ast(rng, i % 4, names=('p', 'q', 'r')) for _ in range(i % 5)]
        conclusion = make_ast(rng, (i + 1) % 4, names=('p','q','r'))
        names = tuple(sorted(set(collect_variables(conclusion)).union(
            *(collect_variables(x) for x in premises))))
        got = check_entailment(premises, conclusion, system)
        models, ce = oracle_entails(premises, conclusion, names, system.value)
        assert got.premise_models == models
        assert got.entails == (ce is None)
        assert (dict(got.counterexample.valuation) if got.counterexample else None) == (ce[0] if ce else None)


def test_axiom_schemas_simultaneous_substitution():
    # Схемы K и S, отрицательные случаи (подмена одного повторного p).
    k = parse_formula('p -> (q -> p)')
    s = parse_formula('(s -> (p -> q)) -> ((s -> p) -> (s -> q))')
    assert match_schema(k, parse_formula('(a & b) -> ((r -> !v) -> (a & b))'))
    assert match_schema(k, parse_formula('(a & b) -> ((r -> !v) -> (a | b))')) is None
    replacement = {'s':'(!a | b)','p':'(c -> d)','q':'(e & f)'}
    good = parse_formula('((!a | b) -> ((c -> d) -> (e & f))) -> (((!a | b) -> (c -> d)) -> ((!a | b) -> (e & f)))')
    bindings = match_schema(s, good)
    assert bindings is not None
    for key, value in replacement.items():
        assert structurally_equal(bindings[key], parse_formula(value))
    bad = parse_formula('((!a | b) -> ((c -> d) -> (e & f))) -> (((!a | b) -> (c -> d)) -> ((!a & b) -> (e & f)))')
    assert match_schema(s, bad) is None


def test_depth_and_length_guardrails():
    with pytest.raises(FormulaSyntaxError):
        parse_formula('(' * 200 + 'p' + ')' * 200)
    with pytest.raises(FormulaSyntaxError):
        parse_formula('!' * 200 + 'p')
    with pytest.raises(FormulaSyntaxError):
        parse_formula('p'*20001)
    with pytest.raises(FormulaSyntaxError):
        parse_formula('p -> ' * 4300 + 'q')


def test_no_false_conclusion_when_resource_exceeded():
    formula = parse_formula(' | '.join('v'+str(i) for i in range(12)))
    with pytest.raises(AnalysisLimitError):
        analyze_formula(formula, LogicSystem.K3)
    with pytest.raises(AnalysisLimitError):
        check_entailment([], formula, LogicSystem.K3)
    with pytest.raises(AnalysisLimitError):
        compare_logics(formula)


def run_cli(commands):
    return subprocess.run([sys.executable, str(ROOT / 'main.py')], input='\n'.join(commands) + '\n',
                          capture_output=True, text=True, cwd=ROOT, timeout=12)


def test_console_error_recovery_and_clean_exit():
    p = run_cli(['2', 'p ->', '5', 'p & !p', '3', 'p -> q', 'junk', '1', '0', '2', '0'])
    assert p.returncode == 0, p.stderr
    assert 'Traceback' not in p.stderr and 'Завершение работы' in p.stdout
    assert 'ОШИБКА СИНТАКСИСА' in p.stdout and 'ОШИБКА ОЦЕНКИ' in p.stdout


def test_console_large_analysis_safe_and_recovers():
    p = run_cli(['1', '2', '5', ' | '.join('p'+str(i) for i in range(12)), '7', '0'])
    assert p.returncode == 0, p.stderr
    assert 'Traceback' not in p.stderr
    assert 'Полный анализ не проводился' in p.stdout
    assert 'Приоритеты' in p.stdout


def test_console_invalid_menu_selection_and_half_inputs():
    p = run_cli(['1', '9', '2', '3', 'p -> p', '0.5', '1', '3', 'p -> p', '½', '0'])
    assert p.returncode == 0, p.stderr
    assert 'Неверный номер' in p.stdout
    assert 'Значение истинности: 1/2' in p.stdout
    assert 'Значение истинности: 1' in p.stdout


def test_valuations_half_not_classical():
    from logic import ValuationError, parse_value, check_valuation
    for x in ('1/2', '0.5', '½'):
        with pytest.raises(ValuationError):
            parse_value(x, LogicSystem.CLASSICAL)
    assert parse_value('1', LogicSystem.K3) == 2
    assert parse_value('0', LogicSystem.L3) == 0
    ast = parse_formula('p & q')
    for valuation in ({'p': 2}, {'p': 2, 'q': 2, 'r': 2}, {'p': 2, 'q': True}):
        with pytest.raises(ValuationError):
            evaluate(ast, valuation, LogicSystem.K3)


def test_a3_literal_f_not_metavariable_regression():
    # A3 из первой лабораторной использует фиксированный символ f.
    schema = parse_formula('p -> f -> f -> p')
    assert match_schema(schema, parse_formula('q -> f -> f -> q'), fixed_symbols=frozenset({'f'}))
    assert match_schema(schema, parse_formula('q -> r -> r -> q'), fixed_symbols=frozenset({'f'})) is None
    assert match_schema(schema, parse_formula('(a & b) -> f -> f -> (a & b)'), fixed_symbols=frozenset({'f'}))
    assert match_schema(schema, parse_formula('(a & b) -> f -> f -> (a | b)'), fixed_symbols=frozenset({'f'})) is None


@pytest.mark.parametrize('system', list(LogicSystem))
def test_all_variant_formulas_independent_reference(system):
    from variants.variant2 import parsed_formulas
    for formula in parsed_formulas().values():
        rows = list(truth_table(formula, system))
        names = collect_variables(formula)
        expected = [(valuation, oracle(formula, valuation, system.value))
                    for valuation in independent_rows(names, system.value)]
        assert [(dict(r.valuation), r.result) for r in rows] == expected
        props = analyze_formula(formula, system)
        assert props.total == len(expected)
        assert props.true_count == sum(value == 2 for _, value in expected)
        assert props.half_count == sum(value == 1 for _, value in expected)
        assert props.false_count == sum(value == 0 for _, value in expected)
        assert props.tautology == all(value == 2 for _, value in expected)
        assert props.satisfiable == any(value == 2 for _, value in expected)
        assert props.identically_false == all(value == 0 for _, value in expected)


@pytest.mark.parametrize('system', list(LogicSystem))
def test_all_variant_relations_independent_reference(system):
    from variants.variant2 import parsed_relations
    for rel in parsed_relations().values():
        outcome = check_entailment(rel.premises, rel.conclusion, system)
        names = outcome.variables
        models, ce = oracle_entails(rel.premises, rel.conclusion, names, system.value)
        assert outcome.total_interpretations == len(VALUES[system.value])**len(names)
        assert outcome.premise_models == models
        assert outcome.entails == (ce is None)
        assert (dict(outcome.counterexample.valuation) if outcome.counterexample else None) == (ce[0] if ce else None)


def test_global_exit_from_nested_valuation():
    p = run_cli(['3', 'p & q', ':exit'])
    assert p.returncode == 0, p.stderr
    assert 'Завершение работы' in p.stdout
    assert 'Traceback' not in p.stderr


def test_global_exit_from_variant_menu():
    p = run_cli(['9', '1', ':exit'])
    assert p.returncode == 0, p.stderr
    assert 'Завершение работы' in p.stdout


def test_menu_export_filesystem_error_is_recoverable(monkeypatch, capsys):
    import builtins
    import main
    answers = iter(['9', '4', '0', '0'])
    monkeypatch.setattr(builtins, 'input', lambda _: next(answers))
    def denied(_):
        raise PermissionError('Нет прав для записи')
    monkeypatch.setattr(main, 'export_variant2', denied)
    assert main.main([]) == 0
    out = capsys.readouterr().out
    assert 'Нет прав для записи' in out
    assert 'Завершение работы' in out
