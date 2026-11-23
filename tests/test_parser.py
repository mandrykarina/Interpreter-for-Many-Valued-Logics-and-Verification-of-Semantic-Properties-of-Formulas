import pytest

from logic import (Binary, BinaryOperator, FormulaSyntaxError, Negation, Variable,
                   collect_variables, format_formula, format_fully_parenthesized, format_tree, parse_formula, structurally_equal)
from logic.parser import MAX_AST_NODES, MAX_NESTING


def node(name):
    return Variable(name)


def implies(a, b):
    return Binary(BinaryOperator.IMPLIES, a, b)


def conj(a, b):
    return Binary(BinaryOperator.AND, a, b)


def disj(a, b):
    return Binary(BinaryOperator.OR, a, b)


@pytest.mark.parametrize("source,expected", [
    ("p", node("p")),
    ("v", node("v")),
    ("result_42", node("result_42")),
    ("p -> q -> r", implies(implies(node("p"), node("q")), node("r"))),
    ("p -> q -> (q -> q)", implies(implies(node("p"), node("q")), implies(node("q"), node("q")))),
    ("p -> (q -> r)", implies(node("p"), implies(node("q"), node("r")))),
    ("(p -> q) -> r", implies(implies(node("p"), node("q")), node("r"))),
    ("(p -> q) -> (q -> q)", implies(implies(node("p"), node("q")), implies(node("q"), node("q")))),
    ("p -> (q -> (q -> q))", implies(node("p"), implies(node("q"), implies(node("q"), node("q"))))),
    ("!p & q | r -> s", implies(disj(conj(Negation(node("p")), node("q")), node("r")), node("s"))),
    ("p & q & r", conj(conj(node("p"), node("q")), node("r"))),
    ("p | q | r", disj(disj(node("p"), node("q")), node("r"))),
    ("p & (q | r)", conj(node("p"), disj(node("q"), node("r")))),
    ("!(p -> q)", Negation(implies(node("p"), node("q")))),
    ("!!!p", Negation(Negation(Negation(node("p"))))),
    ("((p))", node("p")),
    ("P | p", disj(node("P"), node("p"))),
    ("¬α∨β→γ", implies(disj(Negation(node("α")), node("β")), node("γ"))),
    ("p \u00a0->\t q\n-> r", implies(implies(node("p"), node("q")), node("r"))),
])
def test_ast_structures(source, expected):
    assert parse_formula(source) == expected


@pytest.mark.parametrize("malformed", [
    "", "  \t\n", "!", "¬", "()", "( )", "(( ))", "p ->", "p →", "-> p", "→ p",
    "p -> -> q", "p → → q", "p & | q", "p || q", "p && q", "p ∧∧ q", "p q",
    "(p q)", "p\nq", "(p", "p)", ")p(", "(p -> q", "p -> (q))", "(p)(q)",
    "p # q", "p xor q", "p => q", "p v q", "a_ b", "_x", "1p", "p . q",
    "¬∧p", "p->(q|)", "p->(!)", "((p -> q) |)", "(p -> q)) (r)",
    "p -> q ?", "@p", "p + q", "f()", "p; q", "p : q", "¬ )", "(¬)",
    "(p) (q)", "p → q r", "p\u200b->q", "p -> ¬", "p | !", "(p -> q))",
])
def test_malformed_formula_rejected(malformed):
    with pytest.raises(FormulaSyntaxError) as raised:
        parse_formula(malformed)
    error = raised.value
    assert 0 <= error.position <= len(malformed)
    assert "строка" in str(error)
    assert "^" in str(error)


def test_long_identifier_and_unicode():
    name = "переменная_" + "x9" * 700
    assert collect_variables(parse_formula(f"{name} & {name}")) == (name,)


def test_variable_sorting_and_case_sensitivity():
    assert collect_variables(parse_formula("b & A & b & a & α")) == ("A", "a", "b", "α")


def test_all_spaces_are_ignored():
    assert parse_formula("\np\t->\n \u00a0q") == parse_formula("p→q")


def test_tree_representation():
    formula = parse_formula("p -> q -> r")
    assert format_tree(formula).splitlines() == ["→", "  →", "    p", "    q", "  r"]
    assert format_fully_parenthesized(formula) == "((p → q) → r)"
    assert format_formula(formula) == "p → q → r"


def test_parenthesized_roundtrip():
    expressions = [
        "(p | !p) -> q", "((p & q) -> r) -> (p -> (q -> r))",
        "(p -> q) & (q -> p)", "p -> q -> (q -> q)", "¬¬p → p",
        "!(!(!p | !q) & r)", "α1 & (β_2 -> γ3)"
    ]
    for expression in expressions:
        ast = parse_formula(expression)
        assert structurally_equal(ast, parse_formula(format_formula(ast))), expression


def test_nesting_limit_at_boundary():
    assert parse_formula("(" * MAX_NESTING + "p" + ")" * MAX_NESTING) == node("p")
    assert parse_formula("!" * MAX_NESTING + "p")
    with pytest.raises(FormulaSyntaxError, match="глубина"):
        parse_formula("(" * (MAX_NESTING + 1) + "p" + ")" * (MAX_NESTING + 1))
    with pytest.raises(FormulaSyntaxError, match="глубина"):
        parse_formula("!" * (MAX_NESTING + 1) + "p")
    with pytest.raises(FormulaSyntaxError, match="глубина"):
        parse_formula("(" * 80 + "!" * 50 + "p" + ")" * 80)


def test_node_limit():
    with pytest.raises(FormulaSyntaxError, match="узлов"):
        parse_formula(" -> ".join("p" for _ in range((MAX_AST_NODES // 2) + 2)))


def test_length_and_eof_fully_checked():
    for expression in ("p  q", "p ¬q", "p -> q (r)", "(p) q", "p -> q   :"):
        with pytest.raises(FormulaSyntaxError):
            parse_formula(expression)


def test_long_flat_chain_is_supported_without_recursion_error():
    count = 900
    ast = parse_formula(" -> ".join("p" for _ in range(count)))
    assert collect_variables(ast) == ("p",)
    assert format_tree(ast).count("→") == count - 1
    formatted = format_formula(ast)
    assert formatted.count("→") == count - 1
    assert structurally_equal(ast, parse_formula(formatted))


def test_structural_equality_very_deep_left_chain():
    a = parse_formula(" -> ".join("p" for _ in range(800)))
    b = parse_formula(" -> ".join("p" for _ in range(800)))
    c = parse_formula(" -> ".join(["p"] * 799 + ["q"]))
    assert structurally_equal(a, b)
    assert not structurally_equal(a, c)


def test_compact_roundtrip_long_left_nested_chain():
    count = 1800
    ast = parse_formula(" -> ".join("p" for _ in range(count)))
    compact = format_formula(ast)
    assert compact.count("→") == count - 1
    assert structurally_equal(ast, parse_formula(compact))


def test_formatter_respects_equal_priority_right_nested():
    for source in ("p -> (q -> r)", "p & (q & r)", "p | (q | r)",
                   "(p -> q) & r", "p & (q -> r)", "!(p -> q)"):
        ast = parse_formula(source)
        assert structurally_equal(ast, parse_formula(format_formula(ast)))
