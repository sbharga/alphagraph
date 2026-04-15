from __future__ import annotations

from pathlib import Path

from langgraph.types import interrupt

from alphagraph.graph.state import RunState, validate_run_state
from alphagraph.llm.provider import AgentSuite
from alphagraph.runtime.sandbox import SandboxRunner
from alphagraph.schemas import (
    ApprovalState,
    AttemptRecord,
    RunPhase,
    RunSnapshot,
    SupervisorDecision,
    WorkflowNode,
)
from alphagraph.storage.artifacts import ArtifactStore


def supervisor(state: RunState) -> RunState:
    snapshot = validate_run_state(state)
    trace = _append_trace(snapshot.workflow_trace, WorkflowNode.SUPERVISOR)

    if snapshot.approval_status in {ApprovalState.APPROVED, ApprovalState.REJECTED}:
        return {
            "status": "finalizing" if snapshot.approval_status == ApprovalState.APPROVED else "rejected",
            "supervisor_decision": SupervisorDecision.FINALIZE,
            "current_node": WorkflowNode.FINALIZE_RUN,
            "workflow_trace": trace,
        }

    if snapshot.phase == RunPhase.INITIAL:
        return {
            "status": "running",
            "supervisor_decision": SupervisorDecision.RUN_HYPOTHESIS,
            "current_node": WorkflowNode.HYPOTHESIS_AGENT,
            "workflow_trace": trace,
        }

    if snapshot.phase == RunPhase.CRITIC_COMPLETE and snapshot.critic_output is not None:
        if snapshot.critic_output.needs_revision and snapshot.attempt < snapshot.max_attempts:
            return {
                "status": "revising",
                "approval_status": ApprovalState.NOT_REQUESTED,
                "supervisor_decision": SupervisorDecision.RUN_HYPOTHESIS,
                "current_node": WorkflowNode.HYPOTHESIS_AGENT,
                "workflow_trace": trace,
            }
        return {
            "status": "awaiting_approval",
            "phase": RunPhase.AWAITING_APPROVAL,
            "approval_status": ApprovalState.PENDING,
            "supervisor_decision": SupervisorDecision.RUN_HUMAN_REVIEW,
            "current_node": WorkflowNode.HUMAN_IN_THE_LOOP,
            "workflow_trace": trace,
        }

    if snapshot.phase == RunPhase.FINALIZED:
        return {
            "supervisor_decision": SupervisorDecision.STOP,
            "current_node": WorkflowNode.FINALIZE_RUN,
            "workflow_trace": trace,
        }

    return {
        "supervisor_decision": SupervisorDecision.STOP,
        "current_node": WorkflowNode.SUPERVISOR,
        "workflow_trace": trace,
    }


def make_hypothesis_node(agent_suite: AgentSuite):
    def hypothesis_agent(state: RunState) -> RunState:
        snapshot = validate_run_state(state)
        attempt_number = snapshot.attempt + 1
        prior_critique = snapshot.critic_output.critique if snapshot.critic_output else None
        hypothesis = agent_suite.hypothesis_agent.propose(
            brief=snapshot.brief,
            attempt_number=attempt_number,
            prior_critique=prior_critique,
        )
        return {
            "hypothesis_output": hypothesis.model_dump(),
            "phase": RunPhase.HYPOTHESIS_READY,
            "status": "running",
            "current_node": WorkflowNode.HYPOTHESIS_AGENT,
            "workflow_trace": _append_trace(snapshot.workflow_trace, WorkflowNode.HYPOTHESIS_AGENT),
        }

    return hypothesis_agent


def make_coding_node(agent_suite: AgentSuite):
    def coding_agent(state: RunState) -> RunState:
        snapshot = validate_run_state(state)
        attempt_number = snapshot.attempt + 1
        if snapshot.hypothesis_output is None:
            raise ValueError("Hypothesis output is required before coding.")
        codegen_output = agent_suite.coding_agent.translate(
            hypothesis=snapshot.hypothesis_output,
            attempt_number=attempt_number,
        )
        return {
            "codegen_output": codegen_output.model_dump(),
            "phase": RunPhase.CODE_READY,
            "status": "running",
            "current_node": WorkflowNode.CODING_AGENT,
            "workflow_trace": _append_trace(snapshot.workflow_trace, WorkflowNode.CODING_AGENT),
        }

    return coding_agent


def make_execution_tool_node(runner: SandboxRunner):
    def execution_tool(state: RunState) -> RunState:
        snapshot = validate_run_state(state)
        attempt_number = snapshot.attempt + 1
        if snapshot.codegen_output is None:
            raise ValueError("Code output is required before execution.")
        execution_result, artifact_paths = runner.execute(
            run_id=snapshot.run_id,
            attempt_number=attempt_number,
            generated_code=snapshot.codegen_output.generated_code,
            dataset_path=Path(snapshot.dataset_path),
        )
        return {
            "execution_result": execution_result.model_dump(),
            "artifact_paths": artifact_paths,
            "phase": RunPhase.EXECUTION_COMPLETE,
            "status": "running",
            "current_node": WorkflowNode.EXECUTION_TOOL,
            "workflow_trace": _append_trace(snapshot.workflow_trace, WorkflowNode.EXECUTION_TOOL),
        }

    return execution_tool


def make_factor_critic_node(agent_suite: AgentSuite, artifact_store: ArtifactStore):
    def factor_critic(state: RunState) -> RunState:
        snapshot = validate_run_state(state)
        attempt_number = snapshot.attempt + 1
        if snapshot.hypothesis_output is None or snapshot.codegen_output is None or snapshot.execution_result is None:
            raise ValueError("Critic requires hypothesis, code, and execution results.")

        critic_output = agent_suite.factor_critic.review(
            hypothesis=snapshot.hypothesis_output,
            execution_result=snapshot.execution_result,
            attempt_number=attempt_number,
        )

        attempt_record = AttemptRecord(
            attempt_number=attempt_number,
            factor_spec=snapshot.hypothesis_output.factor_spec,
            generated_code=snapshot.codegen_output.generated_code,
            execution_result=snapshot.execution_result,
            evaluation=critic_output.evaluation,
            critique=critic_output.critique,
            artifact_paths=snapshot.artifact_paths,
        )
        attempt_snapshot_path = artifact_store.write_attempt_snapshot(
            snapshot.run_id,
            attempt_number,
            attempt_record,
        )
        merged_artifacts = dict(snapshot.artifact_paths)
        merged_artifacts["attempt_snapshot"] = str(attempt_snapshot_path)
        attempts = [attempt.model_dump() for attempt in snapshot.attempts]
        attempts.append(attempt_record.model_dump())
        return {
            "attempt": attempt_number,
            "attempts": attempts,
            "critic_output": critic_output.model_dump(),
            "artifact_paths": merged_artifacts,
            "phase": RunPhase.CRITIC_COMPLETE,
            "status": "critic_complete",
            "current_node": WorkflowNode.FACTOR_CRITIC,
            "workflow_trace": _append_trace(snapshot.workflow_trace, WorkflowNode.FACTOR_CRITIC),
        }

    return factor_critic


def human_in_the_loop(state: RunState) -> RunState:
    snapshot = validate_run_state(state)
    approved = interrupt(
        {
            "run_id": snapshot.run_id,
            "attempt": snapshot.attempt,
            "summary": snapshot.critic_output.critique.summary if snapshot.critic_output else "",
        }
    )
    return {
        "approval_status": ApprovalState.APPROVED if approved else ApprovalState.REJECTED,
        "status": "finalizing" if approved else "rejected",
        "current_node": WorkflowNode.SUPERVISOR,
    }


def make_finalize_node(artifact_store: ArtifactStore):
    def finalize_run(state: RunState) -> RunState:
        snapshot = validate_run_state(state)
        merged_trace = _append_trace(snapshot.workflow_trace, WorkflowNode.FINALIZE_RUN)
        materialized = RunSnapshot.model_validate(
            {
                **snapshot.model_dump(),
                "phase": RunPhase.FINALIZED,
                "current_node": WorkflowNode.FINALIZE_RUN,
                "workflow_trace": merged_trace,
            }
        )
        if materialized.approval_status == ApprovalState.APPROVED:
            report_path = artifact_store.write_final_report(materialized)
            merged_artifacts = dict(materialized.artifact_paths)
            merged_artifacts["final_report"] = str(report_path)
            return {
                "status": "completed",
                "phase": RunPhase.FINALIZED,
                "supervisor_decision": SupervisorDecision.FINALIZE,
                "current_node": WorkflowNode.FINALIZE_RUN,
                "workflow_trace": merged_trace,
                "final_report_path": str(report_path),
                "artifact_paths": merged_artifacts,
            }
        return {
            "status": "rejected",
            "phase": RunPhase.FINALIZED,
            "supervisor_decision": SupervisorDecision.FINALIZE,
            "current_node": WorkflowNode.FINALIZE_RUN,
            "workflow_trace": merged_trace,
            "final_report_path": None,
        }

    return finalize_run


def route_after_supervisor(state: RunState) -> str:
    snapshot = validate_run_state(state)
    return snapshot.supervisor_decision.value


def _append_trace(trace: list[WorkflowNode], node: WorkflowNode) -> list[WorkflowNode]:
    if trace and trace[-1] == node:
        return trace
    return [*trace, node]
