from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from alphagraph.runtime.factor_dsl import parse_expression
from alphagraph.schemas import EvaluationResult, ExecutionResult


def run_backtest_from_expression(
    dataset_path: Path,
    expression: str,
) -> ExecutionResult:
    try:
        parsed = parse_expression(expression)
        frame = pd.read_csv(dataset_path, parse_dates=["date"]).sort_values(
            ["symbol", "date"]
        )
        frame["factor"] = _compute_factor(frame, parsed.metric, parsed.window)
        if parsed.negated:
            frame["factor"] = -frame["factor"]
        frame["forward_return"] = frame.groupby("symbol")["close"].pct_change().shift(-1)
        ranked = frame.dropna(subset=["factor", "forward_return"]).copy()
        ranked["factor_rank"] = ranked.groupby("date")["factor"].rank(
            method="first",
            pct=True,
        )
        ranked["position"] = 0
        ranked.loc[ranked["factor_rank"] >= 0.75, "position"] = 1
        ranked.loc[ranked["factor_rank"] <= 0.25, "position"] = -1
        active = ranked[ranked["position"] != 0].copy()
        if active.empty:
            raise ValueError("No active positions generated for factor.")

        active["weighted_return"] = active["position"] * active["forward_return"]
        daily = (
            active.groupby("date")
            .agg(
                weighted_return=("weighted_return", "sum"),
                positions=("position", lambda values: int(values.abs().sum())),
            )
            .reset_index()
            .sort_values("date")
        )
        daily["portfolio_return"] = daily["weighted_return"] / daily["positions"]

        returns = daily["portfolio_return"].astype(float)
        equity_curve = (1.0 + returns).cumprod()
        running_peak = equity_curve.cummax()
        drawdown = (equity_curve / running_peak) - 1.0
        sharpe = (
            float(np.sqrt(252) * returns.mean() / returns.std(ddof=0))
            if returns.std(ddof=0) > 0
            else 0.0
        )
        metrics = {
            "total_return": float(equity_curve.iloc[-1] - 1.0),
            "annualized_return": float((1.0 + returns.mean()) ** 252 - 1.0),
            "volatility": float(returns.std(ddof=0) * np.sqrt(252)),
            "sharpe": sharpe,
            "max_drawdown": float(drawdown.min()),
            "trade_count": int(active.shape[0]),
            "num_days": int(daily.shape[0]),
        }
        return ExecutionResult(success=True, metrics=metrics)
    except Exception as exc:  # pragma: no cover - exercised via service/API tests
        return ExecutionResult(success=False, stderr=str(exc), metrics={})


def evaluate_execution(
    expression: str,
    execution: ExecutionResult,
) -> EvaluationResult:
    reasons: list[str] = []
    summary_parts: list[str] = []

    if not execution.success:
        reasons.append("execution_failed")
        summary_parts.append("The generated code did not execute successfully.")
    else:
        trade_count = int(execution.metrics.get("trade_count", 0))
        sharpe = float(execution.metrics.get("sharpe", 0.0))
        max_drawdown = float(execution.metrics.get("max_drawdown", 0.0))

        if expression == "rank(close)":
            reasons.append("raw_price_level")
            summary_parts.append(
                "The factor uses raw price level, which is not comparable cross-sectionally."
            )
        if trade_count < 20:
            reasons.append("insufficient_trades")
            summary_parts.append("The backtest generated too few trades.")
        if sharpe < 0.35:
            reasons.append("weak_sharpe")
            summary_parts.append("Risk-adjusted performance is too weak for the demo gate.")
        if max_drawdown < -0.25:
            reasons.append("excess_drawdown")
            summary_parts.append("The factor breaches the maximum drawdown gate.")

    needs_revision = bool(reasons)
    summary = (
        " ".join(summary_parts)
        if summary_parts
        else "The factor cleared the deterministic evaluation gates."
    )
    return EvaluationResult(
        needs_revision=needs_revision,
        reasons=reasons,
        scorecard=execution.metrics,
        summary=summary,
    )


def _compute_factor(frame: pd.DataFrame, metric: str, window: int | None) -> pd.Series:
    if metric == "close_level":
        return frame["close"].astype(float)
    if metric == "ts_return" and window is not None:
        return frame.groupby("symbol")["close"].pct_change(window)
    raise ValueError(f"Unsupported metric: {metric}")
