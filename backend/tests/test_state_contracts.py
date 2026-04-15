import pytest
from pydantic import ValidationError

from alphagraph.graph.state import RunStateModel


def test_run_state_model_rejects_invalid_supervisor_decision() -> None:
    with pytest.raises(ValidationError):
        RunStateModel.model_validate(
            {
                "run_id": "run-1",
                "brief": "demo",
                "dataset_path": "prices.csv",
                "attempt": 0,
                "max_attempts": 2,
                "status": "queued",
                "phase": "initial",
                "approval_status": "not_requested",
                "supervisor_decision": "do_anything",
                "attempts": [],
                "artifact_paths": {},
                "workflow_trace": [],
            }
        )


def test_run_state_model_rejects_invalid_approval_status() -> None:
    with pytest.raises(ValidationError):
        RunStateModel.model_validate(
            {
                "run_id": "run-1",
                "brief": "demo",
                "dataset_path": "prices.csv",
                "attempt": 0,
                "max_attempts": 2,
                "status": "queued",
                "phase": "initial",
                "approval_status": "maybe",
                "supervisor_decision": "run_hypothesis",
                "attempts": [],
                "artifact_paths": {},
                "workflow_trace": [],
            }
        )
