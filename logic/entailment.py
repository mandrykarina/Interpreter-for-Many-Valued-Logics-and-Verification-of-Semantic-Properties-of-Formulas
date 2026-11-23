"""Проверка семантического следования полным перебором (выделенное значение = 2).

Внутренние коды: 0 = ложь, 1 = 1/2, 2 = истина. При отсутствии
контрпримера следование верно; отсутствие моделей посылок выделяется особо.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .ast import Formula, collect_variables
from .semantics import LogicSystem, compile_formula, logic_system, run_program
from .truth_tables import DEFAULT_MAX_ROWS, ensure_capacity, iter_interpretations


@dataclass(frozen=True)
class EntailmentCounterexample:
    valuation: Mapping[str, int]
    premise_values: tuple[int, ...]
    conclusion_value: int


@dataclass(frozen=True)
class EntailmentResult:
    system: LogicSystem
    variables: tuple[str, ...]
    total_interpretations: int
    premise_models: int
    entails: bool
    counterexample: EntailmentCounterexample | None

    @property
    def vacuous(self) -> bool:
        """Следование истинно из-за отсутствия моделей всех посылок."""
        return self.premise_models == 0


def check_entailment(premises: Sequence[Formula], conclusion: Formula,
                     system: LogicSystem | str,
                     *, max_rows: int = DEFAULT_MAX_ROWS) -> EntailmentResult:
    """Проверить Γ ⊨ B. Не останавливается на первом контрпримере:
    число моделей Γ определяется по ВСЕМ интерпретациям.

    Пустые Γ допустимы: Γ ⊨ B тогда и только тогда, когда B общезначима.
    Ограничения гарантируют, что неполная проверка не вернёт положительный результат.
    """
    logic = logic_system(system)
    premises = tuple(premises)
    # Проверка типов не допускает случайно передать строку вместо набора AST.
    programs = tuple(compile_formula(formula) for formula in premises)
    conclusion_program = compile_formula(conclusion)
    names = tuple(sorted(set(collect_variables(conclusion)).union(
        *(collect_variables(formula) for formula in premises)
    )))
    # Предполагаемая верхняя оценка стоимости: для каждой строки вычисляем все формулы.
    # Общий бюджет учитывает сумму длин программ, а не только длину одной посылки.
    total = ensure_capacity(len(names), sum(map(len, programs)) + len(conclusion_program),
                            logic, max_rows=max_rows)
    models = 0
    counterexample = None
    for valuation in iter_interpretations(names, logic, max_rows=max_rows):
        premise_values = tuple(run_program(program, valuation, logic) for program in programs)
        if all(value == 2 for value in premise_values):
            models += 1
            conclusion_value = run_program(conclusion_program, valuation, logic)
            if conclusion_value != 2 and counterexample is None:
                counterexample = EntailmentCounterexample(
                    dict(valuation), premise_values, conclusion_value
                )
    return EntailmentResult(logic, names, total, models, counterexample is None,
                            counterexample)
