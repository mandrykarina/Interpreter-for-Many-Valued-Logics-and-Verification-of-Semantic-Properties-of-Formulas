import pytest

from logic import FormulaSyntaxError, TokenKind, tokenize
from logic.lexer import MAX_SOURCE_LENGTH, MAX_TOKENS


@pytest.mark.parametrize("expression,expected", [
    ("p -> q", [(TokenKind.VARIABLE, "p", 0), (TokenKind.IMPLIES, "->", 2), (TokenKind.VARIABLE, "q", 5)]),
    ("¬p∧(q∨r)→s", [(TokenKind.NOT, "¬", 0), (TokenKind.VARIABLE, "p", 1),
                       (TokenKind.AND, "∧", 2), (TokenKind.LPAREN, "(", 3),
                       (TokenKind.VARIABLE, "q", 4), (TokenKind.OR, "∨", 5),
                       (TokenKind.VARIABLE, "r", 6), (TokenKind.RPAREN, ")", 7),
                       (TokenKind.IMPLIES, "→", 8), (TokenKind.VARIABLE, "s", 9)]),
    ("\tP_1\n| v", [(TokenKind.VARIABLE, "P_1", 1), (TokenKind.OR, "|", 5), (TokenKind.VARIABLE, "v", 7)]),
    ("αБβ_44", [(TokenKind.VARIABLE, "αБβ_44", 0)]),
])
def test_tokens_with_positions(expression, expected):
    tokens = tokenize(expression)
    assert [(token.kind, token.lexeme, token.position) for token in tokens[:-1]] == expected
    assert tokens[-1].kind == TokenKind.EOF
    assert tokens[-1].position == len(expression)
    for token in tokens:
        assert expression[token.position:token.end] == token.lexeme


def test_empty_token_stream_is_eof():
    assert [token.kind for token in tokenize(" \t \n")] == [TokenKind.EOF]


@pytest.mark.parametrize("source", ["@", "#", "_p", "123", "1p", "p $ q", "p => q", "p → ⊥", "a\u200bb", "p \u2060 q", "p < q", "p ; q"])
def test_lexical_error(source):
    with pytest.raises(FormulaSyntaxError) as raised:
        tokenize(source)
    error = raised.value
    assert 0 <= error.position <= len(source)
    assert error.line >= 1
    assert error.column >= 1
    assert "^" in str(error)


def test_multiline_error_reports_correct_location():
    source = "p ->\n (q | @)"
    with pytest.raises(FormulaSyntaxError) as captured:
        tokenize(source)
    assert captured.value.line == 2
    assert captured.value.column == 7
    assert "строка 2, столбец 7" in str(captured.value)


def test_very_long_source_rejected():
    with pytest.raises(FormulaSyntaxError, match="длиннее"):
        tokenize("p" * (MAX_SOURCE_LENGTH + 1))


def test_too_many_tokens_rejected():
    with pytest.raises(FormulaSyntaxError, match="токенов"):
        tokenize("!" * (MAX_TOKENS + 1))


def test_non_string_rejected():
    with pytest.raises(TypeError, match="строкой"):
        tokenize(None)
