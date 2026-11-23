"""Воспроизводимый экспорт результатов варианта 2 для отчёта.

Запуск: python main.py --export-results (создаёт каталог results/variant2).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from logic import (LogicSystem, analyze_formula, check_entailment, format_value,
                   truth_table)
from .variant2 import FORMULAS, RELATIONS, parsed_formulas, parsed_relations


SYSTEM_LABELS = {LogicSystem.CLASSICAL: "Классическая", LogicSystem.K3: "K3",
                 LogicSystem.L3: "L3"}


def _values(valuation) -> dict[str, str]:
    return {name: format_value(value) for name, value in valuation.items()}


def _assignment(valuation) -> str:
    return ", ".join(f"{name}={format_value(v)}" for name, v in valuation.items()) or "(нет переменных)"


def export_variant2(folder: str | Path) -> tuple[Path, ...]:
    """Создать точные таблицы F1–F5, сводки F и R, JSON и Markdown-обзор.

    Встроенных исключений для конкретных формул нет: вызываются общие алгоритмы.
    """
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    formula_rows = []
    relation_rows = []
    counter_rows = []
    json_data = {"formulae": {}, "relations": {}, "truth_code": {"0": "0", "1": "1/2", "2": "1"}}

    formulas = parsed_formulas()
    relations = parsed_relations()
    for name, formula in formulas.items():
        json_data["formulae"][name] = {"source": FORMULAS[name], "logics": {}}
        for system in LogicSystem:
            props = analyze_formula(formula, system)
            label = SYSTEM_LABELS[system]
            formula_rows.append([name, FORMULAS[name], label, props.total,
                                 props.false_count, props.half_count, props.true_count,
                                 int(props.tautology), int(props.satisfiable),
                                 int(props.identically_false),
                                 _assignment(props.witness.valuation) if props.witness else "",
                                 _assignment(props.counterexample.valuation) if props.counterexample else ""])
            json_data["formulae"][name]["logics"][system.value] = {
                "interpretations": props.total, "counts": {
                    "0": props.false_count, "1/2": props.half_count, "1": props.true_count},
                "tautology": props.tautology, "satisfiable": props.satisfiable,
                "identically_false": props.identically_false,
                "witness": _values(props.witness.valuation) if props.witness else None,
                "counterexample": {"valuation": _values(props.counterexample.valuation),
                                   "value": format_value(props.counterexample.result)}
                if props.counterexample else None,
            }
            filename = out / f"{name}_{system.value}_truth_table.csv"
            with filename.open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.writer(file, delimiter=";")
                writer.writerow([*props.variables, name])
                for row in truth_table(formula, system):
                    writer.writerow([*(format_value(row.valuation[var]) for var in props.variables),
                                     format_value(row.result)])
            written.append(filename)

    for name, relation in relations.items():
        json_data["relations"][name] = {"premises": list(relation.premise_sources),
                                        "conclusion": relation.conclusion_source, "logics": {}}
        for system in LogicSystem:
            outcome = check_entailment(relation.premises, relation.conclusion, system)
            label = SYSTEM_LABELS[system]
            ce = outcome.counterexample
            relation_rows.append([name, label, outcome.total_interpretations,
                                  outcome.premise_models, int(outcome.entails),
                                  int(outcome.vacuous), _assignment(ce.valuation) if ce else "",
                                  format_value(ce.conclusion_value) if ce else ""])
            if ce:
                counter_rows.append([name, label, _assignment(ce.valuation),
                                     *[format_value(v) for v in ce.premise_values],
                                     format_value(ce.conclusion_value)])
            json_data["relations"][name]["logics"][system.value] = {
                "interpretations": outcome.total_interpretations,
                "premise_models": outcome.premise_models,
                "entails": outcome.entails, "vacuous": outcome.vacuous,
                "counterexample": {
                    "valuation": _values(ce.valuation),
                    "premise_values": [format_value(v) for v in ce.premise_values],
                    "conclusion_value": format_value(ce.conclusion_value),
                } if ce else None,
            }

    for filename, header, rows in (
        ("formula_summary.csv", ["Формула", "Выражение", "Логика", "Интерпретаций",
                                 "Результат 0", "Результат 1/2", "Результат 1",
                                 "Общезначима (1/0)", "Выполнима (1/0)", "Тожд. ложна (1/0)",
                                 "Пример истинной оценки", "Контрпример общезначимости"], formula_rows),
        ("relations_summary.csv", ["Отношение", "Логика", "Интерпретаций", "Моделей посылок",
                                  "Следует (1/0)", "Без моделей посылок (1/0)",
                                  "Первый контрпример", "Значение заключения"], relation_rows),
        ("relations_counterexamples.csv", ["Отношение", "Логика", "Оценка", "Посылка 1",
                                          "Посылка 2", "Посылка 3", "Посылка 4", "Посылка 5",
                                          "Заключение"], counter_rows),
    ):
        path = out / filename
        with path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(header)
            writer.writerows(rows)
        written.append(path)

    path = out / "variant2_results.json"
    path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    written.append(path)

    lines = ["# Лабораторная №2 — результаты варианта 2",
             "", "Числа 0, 1/2 и 1 — математические значения истинности.",
             "Общезначимость: результат равен 1 во всех интерпретациях.",
             "Выполнимость: хотя бы одна интерпретация со значением 1.",
             "Следование: нет оценки, в которой все посылки равны 1, а заключение не равно 1.",
             "", "## Задание 1. Исследование формул", "",
             "| Формула | Классическая | K3 | L3 |", "|---|---|---|---|"]
    for name in FORMULAS:
        index = [entry for entry in formula_rows if entry[0] == name]
        lines.append("| " + name + " — `" + FORMULAS[name] + "` | " +
                     " | ".join("общезначима" if row[7] else "не общезначима" for row in index) + " |")
    lines.extend(["", "### Сводка семантических свойств", "",
                  "| Формула | Логика | Оценок | 0 | 1/2 | 1 | Общезначима | Выполнима | Тожд. ложна |",
                  "|---|---|---:|---:|---:|---:|---|---|---|"])
    for r in formula_rows:
        lines.append(f"| {r[0]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | " +
                     " | ".join("да" if v else "нет" for v in (r[7], r[8], r[9])) + " |")
    lines.extend(["", "Полные таблицы истинности находятся в файлах `F*_..._truth_table.csv`.",
                  "", "## Задание 2. Семантическое следование", "",
                  "| Отношение | Классическая | K3 | L3 |", "|---|---|---|---|"])
    for name in RELATIONS:
        entry = [row for row in relation_rows if row[0] == name]
        lines.append("| " + name + " | " +
                     " | ".join("следует" if row[4] else "не следует" for row in entry) + " |")
    for name, relation in relations.items():
        lines.extend(["", f"### {name}", "", "Посылки:"])
        for i, premise in enumerate(relation.premise_sources, 1):
            lines.append(f"{i}. `{premise}`")
        lines.extend(["", f"Заключение: `{relation.conclusion_source}`", ""])
        for system in LogicSystem:
            result = json_data["relations"][name]["logics"][system.value]
            lines.append(f"**{SYSTEM_LABELS[system]}:** " +
                         ("следует" if result["entails"] else "не следует") +
                         f"; моделей посылок: {result['premise_models']} из {result['interpretations']}.")
            if result["vacuous"]:
                lines.append("Посылки не имеют совместной модели со значением 1; следование вакуумно.")
            if result["counterexample"]:
                ex = result["counterexample"]
                lines.append("Контрпример: " + ", ".join(f"{k}={v}" for k, v in ex["valuation"].items()) +
                             "; посылки: " + ", ".join(ex["premise_values"]) +
                             "; заключение: " + ex["conclusion_value"] + ".")
            lines.append("")
    lines.extend(["## Воспроизведение", "", "`python main.py --export-results`", "",
                  "Значения получены полным перебором в реализации, без подгонки под вариант.", ""])
    path = out / "variant2_report_results.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    written.append(path)
    return tuple(written)
