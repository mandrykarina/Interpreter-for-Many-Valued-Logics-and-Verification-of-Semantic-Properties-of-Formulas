"""Детерминированные генеративные проверки синтаксического анализа."""

import random

from logic import (Binary, BinaryOperator, FormulaSyntaxError, Negation, Variable,
                   collect_variables, format_formula, parse_formula, structurally_equal)

NAMES = ("p", "q", "v", "R2", "x_42", "α", "проверка")
OPERATORS = tuple(BinaryOperator)
INVALID_CHARS = ("@", "#", "?", "$", "[", "]", "=", ";", "~", "^", "•", "\u200b")


def random_ast(randomizer: random.Random, depth: int):
    if depth == 0 or randomizer.random() < .28:
        return Variable(randomizer.choice(NAMES))
    if randomizer.random() < .22:
        return Negation(random_ast(randomizer, depth - 1))
    return Binary(randomizer.choice(OPERATORS),
                  random_ast(randomizer, depth - 1),
                  random_ast(randomizer, depth - 1))


def test_10000_generated_ast_roundtrips():
    randomizer = random.Random(20261101)
    for index in range(10_000):
        ast = random_ast(randomizer, index % 7)
        text = format_formula(ast)
        parsed = parse_formula(text)
        assert structurally_equal(ast, parsed), (index, text)
        assert collect_variables(parsed) == collect_variables(ast)


def test_6000_corrupted_formulas_are_rejected():
    randomizer = random.Random(20261102)
    for index in range(6_000):
        ast = random_ast(randomizer, index % 6)
        text = format_formula(ast)
        position = randomizer.randint(0, len(text))
        malformed = text[:position] + randomizer.choice(INVALID_CHARS) + text[position:]
        try:
            parse_formula(malformed)
        except FormulaSyntaxError as error:
            assert error.position >= 0
        else:
            raise AssertionError(f"Принята испорченная формула: {malformed!r}")


def test_all_binary_operations_ordered_variable_pairs():
    for operator in OPERATORS:
        for left in NAMES:
            for right in NAMES:
                ast = Binary(operator, Variable(left), Variable(right))
                assert structurally_equal(ast, parse_formula(format_formula(ast)))


def test_nested_unary_vs_binary_non_equivalence():
    assert not structurally_equal(parse_formula("!(p & q)"), parse_formula("!p & q"))
    assert not structurally_equal(parse_formula("p -> (q -> r)"), parse_formula("p -> q -> r"))


def test_8000_lexically_valid_but_syntactically_broken_expressions():
    """Ошибки именно грамматики, а не одиночные недопустимые символы."""
    randomizer = random.Random(20261103)
    mutations = (
        lambda s: f"({s} & )",              # нет правого операнда
        lambda s: f"({s} -> -> p)",         # двойная импликация
        lambda s: f"({s} {s})",             # две формулы без связки
        lambda s: f"({s}))",                # лишняя закрывающая скобка
        lambda s: f"(& {s})",               # нет левого операнда
        lambda s: f"({s} | | p)",            # повтор операции
        lambda s: f"({s} ->",               # не хватает конца
        lambda s: f"({s} (p))",             # подформула без операции
    )
    for index in range(8_000):
        source = format_formula(random_ast(randomizer, index % 6))
        invalid = mutations[index % len(mutations)](source)
        try:
            parse_formula(invalid)
        except FormulaSyntaxError:
            pass
        else:
            raise AssertionError(f"Парсер принял ошибочную конструкцию: {invalid!r}")
