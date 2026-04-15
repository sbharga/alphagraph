import { useEffect, useState } from "react";
import type { AttemptRecord, RunSnapshot, WorkflowNode } from "./api";

// ─── Types ────────────────────────────────────────────────────────────────────

type MainTab = "run" | "graph";
type ArtifactTab = "factor" | "code" | "metrics" | "critique" | "final";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatMetric(value: number | string): string {
  if (typeof value === "string") return value;
  if (Math.abs(value) >= 1_000) return value.toFixed(0);
  if (Math.abs(value) >= 1) return value.toFixed(2);
  return value.toFixed(3);
}

function defaultArtifactTab(snapshot: RunSnapshot | null): ArtifactTab {
  if (!snapshot) return "factor";
  const p = snapshot.phase;
  if (p === "finalized") return "final";
  if (p === "awaiting_approval" || p === "critic_complete") return "critique";
  if (p === "execution_complete") return "metrics";
  if (p === "code_ready") return "code";
  return "factor";
}

function getKeyMetrics(attempt: AttemptRecord): Array<{ label: string; value: string }> {
  const m = attempt.execution_result.metrics;
  const result: Array<{ label: string; value: string }> = [];
  const tryAdd = (keys: string[], label: string) => {
    for (const k of keys) {
      if (k in m) { result.push({ label, value: formatMetric(m[k]) }); return; }
    }
  };
  tryAdd(["sharpe_ratio", "sharpe", "Sharpe Ratio"], "Sharpe");
  tryAdd(["annual_return", "annual_ret", "Annual Return"], "Annual Ret");
  tryAdd(["ic_mean", "ic", "IC Mean"], "IC Mean");
  tryAdd(["max_drawdown", "Max Drawdown"], "Max DD");
  if (result.length === 0) {
    Object.entries(m).slice(0, 3).forEach(([k, v]) => {
      result.push({ label: k.replace(/_/g, " "), value: formatMetric(v) });
    });
  }
  return result.slice(0, 4);
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function CheckIcon({ size = 11 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 12 12" fill="none">
      <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DotIcon() {
  return <div style={{ width: 6, height: 6, borderRadius: "50%", background: "currentColor" }} />;
}

// ─── StatusHeader ─────────────────────────────────────────────────────────────

export function StatusHeader({
  snapshot,
  busy,
  activeTab,
  onTabChange,
}: {
  snapshot: RunSnapshot | null;
  busy: boolean;
  activeTab: MainTab;
  onTabChange: (tab: MainTab) => void;
}) {
  const status = snapshot?.status ?? (busy ? "running" : "idle");
  const pillClass =
    busy || status === "running"
      ? "status-pill status-running"
      : status === "completed"
        ? "status-pill status-completed"
        : snapshot?.approval_status === "pending"
          ? "status-pill status-approval"
          : "status-pill";

  return (
    <header
      className="sticky top-0 z-50"
      style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)" }}
    >
      <div
        className="max-w-[1400px] mx-auto px-5"
        style={{ height: 52, display: "flex", alignItems: "center", gap: 20 }}
      >
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginRight: 4 }}>
          <div
            style={{
              width: 26,
              height: 26,
              borderRadius: 7,
              background: "var(--accent)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "0.8rem",
              fontWeight: 700,
              color: "#0d1117",
              flexShrink: 0,
            }}
          >
            αG
          </div>
          <span style={{ fontWeight: 600, fontSize: "0.88rem", letterSpacing: "-0.01em" }}>
            AlphaGraph
          </span>
        </div>

        {/* Main tabs */}
        <div className="tab-bar">
          <button
            className={`tab-item${activeTab === "run" ? " active" : ""}`}
            onClick={() => onTabChange("run")}
          >
            Research Run
          </button>
          <button
            className={`tab-item${activeTab === "graph" ? " active" : ""}`}
            onClick={() => onTabChange("graph")}
          >
            Workflow Graph
          </button>
        </div>

        <div style={{ flex: 1 }} />

        {/* Run metadata */}
        {snapshot && (
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <span style={{ fontSize: "0.72rem", color: "var(--muted)", fontFamily: "monospace" }}>
              {snapshot.run_id.slice(0, 8)}
            </span>
            {snapshot.attempt > 0 && (
              <span style={{ fontSize: "0.72rem", color: "var(--muted)" }}>
                attempt {snapshot.attempt} / {snapshot.max_attempts}
              </span>
            )}
          </div>
        )}

        {/* Status pill */}
        <div className={pillClass}>
          <div className="dot" />
          <span style={{ textTransform: "capitalize" }}>
            {snapshot?.approval_status === "pending" ? "awaiting approval" : status}
          </span>
        </div>
      </div>
    </header>
  );
}

// ─── WorkflowRail ─────────────────────────────────────────────────────────────

const RAIL_STEPS: Array<{ node: WorkflowNode; label: string; desc: string }> = [
  { node: "supervisor", label: "Supervisor", desc: "Orchestrates the research pipeline" },
  { node: "hypothesis_agent", label: "Hypothesis", desc: "Generates factor specification" },
  { node: "coding_agent", label: "Coding", desc: "Writes backtest script" },
  { node: "execution_tool", label: "Execution", desc: "Runs backtest on equities data" },
  { node: "factor_critic", label: "Critic", desc: "Evaluates and critiques results" },
  { node: "human_in_the_loop", label: "Approval", desc: "Human review checkpoint" },
  { node: "finalize_run", label: "Finalize", desc: "Saves artifact bundle to disk" },
];

export function WorkflowRail({ snapshot }: { snapshot: RunSnapshot | null }) {
  const visited = new Set(snapshot?.workflow_trace ?? []);
  const active = snapshot?.current_node;
  if (snapshot?.approval_status !== "not_requested") visited.add("human_in_the_loop");

  return (
    <div className="panel" style={{ padding: "16px 14px" }}>
      <p className="eyebrow">Workflow</p>
      <p style={{ fontSize: "0.72rem", color: "var(--muted)", marginBottom: 14 }}>
        Sequential · {RAIL_STEPS.length} nodes
      </p>

      <div style={{ display: "flex", flexDirection: "column" }}>
        {RAIL_STEPS.map((step, i) => {
          const isActive = active === step.node;
          const isComplete = visited.has(step.node) && !isActive;
          const isLast = i === RAIL_STEPS.length - 1;

          return (
            <div key={step.node}>
              <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                {/* Dot */}
                <div
                  className={`rail-dot${isActive ? " active" : isComplete ? " complete" : ""}`}
                  style={{ marginTop: 1 }}
                >
                  {isComplete && <CheckIcon />}
                  {isActive && <DotIcon />}
                </div>

                {/* Content */}
                <div style={{ flex: 1, paddingBottom: isLast ? 0 : 4 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 6 }}>
                    <span
                      style={{
                        fontSize: "0.82rem",
                        fontWeight: 600,
                        color: isActive
                          ? "var(--accent)"
                          : isComplete
                            ? "var(--text)"
                            : "var(--subtle)",
                        lineHeight: 1.3,
                      }}
                    >
                      {step.label}
                    </span>
                    {isActive && <span className="badge-accent">Active</span>}
                    {isComplete && <span className="badge-success">Done</span>}
                  </div>
                  <p
                    style={{
                      fontSize: "0.72rem",
                      color: "var(--subtle)",
                      margin: "2px 0 0",
                      lineHeight: 1.4,
                    }}
                  >
                    {step.desc}
                  </p>
                </div>
              </div>

              {/* Connector line */}
              {!isLast && (
                <div style={{ display: "flex", gap: 10 }}>
                  <div style={{ width: 22, display: "flex", justifyContent: "center" }}>
                    <div
                      style={{
                        width: 1.5,
                        height: 20,
                        background: isComplete ? "var(--success)" : "var(--border)",
                        opacity: isComplete ? 0.4 : 1,
                        margin: "2px 0",
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── AttemptComparisonCard ────────────────────────────────────────────────────

export function AttemptComparisonCard({ snapshot }: { snapshot: RunSnapshot }) {
  if (snapshot.attempts.length < 2) return null;
  const attempts = snapshot.attempts.slice(0, 2);

  return (
    <div className="panel" style={{ padding: 16 }}>
      <p className="eyebrow">Revision Comparison</p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 4 }}>
        {attempts.map((attempt) => {
          const metrics = getKeyMetrics(attempt);
          return (
            <div key={attempt.attempt_number} className="panel-raised" style={{ padding: 12 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <span className="section-label">Attempt {attempt.attempt_number}</span>
                <span className={attempt.evaluation.needs_revision ? "badge-warning" : "badge-success"}>
                  {attempt.evaluation.needs_revision ? "Revised" : "Pass"}
                </span>
              </div>
              <p
                style={{
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  color: "var(--text)",
                  marginBottom: 8,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {attempt.factor_spec.name}
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {metrics.map(({ label, value }) => (
                  <div key={label} style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ fontSize: "0.72rem", color: "var(--muted)" }}>{label}</span>
                    <span
                      style={{
                        fontSize: "0.72rem",
                        fontFamily: "monospace",
                        fontWeight: 500,
                        color: "var(--text)",
                      }}
                    >
                      {value}
                    </span>
                  </div>
                ))}
              </div>
              {attempt.critique.summary && (
                <p
                  style={{
                    fontSize: "0.7rem",
                    color: "var(--muted)",
                    marginTop: 8,
                    lineHeight: 1.4,
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                  }}
                >
                  {attempt.critique.summary}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── ArtifactPane ─────────────────────────────────────────────────────────────

export function ArtifactPane({ snapshot }: { snapshot: RunSnapshot | null }) {
  const [activeTab, setActiveTab] = useState<ArtifactTab>("factor");
  const latest = snapshot?.attempts[snapshot.attempts.length - 1] ?? null;

  useEffect(() => {
    setActiveTab(defaultArtifactTab(snapshot));
  }, [snapshot?.phase]);

  const hasAttempt = !!latest;
  const isFinalized = snapshot?.phase === "finalized";

  const tabs: Array<{ id: ArtifactTab; label: string; available: boolean }> = [
    { id: "factor", label: "Factor", available: hasAttempt },
    { id: "code", label: "Code", available: hasAttempt },
    { id: "metrics", label: "Metrics", available: hasAttempt },
    { id: "critique", label: "Critique", available: hasAttempt },
    { id: "final", label: "Final", available: isFinalized },
  ];

  return (
    <div className="panel animate-fade-up" style={{ display: "flex", flexDirection: "column", minHeight: 520 }}>
      {/* Tab bar header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 16px 0",
          borderBottom: "1px solid var(--border)",
          gap: 8,
        }}
      >
        <p className="eyebrow" style={{ margin: 0 }}>
          Artifact
        </p>
        <div className="tab-bar" style={{ marginBottom: -1 }}>
          {tabs.map((t) => (
            <button
              key={t.id}
              className={`tab-item${activeTab === t.id ? " active" : ""}`}
              onClick={() => t.available && setActiveTab(t.id)}
              disabled={!t.available}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content area */}
      <div style={{ flex: 1, padding: 16, overflow: "auto" }}>
        {!snapshot ? (
          <EmptyArtifactState />
        ) : !latest && activeTab !== "final" ? (
          <EmptyArtifactState />
        ) : activeTab === "factor" && latest ? (
          <FactorTab attempt={latest} />
        ) : activeTab === "code" && latest ? (
          <CodeTab attempt={latest} />
        ) : activeTab === "metrics" && latest ? (
          <MetricsTab attempt={latest} />
        ) : activeTab === "critique" && latest ? (
          <CritiqueTab attempt={latest} />
        ) : activeTab === "final" && isFinalized ? (
          <FinalTab snapshot={snapshot} />
        ) : (
          <EmptyArtifactState />
        )}
      </div>
    </div>
  );
}

function EmptyArtifactState() {
  return (
    <div
      style={{
        height: "100%",
        minHeight: 400,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 12,
        color: "var(--subtle)",
      }}
    >
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: 12,
          background: "var(--raised)",
          border: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "1.5rem",
        }}
      >
        αG
      </div>
      <p style={{ fontSize: "0.82rem", color: "var(--subtle)", margin: 0 }}>
        Start a run to see artifacts
      </p>
    </div>
  );
}

function FactorTab({ attempt }: { attempt: AttemptRecord }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }} className="animate-fade-up">
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <h2
            style={{
              margin: 0,
              fontSize: "1.15rem",
              fontWeight: 700,
              letterSpacing: "-0.02em",
              color: "var(--text)",
            }}
          >
            {attempt.factor_spec.name}
          </h2>
          <span className={attempt.evaluation.needs_revision ? "badge-warning" : "badge-success"}>
            {attempt.evaluation.needs_revision ? "Needs Revision" : "Pass"}
          </span>
        </div>
        <p style={{ fontSize: "0.85rem", color: "var(--muted)", lineHeight: 1.55, margin: 0 }}>
          {attempt.factor_spec.thesis}
        </p>
      </div>

      <div>
        <p className="section-label" style={{ marginBottom: 6 }}>
          Expression
        </p>
        <div className="expr-block">{attempt.factor_spec.expression}</div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
        {[
          { label: "Universe", value: attempt.factor_spec.universe },
          { label: "Rebalance", value: attempt.factor_spec.rebalance },
          { label: "Direction", value: attempt.factor_spec.direction },
        ].map(({ label, value }) => (
          <div key={label} className="panel-elevated" style={{ padding: "10px 12px" }}>
            <p className="section-label" style={{ marginBottom: 4 }}>
              {label}
            </p>
            <p style={{ fontSize: "0.82rem", color: "var(--text)", margin: 0, fontWeight: 500 }}>{value}</p>
          </div>
        ))}
      </div>

      {attempt.evaluation.reasons.length > 0 && (
        <div>
          <p className="section-label" style={{ marginBottom: 8 }}>
            Evaluation Notes
          </p>
          <ul style={{ margin: 0, padding: "0 0 0 16px", display: "flex", flexDirection: "column", gap: 4 }}>
            {attempt.evaluation.reasons.map((r, i) => (
              <li key={i} style={{ fontSize: "0.8rem", color: "var(--muted)", lineHeight: 1.45 }}>
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function CodeTab({ attempt }: { attempt: AttemptRecord }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }} className="animate-fade-up">
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span
          style={{
            fontFamily: "monospace",
            fontSize: "0.78rem",
            background: "var(--elevated)",
            border: "1px solid var(--border)",
            borderRadius: 4,
            padding: "3px 8px",
            color: "var(--muted)",
          }}
        >
          {attempt.generated_code.filename}
        </span>
      </div>
      {attempt.generated_code.commentary && (
        <p style={{ fontSize: "0.85rem", color: "var(--muted)", lineHeight: 1.55, margin: 0 }}>
          {attempt.generated_code.commentary}
        </p>
      )}
      <div className="code-block" style={{ maxHeight: 480 }}>
        {attempt.generated_code.script}
      </div>
    </div>
  );
}

function MetricsTab({ attempt }: { attempt: AttemptRecord }) {
  const metrics = Object.entries(attempt.execution_result.metrics);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }} className="animate-fade-up">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
        {metrics.map(([key, value]) => (
          <div key={key} className="metric-chip">
            <p className="section-label" style={{ marginBottom: 4 }}>
              {key.replaceAll("_", " ")}
            </p>
            <p
              style={{
                margin: 0,
                fontSize: "1.05rem",
                fontWeight: 600,
                fontFamily: "monospace",
                color: "var(--text)",
              }}
            >
              {formatMetric(value)}
            </p>
          </div>
        ))}
      </div>

      <div
        className="panel-raised"
        style={{ padding: "12px 14px", borderLeft: "3px solid var(--accent)" }}
      >
        <p className="section-label" style={{ marginBottom: 4 }}>
          Evaluation Summary
        </p>
        <p style={{ fontSize: "0.85rem", color: "var(--muted)", lineHeight: 1.55, margin: 0 }}>
          {attempt.evaluation.summary}
        </p>
      </div>

      {Object.keys(attempt.evaluation.scorecard).length > 0 && (
        <div>
          <p className="section-label" style={{ marginBottom: 8 }}>
            Scorecard
          </p>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {Object.entries(attempt.evaluation.scorecard).map(([k, v]) => (
              <div key={k} className="kv-row">
                <span className="kv-label">{k.replaceAll("_", " ")}</span>
                <span className="kv-value" style={{ fontFamily: "monospace" }}>
                  {formatMetric(v)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CritiqueTab({ attempt }: { attempt: AttemptRecord }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }} className="animate-fade-up">
      {/* Summary — prominent */}
      <div
        style={{
          background: attempt.evaluation.needs_revision ? "var(--warning-dim)" : "var(--success-dim)",
          border: `1px solid ${attempt.evaluation.needs_revision ? "rgba(210,153,34,0.2)" : "rgba(63,185,80,0.2)"}`,
          borderRadius: 10,
          padding: "14px 16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
          <span className={attempt.evaluation.needs_revision ? "badge-warning" : "badge-success"}>
            {attempt.evaluation.needs_revision ? "Revision Required" : "Approved"}
          </span>
        </div>
        <p
          style={{
            fontSize: "0.9rem",
            color: "var(--text)",
            lineHeight: 1.55,
            margin: 0,
            fontWeight: 500,
          }}
        >
          {attempt.critique.summary}
        </p>
      </div>

      {/* Root cause */}
      <div className="panel-raised" style={{ padding: "12px 14px" }}>
        <p className="section-label" style={{ marginBottom: 6 }}>
          Issue Detected
        </p>
        <p style={{ fontSize: "0.85rem", color: "var(--muted)", lineHeight: 1.55, margin: 0 }}>
          {attempt.critique.root_cause}
        </p>
      </div>

      {/* Revision instructions */}
      {attempt.critique.revision_instructions && (
        <div
          className="panel-raised"
          style={{ padding: "12px 14px", borderLeft: "3px solid var(--accent)" }}
        >
          <p className="section-label" style={{ marginBottom: 6 }}>
            Revision Guidance
          </p>
          <p style={{ fontSize: "0.85rem", color: "var(--muted)", lineHeight: 1.55, margin: 0 }}>
            {attempt.critique.revision_instructions}
          </p>
        </div>
      )}
    </div>
  );
}

function FinalTab({ snapshot }: { snapshot: RunSnapshot }) {
  const lastAttempt = snapshot.attempts[snapshot.attempts.length - 1];
  const metrics = lastAttempt ? Object.entries(lastAttempt.execution_result.metrics).slice(0, 6) : [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }} className="animate-fade-up">
      {/* Approval banner */}
      <div
        style={{
          background: "var(--success-dim)",
          border: "1px solid rgba(63,185,80,0.2)",
          borderRadius: 10,
          padding: "16px",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: "50%",
            background: "rgba(63,185,80,0.15)",
            border: "1.5px solid var(--success)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--success)",
            flexShrink: 0,
          }}
        >
          <CheckIcon size={16} />
        </div>
        <div>
          <p style={{ margin: "0 0 2px", fontSize: "0.9rem", fontWeight: 600, color: "var(--success)" }}>
            Run Finalized
          </p>
          <p style={{ margin: 0, fontSize: "0.78rem", color: "var(--muted)" }}>
            Factor approved and artifact bundle saved
          </p>
        </div>
      </div>

      {lastAttempt && (
        <>
          <div>
            <p className="section-label" style={{ marginBottom: 6 }}>
              Approved Factor
            </p>
            <p style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text)", margin: "0 0 4px" }}>
              {lastAttempt.factor_spec.name}
            </p>
            <div className="expr-block">{lastAttempt.factor_spec.expression}</div>
          </div>

          {metrics.length > 0 && (
            <div>
              <p className="section-label" style={{ marginBottom: 8 }}>
                Final Metrics
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
                {metrics.map(([key, value]) => (
                  <div key={key} className="metric-chip">
                    <p className="section-label" style={{ marginBottom: 3 }}>
                      {key.replaceAll("_", " ")}
                    </p>
                    <p style={{ margin: 0, fontSize: "1rem", fontWeight: 600, fontFamily: "monospace", color: "var(--text)" }}>
                      {formatMetric(value)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {snapshot.final_report_path && (
        <div className="panel-raised" style={{ padding: "12px 14px" }}>
          <p className="section-label" style={{ marginBottom: 6 }}>
            Artifact Path
          </p>
          <code
            style={{
              fontSize: "0.78rem",
              fontFamily: "monospace",
              color: "var(--accent)",
              wordBreak: "break-all",
            }}
          >
            {snapshot.final_report_path}
          </code>
        </div>
      )}
    </div>
  );
}

// ─── WorkflowGraphView ────────────────────────────────────────────────────────

const GRAPH_NODES: Array<{ id: WorkflowNode; label: string; desc: string; cx: number; cy: number }> = [
  { id: "supervisor",       label: "Supervisor",  desc: "Orchestrates pipeline",     cx: 90,  cy: 90 },
  { id: "hypothesis_agent", label: "Hypothesis",  desc: "Generates factor spec",     cx: 230, cy: 90 },
  { id: "coding_agent",     label: "Coding",      desc: "Writes backtest script",    cx: 370, cy: 90 },
  { id: "execution_tool",   label: "Execution",   desc: "Runs backtest",             cx: 510, cy: 90 },
  { id: "factor_critic",    label: "Critic",      desc: "Evaluates results",         cx: 510, cy: 185 },
  { id: "human_in_the_loop",label: "Approval",    desc: "Human review",              cx: 370, cy: 185 },
  { id: "finalize_run",     label: "Finalize",    desc: "Saves artifacts",           cx: 230, cy: 185 },
];

const NW = 110; // node width
const NH = 44;  // node height

function nodeState(
  id: WorkflowNode,
  activeNode: WorkflowNode | null,
  visited: Set<string>,
): "pending" | "active" | "complete" {
  if (activeNode === id) return "active";
  if (visited.has(id)) return "complete";
  return "pending";
}

export function WorkflowGraphView({ snapshot }: { snapshot: RunSnapshot | null }) {
  const [selectedId, setSelectedId] = useState<WorkflowNode | null>(null);

  const visited = new Set(snapshot?.workflow_trace ?? []);
  const active = snapshot?.current_node ?? null;
  if (snapshot?.approval_status !== "not_requested") visited.add("human_in_the_loop");

  const showLoop = (snapshot?.attempt ?? 1) > 1;

  const selectedNode = GRAPH_NODES.find((n) => n.id === selectedId);
  const selectedState = selectedId ? nodeState(selectedId, active, visited) : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="panel" style={{ padding: 24 }}>
        <div
          style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20 }}
        >
          <div>
            <p className="eyebrow">Architecture</p>
            <h2 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
              Agentic Research Pipeline
            </h2>
            <p style={{ margin: "4px 0 0", fontSize: "0.78rem", color: "var(--muted)" }}>
              Click a node to inspect its output
            </p>
          </div>
          {showLoop && <span className="badge-warning">Revision Loop Active</span>}
        </div>

        <div style={{ overflowX: "auto" }}>
          <svg
            viewBox="0 0 640 240"
            style={{ width: "100%", maxWidth: 640, height: "auto", minHeight: 200, display: "block", margin: "0 auto" }}
          >
            <defs>
              <marker id="arr" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                <path d="M0,0 L6,3 L0,6 Z" fill="rgba(255,255,255,0.2)" />
              </marker>
              <marker id="arr-loop" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                <path d="M0,0 L6,3 L0,6 Z" fill="rgba(210,153,34,0.7)" />
              </marker>
              <filter id="glow-filter">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* Row labels */}
            <text x="8" y="93" fontSize="8" fill="rgba(255,255,255,0.18)" fontFamily="Inter,sans-serif" fontWeight="600" letterSpacing="1">RESEARCH</text>
            <text x="8" y="188" fontSize="8" fill="rgba(255,255,255,0.18)" fontFamily="Inter,sans-serif" fontWeight="600" letterSpacing="1">REVIEW</text>

            {/* Straight edges */}
            {/* Sup→Hyp */}
            <line x1="145" y1="90" x2="175" y2="90" className="gedge" markerEnd="url(#arr)" />
            {/* Hyp→Cod */}
            <line x1="285" y1="90" x2="315" y2="90" className="gedge" markerEnd="url(#arr)" />
            {/* Cod→Exec */}
            <line x1="425" y1="90" x2="455" y2="90" className="gedge" markerEnd="url(#arr)" />
            {/* Exec→Crit (vertical) */}
            <line x1="510" y1="112" x2="510" y2="163" className="gedge" markerEnd="url(#arr)" />
            {/* Crit→App */}
            <line x1="455" y1="185" x2="425" y2="185" className="gedge" markerEnd="url(#arr)" />
            {/* App→Fin */}
            <line x1="315" y1="185" x2="285" y2="185" className="gedge" markerEnd="url(#arr)" />

            {/* Loop-back: Critic → Hypothesis (above all nodes) */}
            {showLoop && (
              <path
                d="M 455,185 C 430,185 420,18 230,18 C 140,18 175,66 175,66"
                className="gedge-loop"
                markerEnd="url(#arr-loop)"
              />
            )}

            {/* Nodes */}
            {GRAPH_NODES.map(({ id, label, cx, cy }) => {
              const state = nodeState(id, active, visited);
              const isSelected = selectedId === id;
              const rx = cx - NW / 2;
              const ry = cy - NH / 2;
              const textClass =
                state === "active" ? "gtext-active" : state === "complete" ? "gtext-complete" : "gtext-pending";
              const subClass =
                state === "active" ? "gtext-sub-active" : state === "complete" ? "gtext-sub-complete" : "gtext-sub";

              return (
                <g
                  key={id}
                  onClick={() => setSelectedId(selectedId === id ? null : id)}
                  style={{ cursor: "pointer" }}
                  filter={state === "active" ? "url(#glow-filter)" : undefined}
                >
                  <rect
                    x={rx}
                    y={ry}
                    width={NW}
                    height={NH}
                    rx={8}
                    className={`${
                      state === "active" ? "gnode-active" : state === "complete" ? "gnode-complete" : "gnode-pending"
                    }${isSelected ? " gnode-selected" : ""}`}
                  />
                  <text
                    x={cx}
                    y={cy - 5}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="11"
                    fontWeight="600"
                    fontFamily="Inter, system-ui, sans-serif"
                    className={textClass}
                  >
                    {label}
                  </text>
                  <text
                    x={cx}
                    y={cy + 10}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontFamily="Inter, system-ui, sans-serif"
                    className={subClass}
                  >
                    {state === "active" ? "● active" : state === "complete" ? "✓ done" : "· pending"}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Legend */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 20,
            marginTop: 16,
            paddingTop: 14,
            borderTop: "1px solid var(--border)",
          }}
        >
          {[
            { color: "rgba(255,255,255,0.12)", bg: "rgba(255,255,255,0.03)", label: "Pending" },
            { color: "#2dd4bf", bg: "rgba(45,212,191,0.10)", label: "Active" },
            { color: "rgba(63,185,80,0.45)", bg: "rgba(63,185,80,0.07)", label: "Complete" },
          ].map(({ color, bg, label }) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: 3,
                  border: `1.5px solid ${color}`,
                  background: bg,
                  flexShrink: 0,
                }}
              />
              <span style={{ fontSize: "0.72rem", color: "var(--muted)" }}>{label}</span>
            </div>
          ))}
          {showLoop && (
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div
                style={{
                  width: 20,
                  height: 1.5,
                  borderTop: "1.5px dashed rgba(210,153,34,0.7)",
                  flexShrink: 0,
                }}
              />
              <span style={{ fontSize: "0.72rem", color: "var(--muted)" }}>Revision loop</span>
            </div>
          )}
        </div>
      </div>

      {/* Node detail panel */}
      {selectedNode && (
        <NodeDetailPanel
          node={selectedNode}
          state={selectedState!}
          snapshot={snapshot}
        />
      )}
    </div>
  );
}

function NodeDetailPanel({
  node,
  state,
  snapshot,
}: {
  node: (typeof GRAPH_NODES)[number];
  state: "pending" | "active" | "complete";
  snapshot: RunSnapshot | null;
}) {
  const lastAttempt = snapshot?.attempts[snapshot.attempts.length - 1];

  const outputMap: Partial<Record<WorkflowNode, React.ReactNode>> = {
    hypothesis_agent: lastAttempt ? (
      <div>
        <p style={{ fontSize: "0.85rem", fontWeight: 600, margin: "0 0 4px" }}>{lastAttempt.factor_spec.name}</p>
        <p style={{ fontSize: "0.8rem", color: "var(--muted)", margin: "0 0 8px", lineHeight: 1.5 }}>
          {lastAttempt.factor_spec.thesis}
        </p>
        <div className="expr-block">{lastAttempt.factor_spec.expression}</div>
      </div>
    ) : null,
    coding_agent: lastAttempt ? (
      <div className="code-block" style={{ maxHeight: 220 }}>
        {lastAttempt.generated_code.script}
      </div>
    ) : null,
    execution_tool: lastAttempt ? (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 6 }}>
        {Object.entries(lastAttempt.execution_result.metrics)
          .slice(0, 6)
          .map(([k, v]) => (
            <div key={k} className="metric-chip">
              <p className="section-label" style={{ marginBottom: 3 }}>{k.replaceAll("_", " ")}</p>
              <p style={{ margin: 0, fontSize: "0.95rem", fontWeight: 600, fontFamily: "monospace" }}>
                {formatMetric(v)}
              </p>
            </div>
          ))}
      </div>
    ) : null,
    factor_critic: lastAttempt ? (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <p style={{ fontSize: "0.85rem", color: "var(--text)", margin: 0, lineHeight: 1.5 }}>
          {lastAttempt.critique.summary}
        </p>
        <div className="panel-elevated" style={{ padding: "10px 12px" }}>
          <p className="section-label" style={{ marginBottom: 4 }}>Root Cause</p>
          <p style={{ fontSize: "0.8rem", color: "var(--muted)", margin: 0 }}>{lastAttempt.critique.root_cause}</p>
        </div>
      </div>
    ) : null,
  };

  const content = outputMap[node.id];

  return (
    <div className="panel animate-fade-up" style={{ padding: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <h3 style={{ margin: 0, fontSize: "0.88rem", fontWeight: 600 }}>{node.label}</h3>
        <span
          className={
            state === "active" ? "badge-accent" : state === "complete" ? "badge-success" : "badge-neutral"
          }
        >
          {state}
        </span>
        <span style={{ fontSize: "0.78rem", color: "var(--muted)" }}>{node.desc}</span>
      </div>
      {content ?? (
        <p style={{ fontSize: "0.82rem", color: "var(--subtle)", margin: 0 }}>
          {state === "pending" ? "Not yet reached in this run." : "No output captured for this node."}
        </p>
      )}
    </div>
  );
}
