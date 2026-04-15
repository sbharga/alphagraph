from pathlib import Path

import pytest

from alphagraph.runtime.factor_dsl import parse_expression


def test_parse_supports_ranked_short_term_return_expression() -> None:
    expression = parse_expression("rank(ts_return(close, 5))")

    assert expression.root == "rank"
    assert expression.metric == "ts_return"
    assert expression.field == "close"
    assert expression.window == 5
    assert expression.negated is False


def test_parse_supports_negated_mean_reversion_expression() -> None:
    expression = parse_expression("rank(-ts_return(close, 3))")

    assert expression.root == "rank"
    assert expression.metric == "ts_return"
    assert expression.field == "close"
    assert expression.window == 3
    assert expression.negated is True


@pytest.mark.parametrize(
    "raw_expression",
    [
        "rank(ts_return(volume, 5))",
        "rank(ts_return(close, 0))",
        "rank(close, 5)",
        "close",
    ],
)
def test_parse_rejects_invalid_factor_expressions(raw_expression: str) -> None:
    with pytest.raises(ValueError):
        parse_expression(raw_expression)
