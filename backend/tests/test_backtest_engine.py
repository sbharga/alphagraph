from pathlib import Path

from alphagraph.runtime.backtest_engine import (
    evaluate_execution,
    run_backtest_from_expression,
)


DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "prices.csv"


def test_backtest_metrics_show_momentum_factor_clears_demo_thresholds() -> None:
    execution = run_backtest_from_expression(
        dataset_path=DATASET_PATH,
        expression="rank(ts_return(close, 5))",
    )

    assert execution.success is True
    assert execution.metrics["trade_count"] >= 40
    assert execution.metrics["sharpe"] > 0.35
    assert execution.metrics["max_drawdown"] > -0.25


def test_evaluator_flags_raw_price_level_factor_as_methodologically_invalid() -> None:
    execution = run_backtest_from_expression(
        dataset_path=DATASET_PATH,
        expression="rank(close)",
    )

    evaluation = evaluate_execution(
        expression="rank(close)",
        execution=execution,
    )

    assert execution.success is True
    assert evaluation.needs_revision is True
    assert "raw_price_level" in evaluation.reasons
    assert "price" in evaluation.summary.lower()
