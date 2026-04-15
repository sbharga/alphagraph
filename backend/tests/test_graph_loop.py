from pathlib import Path

from alphagraph.graph.workflow import create_workflow
from alphagraph.llm.provider import DemoLLMProvider
from alphagraph.schemas import ApprovalState, RunPhase, SupervisorDecision, WorkflowNode
from alphagraph.service import AlphaGraphService


def test_graph_performs_one_revision_then_waits_for_human_approval(tmp_path: Path) -> None:
    service = AlphaGraphService(
        base_dir=tmp_path,
        dataset_path=Path(__file__).resolve().parents[1] / "data" / "prices.csv",
        workflow=create_workflow(DemoLLMProvider(), tmp_path),
        run_mode="inline",
    )

    snapshot = service.create_run()

    assert snapshot.status == "awaiting_approval"
    assert snapshot.phase == RunPhase.AWAITING_APPROVAL
    assert snapshot.approval_status == ApprovalState.PENDING
    assert snapshot.supervisor_decision == SupervisorDecision.RUN_HUMAN_REVIEW
    assert snapshot.current_node == WorkflowNode.HUMAN_IN_THE_LOOP
    assert snapshot.attempt == 2
    assert len(snapshot.attempts) == 2
    assert snapshot.attempts[0].evaluation.needs_revision is True
    assert snapshot.attempts[1].evaluation.needs_revision is False
    assert snapshot.attempts[0].factor_spec.expression == "rank(close)"
    assert snapshot.attempts[1].factor_spec.expression == "rank(ts_return(close, 5))"


def test_graph_resume_with_approval_finalizes_artifacts(tmp_path: Path) -> None:
    service = AlphaGraphService(
        base_dir=tmp_path,
        dataset_path=Path(__file__).resolve().parents[1] / "data" / "prices.csv",
        workflow=create_workflow(DemoLLMProvider(), tmp_path),
        run_mode="inline",
    )

    initial = service.create_run()
    final = service.approve_run(initial.run_id, approved=True)

    assert final.status == "completed"
    assert final.phase == RunPhase.FINALIZED
    assert final.approval_status == ApprovalState.APPROVED
    assert final.supervisor_decision == SupervisorDecision.FINALIZE
    assert final.current_node == WorkflowNode.FINALIZE_RUN
    assert final.final_report_path is not None
    assert Path(final.final_report_path).exists()


def test_graph_rejection_stops_without_writing_final_report(tmp_path: Path) -> None:
    service = AlphaGraphService(
        base_dir=tmp_path,
        dataset_path=Path(__file__).resolve().parents[1] / "data" / "prices.csv",
        workflow=create_workflow(DemoLLMProvider(), tmp_path),
        run_mode="inline",
    )

    initial = service.create_run()
    final = service.approve_run(initial.run_id, approved=False)

    assert final.status == "rejected"
    assert final.phase == RunPhase.FINALIZED
    assert final.approval_status == ApprovalState.REJECTED
    assert final.supervisor_decision == SupervisorDecision.FINALIZE
    assert final.current_node == WorkflowNode.FINALIZE_RUN
    assert final.final_report_path is None
