"""Формулы и следования варианта 2 из задания лабораторной работы №2.

Данные отделены от алгоритма: семантический анализ не знает названий F1/R1.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from logic import Formula, parse_formula

FORMULAS: dict[str, str] = {
    "F1": "!!p -> p",
    "F2": "(p | !p) -> q",
    "F3": "(p -> q) & (q -> p)",
    "F4": "p & !p",
    "F5": "((p & q) -> r) -> (p -> (q -> r))",
}

RELATIONS: dict[str, tuple[tuple[str, ...], str]] = {
    "R1": (("(p & q) | r", "(p & q) -> s", "r -> s", "s -> t", "t -> u"), "u"),
    "R2": (("p -> !q", "!q -> r", "r -> s", "s -> t", "t -> u"), "!p | u"),
    "R3": (("(p -> q) | r", "p", "r -> q", "q -> s", "s -> t"), "t & (r -> r)"),
    "R4": (("(p -> q) | (r -> s)", "p", "r", "q -> t", "s -> t"), "t & q"),
}


@dataclass(frozen=True)
class Relation:
    name: str
    premise_sources: tuple[str, ...]
    conclusion_source: str
    premises: tuple[Formula, ...]
    conclusion: Formula


@lru_cache(maxsize=1)
def parsed_formulas() -> dict[str, Formula]:
    return {name: parse_formula(source) for name, source in FORMULAS.items()}


@lru_cache(maxsize=1)
def parsed_relations() -> dict[str, Relation]:
    return {
        name: Relation(name, sources, target,
                       tuple(parse_formula(source) for source in sources), parse_formula(target))
        for name, (sources, target) in RELATIONS.items()
    }
