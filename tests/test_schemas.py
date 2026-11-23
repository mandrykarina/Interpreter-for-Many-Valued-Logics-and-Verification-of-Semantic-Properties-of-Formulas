import pytest

from logic import Binary, Variable, match_schema, parse_formula, structurally_equal


def parse(text):
    return parse_formula(text)


def test_k_axiom_complex_instance():
    schema = parse("p -> (q -> p)")
    instance = parse("(a & b) -> ((r -> !s) -> (a & b))")
    binding = match_schema(schema, instance)
    assert binding is not None
    assert structurally_equal(binding["p"], parse("a & b"))
    assert structurally_equal(binding["q"], parse("r -> !s"))


@pytest.mark.parametrize("candidate", [
    "r -> (s -> q)",
    "r -> (s -> !r)",
    "r -> s -> r",  # left-assoc!, не экземпляр p -> (q -> p)
    "(a & b) -> (q -> (a | b))",
    "(a & b) -> (q -> a)",
    "(a & b) & (q -> (a & b))",
])
def test_noninstances_are_rejected(candidate):
    assert match_schema(parse("p -> (q -> p)"), parse(candidate)) is None


def test_same_variable_in_schema_requires_identical_substitution():
    schema = parse("p & p")
    assert match_schema(schema, parse("(a -> b) & (a -> b)")) is not None
    assert match_schema(schema, parse("(a -> b) & (a -> c)")) is None


def test_meta_variable_can_match_arbitrary_formula():
    assert match_schema(parse("p"), parse("!((a | b) -> (c & d))")) is not None


def test_no_partial_identifier_substitution():
    assert match_schema(parse("p1 -> p1"), parse("abc -> abc")) is not None
    assert match_schema(parse("p1 -> p1"), parse("abc -> abc_1")) is None


def test_a_tautology_does_not_automatically_match_ax_schema():
    assert match_schema(parse("p -> (q -> p)"), parse("p -> p")) is None


def test_schema_match_does_not_mutate_input():
    schema = parse("p -> (q -> p)")
    instance = parse("x -> (y -> x)")
    assert match_schema(schema, instance) == {"p": Variable("x"), "q": Variable("y")}
    assert structurally_equal(schema, parse("p -> (q -> p)"))
    assert structurally_equal(instance, parse("x -> (y -> x)"))
