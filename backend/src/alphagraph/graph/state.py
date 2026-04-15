from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field

from alphagraph.schemas import (
    ApprovalState,
    AttemptRecord,
    CodegenOutput,
    CriticOutput,
    ExecutionResult,
    HypothesisOutput,
    RunPhase,
    SupervisorDecision,
    WorkflowNode,
)


class RunState(TypedDict, total=False):
    run_id: str
    brief: str
    dataset_path: str
    status: str
    phase: RunPhase
    attempt: int
    max_attempts: int
    approval_status: ApprovalState
    supervisor_decision: SupervisorDecision
    current_node: WorkflowNode
    workflow_trace: list[WorkflowNode]
    hypothesis_output: dict[str, Any]
    codegen_output: dict[str, Any]
    execution_result: dict[str, Any]
    attempts: list[dict[str, Any]]
    critic_output: dict[str, Any]
    artifact_paths: dict[str, str]
    final_report_path: str | None


class RunStateModel(BaseModel):
    run_id: str
    brief: str
    dataset_path: str
    status: str
    phase: RunPhase
    attempt: int = 0
    max_attempts: int = 2
    approval_status: ApprovalState = ApprovalState.NOT_REQUESTED
    supervisor_decision: SupervisorDecision = SupervisorDecision.RUN_HYPOTHESIS
    current_node: WorkflowNode = WorkflowNode.SUPERVISOR
    workflow_trace: list[WorkflowNode] = Field(default_factory=list)
    hypothesis_output: HypothesisOutput | None = None
    codegen_output: CodegenOutput | None = None
    execution_result: ExecutionResult | None = None
    critic_output: CriticOutput | None = None
    attempts: list[AttemptRecord] = Field(default_factory=list)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    final_report_path: str | None = None


def validate_run_state(state: RunState) -> RunStateModel:
    return RunStateModel.model_validate(state)
