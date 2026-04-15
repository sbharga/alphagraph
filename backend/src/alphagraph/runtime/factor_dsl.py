from __future__ import annotations

import re

from alphagraph.schemas import ParsedExpression


EXPRESSION_PATTERN = re.compile(
    r"^rank\((?P<body>close|-?ts_return\(close,\s*(?P<window>\d+)\))\)$"
)


def parse_expression(expression: str) -> ParsedExpression:
    match = EXPRESSION_PATTERN.fullmatch(expression.strip())
    if not match:
        raise ValueError(f"Unsupported factor expression: {expression}")

    body = match.group("body")
    if body == "close":
        return ParsedExpression(
            root="rank",
            metric="close_level",
            field="close",
            negated=False,
        )

    window = int(match.group("window") or 0)
    if window <= 0:
        raise ValueError(f"Unsupported factor window: {expression}")

    return ParsedExpression(
        root="rank",
        metric="ts_return",
        field="close",
        window=window,
        negated=body.startswith("-"),
    )
