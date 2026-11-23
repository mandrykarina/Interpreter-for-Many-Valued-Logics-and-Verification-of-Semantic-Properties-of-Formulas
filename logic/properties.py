"""Семантические свойства и сравнение логических систем по полному перебору."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .ast import Formula, collect_variables
from .semantics import (LogicSystem, ValuationError, check_valuation, compile_formula,
                        logic_system, run_program)
from .truth_tables import DEFAULT_MAX_ROWS, TruthRow, ensure_capacity, iter_interpretations, truth_table


@dataclass(frozen=True)
class FormulaProperties:
    system: LogicSystem
    variables: tuple[str, ...]
    total: int
    true_count: int
    half_count: int
    false_count: int
    tautology: bool
    satisfiable: bool
    identically_false: bool
    witness: TruthRow | None
    counterexample: TruthRow | None
    nonzero_example: TruthRow | None


def analyze_formula(formula: Formula, system: LogicSystem | str,
                    *, max_rows: int = DEFAULT_MAX_ROWS) -> FormulaProperties:
    logic = logic_system(system)
    variables = collect_variables(formula)
    program = compile_formula(formula)
    total = ensure_capacity(len(variables), len(program), logic, max_rows=max_rows)
    counts = [0, 0, 0]
    witness = counterexample = nonzero_example = None
    for row in truth_table(formula, logic, max_rows=max_rows):
        counts[row.result] += 1
        if row.result == 2 and witness is None:
            witness = row
        if row.result != 2 and counterexample is None:
            counterexample = row
        if row.result != 0 and nonzero_example is None:
            nonzero_example = row
    return FormulaProperties(logic, variables, total, counts[2], counts[1], counts[0],
                             counts[2] == total, counts[2] > 0, counts[0] == total,
                             witness, counterexample, nonzero_example)


@dataclass(frozen=True)
class ComparisonEntry:
    system: LogicSystem
    properties: FormulaProperties
    value: int | None
    note: str | None


@dataclass(frozen=True)
class Difference:
    valuation: Mapping[str, int]
    k3_value: int
    l3_value: int


@dataclass(frozen=True)
class LogicComparison:
    entries: tuple[ComparisonEntry, ...]
    properties_equal: bool
    values_equal: bool | None  # None: общей для всех трёх оценки нет или она не задана
    k3_l3_equal_on_all: bool
    k3_l3_difference_count: int
    first_difference: Difference | None


def compare_logics(formula: Formula, valuation: Mapping[str, int] | None = None,
                   *, max_rows: int = DEFAULT_MAX_ROWS) -> LogicComparison:
    variables = collect_variables(formula)
    program = compile_formula(formula)
    if valuation is not None:
        # Структура оценки должна быть корректной даже когда классика не допускает 1/2.
        check_valuation(variables, valuation, LogicSystem.K3)

    # Все проверки лимита выполняются до начала вычислений.
    for system in LogicSystem:
        ensure_capacity(len(variables), len(program), system, max_rows=max_rows)

    entries: list[ComparisonEntry] = []
    for system in LogicSystem:
        properties = analyze_formula(formula, system, max_rows=max_rows)
        value = None
        note = None
        if valuation is not None:
            try:
                checked = check_valuation(variables, valuation, system)
            except ValuationError:
                note = "Оценка с 1/2 недопустима для классической логики"
            else:
                value = run_program(program, checked, system)
        entries.append(ComparisonEntry(system, properties, value, note))

    properties_equal = len({(entry.properties.tautology, entry.properties.satisfiable,
                             entry.properties.identically_false) for entry in entries}) == 1
    all_values = [entry.value for entry in entries]
    values_equal = (len(set(all_values)) == 1 if valuation is not None and None not in all_values else None)

    differences = 0
    first = None
    for values in iter_interpretations(variables, LogicSystem.K3, max_rows=max_rows):
        a = run_program(program, values, LogicSystem.K3)
        b = run_program(program, values, LogicSystem.L3)
        if a != b:
            differences += 1
            if first is None:
                first = Difference(values, a, b)
    return LogicComparison(tuple(entries), properties_equal, values_equal,
                           differences == 0, differences, first)
