"""Синтаксическое ядро интерпретатора лабораторной № 2."""

from .ast import Binary, BinaryOperator, Formula, Negation, Variable, collect_variables, format_formula, format_fully_parenthesized, format_tree
from .lexer import FormulaSyntaxError, Token, TokenKind, tokenize
from .parser import MAX_AST_NODES, MAX_NESTING, parse_formula
from .schemas import match_schema, structurally_equal

__all__ = [
    "Binary", "BinaryOperator", "Formula", "Negation", "Variable",
    "collect_variables", "format_formula", "format_fully_parenthesized", "format_tree", "FormulaSyntaxError",
    "Token", "TokenKind", "tokenize", "MAX_AST_NODES", "MAX_NESTING",
    "parse_formula", "match_schema", "structurally_equal",
]

from .semantics import (LogicSystem, ValuationError, binary, check_valuation, compile_formula,
                        evaluate, format_value, logic_system, negate, parse_value)
from .truth_tables import (AnalysisLimitError, TruthRow, count_interpretations,
                           iter_interpretations, truth_table)
from .properties import (ComparisonEntry, Difference, FormulaProperties, LogicComparison,
                         analyze_formula, compare_logics)

__all__.extend([
    "LogicSystem", "ValuationError", "binary", "check_valuation", "compile_formula",
    "evaluate", "format_value", "logic_system", "negate", "parse_value",
    "AnalysisLimitError", "TruthRow", "count_interpretations", "iter_interpretations",
    "truth_table", "ComparisonEntry", "Difference", "FormulaProperties", "LogicComparison",
    "analyze_formula", "compare_logics",
])

from .entailment import EntailmentCounterexample, EntailmentResult, check_entailment

__all__.extend(["EntailmentCounterexample", "EntailmentResult", "check_entailment"])
