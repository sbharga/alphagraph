export type RunPhase =
  | "initial"
  | "hypothesis_ready"
  | "code_ready"
  | "execution_complete"
  | "critic_complete"
  | "awaiting_approval"
  | "finalized";

export type SupervisorDecision =
  | "run_hypothesis"
  | "run_human_review"
  | "finalize"
  | "stop";

export type WorkflowNode =
  | "supervisor"
  | "hypothesis_agent"
  | "coding_agent"
  | "execution_tool"
  | "factor_critic"
  | "human_in_the_loop"
  | "finalize_run";

export type FactorSpec = {
  name: string;
  thesis: string;
  expression: string;
  universe: string;
  rebalance: string;
  direction: string;
};

export type GeneratedCode = {
  filename: string;
  commentary: string;
  script: string;
};

export type ExecutionResult = {
  success: boolean;
  stdout: string;
  stderr: string;
  metrics: Record<string, number | string>;
  artifact_path: string | null;
};

export type EvaluationResult = {
  needs_revision: boolean;
  reasons: string[];
  scorecard: Record<string, number | string>;
  summary: string;
};

export type Critique = {
  summary: string;
  root_cause: string;
  revision_instructions: string;
};

export type AttemptRecord = {
  attempt_number: number;
  factor_spec: FactorSpec;
  generated_code: GeneratedCode;
  execution_result: ExecutionResult;
  evaluation: EvaluationResult;
  critique: Critique;
  artifact_paths: Record<string, string>;
};

export type RunSnapshot = {
  run_id: string;
  brief: string;
  status: string;
  phase: RunPhase;
  attempt: number;
  max_attempts: number;
  approval_status: string;
  supervisor_decision: SupervisorDecision;
  current_node: WorkflowNode | null;
  workflow_trace: WorkflowNode[];
  attempts: AttemptRecord[];
  final_report_path: string | null;
  artifact_paths: Record<string, string>;
};

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function createRun(): Promise<RunSnapshot> {
  const response = await fetch("/runs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });
  return parseJson<RunSnapshot>(response);
}

export async function approveRun(runId: string, approved: boolean): Promise<RunSnapshot> {
  const response = await fetch(`/runs/${runId}/approve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ approved }),
  });
  return parseJson<RunSnapshot>(response);
}
