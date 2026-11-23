"""Воспроизводимый длительный QA-прогон.

Запуск: python -m qa.stress --formulas 50000 --invalid 10000 --relations 3000
Не изменяет реализацию; при ошибке печатает seed/индекс/формулу.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from itertools import product
from pathlib import Path

from logic import (Binary, BinaryOperator, FormulaSyntaxError, LogicSystem, Negation,
                   Variable, check_entailment, collect_variables, evaluate,
                   format_formula, parse_formula, structurally_equal)
from qa.reference import VALUES, independent_rows, oracle, oracle_entails

SEED = 2026110701
NAMES = ('p', 'q', 'r', 's', 'x_2', 'v', 'α', 'переменная')


def random_tree(rng, depth, pool):
    if not depth or rng.random() < .26:
        return Variable(rng.choice(pool))
    if rng.random() < .28:
        return Negation(random_tree(rng, depth-1, pool))
    return Binary(rng.choice(tuple(BinaryOperator)), random_tree(rng, depth-1, pool),
                  random_tree(rng, depth-1, pool))


def run(formulas, invalid, relations):
    rng = random.Random(SEED)
    start = time.perf_counter()
    checks = 0
    for idx in range(formulas):
        tree = random_tree(rng, idx % 8, NAMES[:2 + idx % 6])
        text = format_formula(tree)
        restored = parse_formula(text)
        assert structurally_equal(tree, restored), ('roundtrip', idx, text)
        logic = tuple(LogicSystem)[idx % 3]
        names = collect_variables(tree)
        if idx % 23 == 0 and len(names) <= 3:
            candidates = independent_rows(names, logic.value)
        else:
            candidates = ({name: rng.choice(VALUES[logic.value]) for name in names} for _ in range(2))
        for valuation in candidates:
            expected = oracle(tree, valuation, logic.value)
            actual = evaluate(restored, valuation, logic)
            assert expected == actual, ('value', idx, text, logic.value, valuation, expected, actual)
            checks += 1
    mutations = [
        lambda s: s + ' ->', lambda s: '-> ' + s,
        lambda s: '(' + s, lambda s: s + ')',
        lambda s: '(' + s + ' & )', lambda s: s + '@',
        lambda s: '(' + s + ' || p)', lambda s: '(' + s + ' r)',
        lambda s: '!' + s + '&', lambda s: '(' + s + ' -> -> q)',
    ]
    for idx in range(invalid):
        source = format_formula(random_tree(rng, idx % 7, NAMES[:4]))
        bad = mutations[idx % len(mutations)](source)
        try:
            parse_formula(bad)
        except FormulaSyntaxError:
            continue
        raise AssertionError(('invalid accepted', idx, bad))
    relation_checks = 0
    for idx in range(relations):
        logic = tuple(LogicSystem)[idx % 3]
        pool = ('p', 'q', 'r')
        premises = [random_tree(rng, idx % 4, pool) for _ in range(idx % 5)]
        conclusion = random_tree(rng, (idx+1) % 4, pool)
        names = tuple(sorted(set(collect_variables(conclusion)).union(
            *(collect_variables(p) for p in premises))))
        actual = check_entailment(premises, conclusion, logic)
        models, ce = oracle_entails(premises, conclusion, names, logic.value)
        assert actual.premise_models == models, ('models', idx, logic.value)
        assert actual.entails == (ce is None), ('entails', idx, logic.value)
        assert (dict(actual.counterexample.valuation) if actual.counterexample else None) == (ce[0] if ce else None), ('counterexample', idx, logic.value)
        relation_checks += len(VALUES[logic.value]) ** len(names)
    return {
        'seed': SEED,
        'generated_valid_ast': formulas,
        'generated_invalid_strings': invalid,
        'generated_entailments': relations,
        'independent_formula_valuation_comparisons': checks,
        'independent_entailment_interpretations': relation_checks,
        'elapsed_seconds': round(time.perf_counter() - start, 3),
        'failures': 0,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--formulas', type=int, default=50_000)
    p.add_argument('--invalid', type=int, default=10_000)
    p.add_argument('--relations', type=int, default=3_000)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    result = run(args.formulas, args.invalid, args.relations)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
