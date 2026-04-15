from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from langgraph.types import Command

from alphagraph.graph.workflow import WorkflowRuntime, create_workflow
from alphagraph.llm.provider import DemoLLMProvider, build_agent_suite
from alphagraph.schemas import (
    ApprovalState,
    RunPhase,
    RunSnapshot,
    SupervisorDecision,
    WorkflowNode,
)
from alphagraph.storage.db import RunRepository


DEFAULT_BRIEF = (
    "Propose a simple cross-sectional equity factor, generate backtest code, "
    "execute it on the local dataset, critique the result, revise once if "
    "needed, and wait for human approval before finalizing."
)


class AlphaGraphService:
    def __init__(
        self,
        *,
        base_dir: Path,
        dataset_path: Path,
        workflow: WorkflowRuntime | None = None,
        run_mode: str = "inline",
    ) -> None:
        self.base_dir = base_dir
        self.dataset_path = dataset_path
        self.workflow = workflow or create_workflow(build_agent_suite(DemoLLMProvider()), base_dir)
        self.run_mode = run_mode
        self.repository = RunRepository(base_dir / ".data" / "runs.sqlite")

    def create_run(self, brief: str | None = None) -> RunSnapshot:
        run_id = str(uuid4())
        initial_state = {
            "run_id": run_id,
            "brief": brief or DEFAULT_BRIEF,
            "dataset_path": str(self.dataset_path),
            "attempt": 0,
            "max_attempts": 2,
            "approval_status": ApprovalState.NOT_REQUESTED,
            "phase": RunPhase.INITIAL,
            "supervisor_decision": SupervisorDecision.RUN_HYPOTHESIS,
            "current_node": WorkflowNode.SUPERVISOR,
            "workflow_trace": [],
            "status": "queued",
            "attempts": [],
            "artifact_paths": {},
        }
        snapshot = self._invoke(run_id, initial_state)
        self.repository.save_snapshot(snapshot)
        return snapshot

    def approve_run(self, run_id: str, *, approved: bool) -> RunSnapshot:
        snapshot = self._invoke(run_id, Command(resume=approved))
        self.repository.save_snapshot(snapshot)
        return snapshot

    def get_run(self, run_id: str) -> RunSnapshot:
        snapshot = self.repository.get_snapshot(run_id)
        if snapshot is None:
            raise KeyError(run_id)
        return snapshot

    def _invoke(self, run_id: str, payload) -> RunSnapshot:
        config = {"configurable": {"thread_id": run_id}}
        self.workflow.graph.invoke(payload, config)
        state_snapshot = self.workflow.graph.get_state(config)
        return RunSnapshot.model_validate(state_snapshot.values)
