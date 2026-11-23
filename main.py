"""Консоль лабораторной №2: интерпретация и следование, вариант 2."""
from __future__ import annotations

import argparse
from pathlib import Path

from logic import (AnalysisLimitError, FormulaSyntaxError, LogicSystem, ValuationError,
                   analyze_formula, collect_variables, compare_logics, count_interpretations,
                   evaluate, check_entailment, format_formula, format_fully_parenthesized, format_tree,
                   format_value, parse_formula, parse_value, truth_table)
from logic.truth_tables import DEFAULT_MAX_ROWS, HARD_MAX_WORK, ensure_capacity
from logic.semantics import compile_formula
from variants.variant2 import FORMULAS, RELATIONS, parsed_formulas, parsed_relations
from variants.export import export_variant2


SYSTEMS = {"1": LogicSystem.CLASSICAL, "2": LogicSystem.K3, "3": LogicSystem.L3}


class UserRequestedExit(Exception):
    """Глобальный выход из любого вложенного меню или запроса оценки."""


def _read_input(prompt: str) -> str:
    result = input(prompt)
    if result.strip().lower() in (":exit", ":quit"):
        raise UserRequestedExit
    return result
MENU = """
  1. Выбрать логику
  2. Проверить синтаксис и дерево формулы
  3. Вычислить формулу при заданных значениях
  4. Построить полную таблицу истинности
  5. Исследовать семантические свойства
  6. Сравнить классическую логику, K3 и L3
  7. Справка
  8. Проверить произвольное логическое следование
  9. Задания варианта 2 (F1–F5, R1–R4)
  0. Выход
Можно также сразу ввести формулу (режим проверки синтаксиса).
"""


def show_formula(source: str) -> bool:
    """Режим этапа 1 сохранён для совместимости и регрессионных тестов."""
    try:
        ast = parse_formula(source)
    except FormulaSyntaxError as error:
        print("ОШИБКА СИНТАКСИСА")
        print(error)
        return False
    print("ПРИНЯТО")
    print("Однозначная запись:", format_formula(ast))
    print("Полная расстановка скобок:", format_fully_parenthesized(ast))
    names = collect_variables(ast)
    print("Переменные:", ", ".join(names))
    print("Дерево формулы:")
    print(format_tree(ast))
    return True


def _ask_formula():
    source = _read_input("Формула (:back — возврат)> ")
    if source.strip().lower() == ":back":
        return None
    try:
        return parse_formula(source)
    except FormulaSyntaxError as error:
        print("ОШИБКА СИНТАКСИСА")
        print(error)
        return None


def _ask_valuation(names: tuple[str, ...], system: LogicSystem) -> dict[str, int] | None:
    print("Введите 0 или 1" + (", также 1/2 (0.5, ½)" if system is not LogicSystem.CLASSICAL else ""))
    valuation = {}
    for name in names:
        while True:
            source = _read_input(f"  {name} = ")
            if source.strip().lower() == ":back":
                return None
            try:
                valuation[name] = parse_value(source, system)
                break
            except ValuationError as error:
                print("ОШИБКА ОЦЕНКИ:", error)
    return valuation


def _fmt_assignment(valuation) -> str:
    return ", ".join(f"{name}={format_value(value)}" for name, value in valuation.items()) or "(переменных нет)"


def _report_properties(data) -> None:
    print(f"Логика: {data.system.title}. Переменные: {', '.join(data.variables)}")
    print(f"Все интерпретации проверены: {data.total}")
    print(f"Значений 0: {data.false_count}; 1/2: {data.half_count}; 1: {data.true_count}")
    print("Общезначимость:", "ДА" if data.tautology else "НЕТ")
    print("Выполнимость:", "ДА" if data.satisfiable else "НЕТ")
    print("Тождественная ложность:", "ДА" if data.identically_false else "НЕТ")
    if data.witness is not None:
        print("Пример истинной оценки:", _fmt_assignment(data.witness.valuation))
    if data.counterexample is not None:
        print("Контрпример общезначимости:", _fmt_assignment(data.counterexample.valuation),
              "->", format_value(data.counterexample.result))
    if not data.identically_false and data.nonzero_example is not None:
        print("Пример ненулевого значения:", _fmt_assignment(data.nonzero_example.valuation),
              "->", format_value(data.nonzero_example.result))


def _select_system(current: LogicSystem) -> LogicSystem:
    print("Системы: 1 — классическая, 2 — Клини K3, 3 — Лукасевича L3")
    while True:
        choice = _read_input("Номер (:back — отмена)> ").strip().lower()
        if choice == ":back":
            return current
        found = SYSTEMS.get(choice)
        if found is not None:
            print("Выбрана логика:", found.title)
            return found
        print("Неверный номер: введите 1, 2 или 3")


def _calculate(system: LogicSystem) -> None:
    ast = _ask_formula()
    if ast is None:
        return
    values = _ask_valuation(collect_variables(ast), system)
    if values is None:
        return
    result = evaluate(ast, values, system)
    print("Формула:", format_formula(ast))
    print("Оценка:", _fmt_assignment(values))
    print("Логика:", system.title)
    print("Значение истинности:", format_value(result))


def _table(system: LogicSystem) -> None:
    ast = _ask_formula()
    if ast is None:
        return
    names = collect_variables(ast)
    size = len(compile_formula(ast))
    total = ensure_capacity(len(names), size, system)
    print(f"Строк в таблице: {total}")
    if total > 100:
        print("ВНИМАНИЕ: вывод большого количества строк в консоль.")
        answer = _read_input("Напечатать ВСЕ строки? (да/нет)> ").strip().lower()
        if answer not in ("да", "д", "yes", "y"):
            print("Вывод таблицы отменён, анализ не выполнялся.")
            return
    print(" | ".join((*names, format_formula(ast))))
    print("-" * min(100, (len(names) + 1) * 8))
    for row in truth_table(ast, system):
        print(" | ".join([*(format_value(row.valuation[name]) for name in names), format_value(row.result)]))
    print(f"Таблица завершена: {total} из {total} строк.")


def _properties(system: LogicSystem) -> None:
    ast = _ask_formula()
    if ast is not None:
        _report_properties(analyze_formula(ast, system))


def _compare() -> None:
    ast = _ask_formula()
    if ast is None:
        return
    print("Сравнение свойств всегда выполняется на полном наборе оценок каждой логики.")
    answer = _read_input("Задать общую оценку переменных? (да/нет)> ").strip().lower()
    valuation = None
    if answer in ("да", "д", "y", "yes"):
        valuation = _ask_valuation(collect_variables(ast), LogicSystem.K3)
        if valuation is None:
            return
    comparison = compare_logics(ast, valuation)
    for entry in comparison.entries:
        print("\n", entry.system.title, sep="")
        data = entry.properties
        print(f"  Общезначимость: {'ДА' if data.tautology else 'НЕТ'}; "
              f"выполнимость: {'ДА' if data.satisfiable else 'НЕТ'}; "
              f"тождественная ложность: {'ДА' if data.identically_false else 'НЕТ'}")
        print(f"  Проверено {data.total} оценок. Распределение 0 / 1/2 / 1: "
              f"{data.false_count} / {data.half_count} / {data.true_count}")
        if valuation is not None:
            if entry.note:
                print("  Значение по заданной оценке: неприменимо —", entry.note)
            else:
                print("  Значение по заданной оценке:", format_value(entry.value))
    print("\nСемантические свойства совпадают во всех логиках:",
          "ДА" if comparison.properties_equal else "НЕТ")
    if valuation is None:
        print("Значения одной оценки: не сравнивались (оценка не задана).")
    elif comparison.values_equal is None:
        print("Значения во всех трёх логиках: несопоставимы (1/2 недопустима в классической).")
    else:
        print("Значения по заданной оценке во всех трёх логиках совпадают:",
              "ДА" if comparison.values_equal else "НЕТ")
    print("Функции K3 и L3 совпадают на всех трёхзначных оценках:",
          "ДА" if comparison.k3_l3_equal_on_all else "НЕТ")
    print("Количество различающихся оценок K3/L3:", comparison.k3_l3_difference_count)
    if comparison.first_difference is not None:
        example = comparison.first_difference
        print("Первое различие:", _fmt_assignment(example.valuation),
              f"-> K3={format_value(example.k3_value)}, L3={format_value(example.l3_value)}")


def _read_formula_until_valid(prompt: str):
    """Возврат по :back; синтаксическая ошибка не отменяет операцию."""
    while True:
        source = _read_input(prompt)
        if source.strip().lower() == ":back":
            return None
        try:
            return parse_formula(source)
        except FormulaSyntaxError as error:
            print("ОШИБКА СИНТАКСИСА:", error)
            print("Повторите ввод или :back для отмены.")


def _report_entailment(result, premise_sources: tuple[str, ...], conclusion_source: str) -> None:
    print("Логика:", result.system.title)
    print("Посылки:")
    if not premise_sources:
        print("  (пустой набор)")
    for index, source in enumerate(premise_sources, 1):
        print(f"  A{index}: {source}")
    print("Заключение:", conclusion_source)
    print("Все интерпретации проверены:", result.total_interpretations)
    print("Совместных моделей посылок (все имеют значение 1):", result.premise_models)
    print("СЛЕДУЕТ" if result.entails else "НЕ СЛЕДУЕТ")
    if result.vacuous:
        print("ВНИМАНИЕ: ни одна интерпретация не удовлетворяет всем посылкам ")
        print("со значением 1. Следование выполняется вакуумно (контрпримеров нет).")
    if result.counterexample is not None:
        example = result.counterexample
        print("Контрпример:", _fmt_assignment(example.valuation))
        for index, value in enumerate(example.premise_values, 1):
            print(f"  A{index} = {format_value(value)}")
        print("  Заключение =", format_value(example.conclusion_value))


def _entailment(system: LogicSystem) -> None:
    print("Проверка A1, ..., An ⊨ B. Посылки вводятся по одной.")
    print("Пустая строка завершает список посылок; :back отменяет операцию.")
    sources: list[str] = []
    premises = []
    while True:
        source = _read_input(f"Посылка {len(premises) + 1} (Enter — завершить)> ")
        if source.strip().lower() == ":back":
            return
        if not source.strip():
            break
        try:
            premises.append(parse_formula(source))
            sources.append(source)
        except FormulaSyntaxError as error:
            print("ОШИБКА СИНТАКСИСА:", error)
            print("Повторите текущую посылку, она не добавлена.")
    conclusion = _read_formula_until_valid("Заключение (:back — отмена)> ")
    if conclusion is None:
        return
    _report_entailment(check_entailment(premises, conclusion, system),
                       tuple(sources), format_formula(conclusion))


def _variant_summary() -> None:
    print("\nЗАДАНИЕ 1. СВОЙСТВА ФОРМУЛ: общезначимость, выполнимость, тождественная ложность")
    for name, formula in parsed_formulas().items():
        print(f"{name}: {FORMULAS[name]}")
        for system in LogicSystem:
            props = analyze_formula(formula, system)
            print(f"  {system.title}: {props.total} оценок; "
                  f"общезначима={'ДА' if props.tautology else 'НЕТ'}, "
                  f"выполнима={'ДА' if props.satisfiable else 'НЕТ'}, "
                  f"тождественно ложна={'ДА' if props.identically_false else 'НЕТ'}")
    print("\nЗАДАНИЕ 2. ОТНОШЕНИЯ СЛЕДОВАНИЯ")
    for name, relation in parsed_relations().items():
        print(f"{name}: {', '.join(relation.premise_sources)} ⊨ {relation.conclusion_source}")
        for system in LogicSystem:
            result = check_entailment(relation.premises, relation.conclusion, system)
            print(f"  {system.title}: {'СЛЕДУЕТ' if result.entails else 'НЕ СЛЕДУЕТ'}; "
                  f"моделей посылок: {result.premise_models}")
            if result.vacuous:
                print("  Посылки не имеют совместной модели со значением 1")
            if result.counterexample:
                print("  Контрпример:", _fmt_assignment(result.counterexample.valuation),
                      "->", format_value(result.counterexample.conclusion_value))


def _variant_menu(system: LogicSystem) -> None:
    while True:
        print("\nВАРИАНТ 2 (текущая логика: " + system.title + ")")
        print("1. Исследовать одну из формул F1–F5")
        print("2. Проверить одно из следований R1–R4")
        print("3. Показать сводку всех 9 заданий по трём логикам")
        print("4. Сохранить все результаты и полные таблицы в results/variant2")
        print("0. Вернуться в главное меню")
        action = _read_input("Выбор> ").strip().lower()
        if action in ("0", ":back"):
            return
        if action == "1":
            print("Формулы:", "; ".join(f"{k}: {v}" for k, v in FORMULAS.items()))
            selection = _read_input("Имя формулы (:back — отмена)> ").strip().upper()
            formula = parsed_formulas().get(selection)
            if formula is None:
                print("Неизвестная формула. Выберите F1–F5.")
                continue
            _report_properties(analyze_formula(formula, system))
            if _read_input("Показать ПОЛНУЮ таблицу истинности? (да/нет)> ").strip().lower() in ("да", "д", "yes", "y"):
                names = collect_variables(formula)
                print(" | ".join((*names, selection)))
                for row in truth_table(formula, system):
                    print(" | ".join((*(format_value(row.valuation[name]) for name in names),
                                      format_value(row.result))))
        elif action == "2":
            print("Отношения:", ", ".join(RELATIONS))
            selection = _read_input("Имя отношения (:back — отмена)> ").strip().upper()
            relation = parsed_relations().get(selection)
            if relation is None:
                print("Неизвестное отношение. Выберите R1–R4.")
                continue
            outcome = check_entailment(relation.premises, relation.conclusion, system)
            _report_entailment(outcome, relation.premise_sources, relation.conclusion_source)
        elif action == "3":
            _variant_summary()
        elif action == "4":
            files = export_variant2(Path(__file__).resolve().parent / "results" / "variant2")
            print(f"Результаты сохранены: {len(files)} файлов, "
                  "каталог results/variant2")
        else:
            print("Неизвестный пункт меню.")


def _help() -> None:
    print("Приоритеты: ¬ > ∧ > ∨ > →. Все бинарные связки связываются слева.")
    print("Пример: p -> q -> (q -> q) равен (p -> q) -> (q -> q).")
    print("Ввод: p, q, v, имя_2; операции !/¬, &/∧, |/∨, ->/→; круглые скобки.")
    print("В пользовательском вводе 1 — истина, 0 — ложь, 1/2 — промежуточное значение.")
    print(f"Лимиты: {DEFAULT_MAX_ROWS} строк и {HARD_MAX_WORK} вычислительных шагов; "
          "при превышении анализ не производится.")
    print(":back отменяет ввод формулы или оценок; :exit — завершает работу.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Лабораторная № 2, вариант 2: интерпретатор многозначной логики")
    parser.add_argument("--formula", type=str, help="Проверить синтаксис формулы (режим первого этапа)")
    parser.add_argument("--analyze", type=str, help="Исследовать формулу в выбранной логике")
    parser.add_argument("--entails", type=str, help="Проверить, следует ли заключение из посылок")
    parser.add_argument("--premise", action="append", default=[], help="Посылка (параметр повторяется)")
    parser.add_argument("--variant2", action="store_true", help="Показать сводку F1–F5 и R1–R4")
    parser.add_argument("--export-results", nargs="?", const=str(Path(__file__).resolve().parent / "results" / "variant2"), metavar="PATH",
                        help="Сгенерировать результаты варианта 2 в указанный каталог")
    parser.add_argument("--logic", choices=[s.value for s in LogicSystem], default="classical", help="Логика для --analyze")
    options = parser.parse_args(argv)
    if options.premise and options.entails is None:
        parser.error("--premise требует --entails")
    if options.entails is not None:
        try:
            asts = tuple(parse_formula(source) for source in options.premise)
            conclusion = parse_formula(options.entails)
            result = check_entailment(asts, conclusion, options.logic)
            _report_entailment(result, tuple(options.premise), options.entails)
            return 0
        except (FormulaSyntaxError, AnalysisLimitError, ValueError) as error:
            print("ОШИБКА:", error)
            return 2
    if options.variant2:
        try:
            _variant_summary()
            return 0
        except (AnalysisLimitError, ValueError) as error:
            print("ОШИБКА:", error)
            return 2
    if options.export_results is not None:
        try:
            generated = export_variant2(Path(options.export_results))
            print(f"Результаты сохранены: {len(generated)} файлов, "
                  f"каталог {Path(options.export_results).resolve()}")
            return 0
        except (OSError, AnalysisLimitError, ValueError) as error:
            print("ОШИБКА ЭКСПОРТА:", error)
            return 2
    if options.formula is not None:
        return 0 if show_formula(options.formula) else 2
    if options.analyze is not None:
        try:
            _report_properties(analyze_formula(parse_formula(options.analyze), options.logic))
            return 0
        except (FormulaSyntaxError, AnalysisLimitError, ValuationError, ValueError) as error:
            print("ОШИБКА:", error)
            return 2

    system = LogicSystem.CLASSICAL
    print("Лабораторная № 2, вариант 2. Семантический интерпретатор: классика, K3, L3.")
    print("Для выхода: :exit. Для справки: :help.")
    print(MENU)
    while True:
        try:
            print("Текущая логика:", system.title)
            command = _read_input("Действие или формула> ").strip()
            if command.lower() in ("0", ":exit", ":quit"):
                print("Завершение работы.")
                return 0
            if command == "1":
                system = _select_system(system)
            elif command == "2":
                source = _read_input("Формула (:back — возврат)> ")
                if source.strip().lower() != ":back":
                    show_formula(source)
            elif command == "3":
                _calculate(system)
            elif command == "4":
                _table(system)
            elif command == "5":
                _properties(system)
            elif command == "6":
                _compare()
            elif command == "8":
                _entailment(system)
            elif command == "9":
                _variant_menu(system)
            elif command in ("7", ":help"):
                _help()
            elif not command:
                print("Введите пункт меню или формулу. Справка: :help.")
            else:
                show_formula(command)
        except (EOFError, KeyboardInterrupt, UserRequestedExit):
            print("\nЗавершение работы. Если вывод таблицы прерван, она неполная.")
            return 0
        except (AnalysisLimitError, ValuationError, OSError) as error:
            print("ОШИБКА:", error)
            print("Результат не вычислен; вернитесь к меню или введите другую формулу.")


if __name__ == "__main__":
    raise SystemExit(main())
