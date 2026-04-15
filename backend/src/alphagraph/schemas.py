from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunPhase(str, Enum):
    INITIAL = "initial"
    HYPOTHESIS_READY = "hypothesis_ready"
    CODE_READY = "code_ready"
    EXECUTION_COMPLETE = "execution_complete"
    CRITIC_COMPLETE = "critic_complete"
    AWAITING_APPROVAL = "awaiting_approval"
    FINALIZED = "finalized"


class SupervisorDecision(str, Enum):
    RUN_HYPOTHESIS = "run_hypothesis"
    RUN_HUMAN_REVIEW = "run_human_review"
    FINALIZE = "finalize"
    STOP = "stop"


class ApprovalState(str, Enum):
    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WorkflowNode(str, Enum):
    SUPERVISOR = "supervisor"
    HYPOTHESIS_AGENT = "hypothesis_agent"
    CODING_AGENT = "coding_agent"
    EXECUTION_TOOL = "execution_tool"
    FACTOR_CRITIC = "factor_critic"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"
    FINALIZE_RUN = "finalize_run"


class FactorSpec(BaseModel):
    name: str
    thesis: str
    expression: str
    universe: str = "demo-large-cap-8"
    rebalance: str = "daily"
    direction: str = "long_short"


class ParsedExpression(BaseModel):
    root: str
    metric: str
    field: str
    window: int | None = None
    negated: bool = False


class GeneratedCode(BaseModel):
    filename: str = "generated_strategy.py"
    commentary: str
    script: str


class HypothesisOutput(BaseModel):
    factor_spec: FactorSpec


class CodegenOutput(BaseModel):
    generated_code: GeneratedCode


class ExecutionResult(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    metrics: dict[str, float | int | str] = Field(default_factory=dict)
    artifact_path: str | None = None


class EvaluationResult(BaseModel):
    needs_revision: bool
    reasons: list[str] = Field(default_factory=list)
    scorecard: dict[str, Any] = Field(default_factory=dict)
    summary: str


class Critique(BaseModel):
    summary: str
    root_cause: str
    revision_instructions: str


class CriticOutput(BaseModel):
    evaluation: EvaluationResult
    critique: Critique
    needs_revision: bool


class AttemptRecord(BaseModel):
    attempt_number: int
    factor_spec: FactorSpec
    generated_code: GeneratedCode
    execution_result: ExecutionResult
    evaluation: EvaluationResult
    critique: Critique
    artifact_paths: dict[str, str] = Field(default_factory=dict)


class RunSnapshot(BaseModel):
    run_id: str
    brief: str
    status: str
    phase: RunPhase
    attempt: int
    max_attempts: int = 2
    approval_status: ApprovalState
    supervisor_decision: SupervisorDecision
    current_node: WorkflowNode | None = None
    workflow_trace: list[WorkflowNode] = Field(default_factory=list)
    attempts: list[AttemptRecord] = Field(default_factory=list)
    final_report_path: str | None = None
    artifact_paths: dict[str, str] = Field(default_factory=dict)


class CreateRunRequest(BaseModel):
    brief: str | None = None


class ApproveRunRequest(BaseModel):
    approved: bool
