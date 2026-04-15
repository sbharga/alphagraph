from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from alphagraph.graph.nodes import (
    human_in_the_loop,
    make_coding_node,
    make_execution_tool_node,
    make_factor_critic_node,
    make_finalize_node,
    make_hypothesis_node,
    route_after_supervisor,
    supervisor,
)
from alphagraph.graph.state import RunState
from alphagraph.llm.provider import AgentSuite, LLMProvider, build_agent_suite
from alphagraph.runtime.sandbox import SandboxRunner
from alphagraph.storage.artifacts import ArtifactStore


@dataclass
class WorkflowRuntime:
    graph: object
    checkpointer: SqliteSaver
    checkpoint_conn: sqlite3.Connection
    artifact_store: ArtifactStore


def create_workflow(provider: LLMProvider | AgentSuite, base_dir: Path) -> WorkflowRuntime:
    data_dir = base_dir / ".data"
    data_dir.mkdir(parents=True, exist_ok=True)
    artifact_store = ArtifactStore(base_dir / "artifacts")
    checkpoint_conn = sqlite3.connect(
        data_dir / "checkpoints.sqlite",
        check_same_thread=False,
    )
    checkpointer = SqliteSaver(checkpoint_conn)
    checkpointer.setup()
    runner = SandboxRunner(project_src=Path(__file__).resolve().parents[2], artifact_store=artifact_store)
    agent_suite = provider if isinstance(provider, AgentSuite) else build_agent_suite(provider)

    builder = StateGraph(RunState)
    builder.add_node("supervisor", supervisor)
    builder.add_node("hypothesis_agent", make_hypothesis_node(agent_suite))
    builder.add_node("coding_agent", make_coding_node(agent_suite))
    builder.add_node("execution_tool", make_execution_tool_node(runner))
    builder.add_node("factor_critic", make_factor_critic_node(agent_suite, artifact_store))
    builder.add_node("human_in_the_loop", human_in_the_loop)
    builder.add_node("finalize_run", make_finalize_node(artifact_store))

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "run_hypothesis": "hypothesis_agent",
            "run_human_review": "human_in_the_loop",
            "finalize": "finalize_run",
            "stop": END,
        },
    )
    builder.add_edge("hypothesis_agent", "coding_agent")
    builder.add_edge("coding_agent", "execution_tool")
    builder.add_edge("execution_tool", "factor_critic")
    builder.add_edge("factor_critic", "supervisor")
    builder.add_edge("human_in_the_loop", "supervisor")
    builder.add_edge("finalize_run", END)

    return WorkflowRuntime(
        graph=builder.compile(checkpointer=checkpointer),
        checkpointer=checkpointer,
        checkpoint_conn=checkpoint_conn,
        artifact_store=artifact_store,
    )
