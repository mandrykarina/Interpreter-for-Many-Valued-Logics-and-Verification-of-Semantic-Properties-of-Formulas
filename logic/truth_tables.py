"""Ленивый перебор оценок и строк таблицы, с предварительными лимитами."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterator, Mapping, Sequence

from .ast import Formula, collect_variables
from .semantics import LogicSystem, compile_formula, logic_system, run_program

DEFAULT_MAX_ROWS = 100_000
HARD_MAX_ROWS = 200_000
HARD_MAX_WORK = 3_000_000  # (число строк) x (число узлов AST)


class AnalysisLimitError(ValueError):
    """Слишком большой полный перебор; результат нельзя считать доказанным."""


@dataclass(frozen=True)
class TruthRow:
    valuation: Mapping[str, int]  # внутренние коды значений
    result: int


def _check_limit(max_rows: int) -> None:
    if type(max_rows) is not int or not (1 <= max_rows <= HARD_MAX_ROWS):
        raise AnalysisLimitError(f"Лимит строк должен быть целым числом от 1 до {HARD_MAX_ROWS}")


def count_interpretations(n: int, system: LogicSystem | str) -> int:
    if type(n) is not int or n < 0:
        raise ValueError("Число переменных должно быть неотрицательным целым")
    return len(logic_system(system).values) ** n


def ensure_capacity(n: int, program_size: int, system: LogicSystem | str,
                    *, max_rows: int = DEFAULT_MAX_ROWS) -> int:
    _check_limit(max_rows)
    count = count_interpretations(n, system)
    if count > max_rows:
        raise AnalysisLimitError(
            f"Требуется {count} интерпретаций; установлен лимит {max_rows}. "
            "Полный анализ не проводился, итоговые свойства неизвестны."
        )
    if program_size > 0 and count * program_size > HARD_MAX_WORK:
        raise AnalysisLimitError(
            f"Требуется до {count * program_size} операций интерпретатора "
            f"(лимит {HARD_MAX_WORK}). Полный анализ не проводился."
        )
    return count


def iter_interpretations(names: Sequence[str], system: LogicSystem | str,
                         *, max_rows: int = DEFAULT_MAX_ROWS) -> Iterator[dict[str, int]]:
    logic = logic_system(system)
    name_tuple = tuple(names)
    if any(not isinstance(name, str) or not name for name in name_tuple):
        raise ValueError("Имена переменных должны быть непустыми строками")
    if len(name_tuple) != len(set(name_tuple)):
        raise ValueError("В списке переменных обнаружены дубликаты")
    ensure_capacity(len(name_tuple), 0, logic, max_rows=max_rows)
    for values in product(logic.values, repeat=len(name_tuple)):
        yield dict(zip(name_tuple, values))


def truth_table(formula: Formula, system: LogicSystem | str,
                *, max_rows: int = DEFAULT_MAX_ROWS) -> Iterator[TruthRow]:
    logic = logic_system(system)
    variables = collect_variables(formula)
    program = compile_formula(formula)
    ensure_capacity(len(variables), len(program), logic, max_rows=max_rows)
    for valuation in iter_interpretations(variables, logic, max_rows=max_rows):
        yield TruthRow(valuation, run_program(program, valuation, logic))
