import { startTransition, useDeferredValue, useState } from "react";

import { approveRun, createRun, type RunSnapshot } from "./api";
import {
  ArtifactPane,
  AttemptComparisonCard,
  StatusHeader,
  WorkflowGraphView,
  WorkflowRail,
} from "./components";

type MainTab = "run" | "graph";

export default function App() {
  const [snapshot, setSnapshot] = useState<RunSnapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mainTab, setMainTab] = useState<MainTab>("run");

  const deferredSnapshot = useDeferredValue(snapshot);

  async function handleRunDemo() {
    setBusy(true);
    setError(null);
    try {
      const next = await createRun();
      startTransition(() => setSnapshot(next));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start run.");
    } finally {
      setBusy(false);
    }
  }

  async function handleApproval(approved: boolean) {
    if (!snapshot) return;
    setBusy(true);
    setError(null);
    try {
      const next = await approveRun(snapshot.run_id, approved);
      startTransition(() => setSnapshot(next));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit approval.");
    } finally {
      setBusy(false);
    }
  }

  const awaitingApproval = snapshot?.approval_status === "pending";

  return (
    <div
      className="bg-grid"
      style={{ minHeight: "100vh", background: "var(--bg)" }}
    >
      {/* Top nav */}
      <StatusHeader
        snapshot={deferredSnapshot}
        busy={busy}
        activeTab={mainTab}
        onTabChange={setMainTab}
      />

      {mainTab === "run" ? (
        <div
          style={{
            maxWidth: 1520,
            margin: "0 auto",
            padding: "20px 20px 40px",
            display: "grid",
            gridTemplateColumns: "minmax(280px, 340px) minmax(0, 1fr)",
            gap: 16,
            alignItems: "start",
          }}
        >
          {/* ── Left column ───────────────────────────────────── */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {/* Brief / run info */}
            <div className="panel" style={{ padding: 16 }}>
              <p className="eyebrow">Research Brief</p>
              <p
                style={{
                  fontSize: "0.82rem",
                  color: deferredSnapshot ? "var(--text)" : "var(--subtle)",
                  lineHeight: 1.55,
                  margin: 0,
                }}
              >
                {deferredSnapshot?.brief ??
                  "Propose a factor, generate a backtest script, execute it, critique the result, revise once, then await human approval."}
              </p>
            </div>

            {/* Workflow rail */}
            <WorkflowRail snapshot={deferredSnapshot} />

            {/* Attempt comparison — only when ≥2 attempts */}
            {(deferredSnapshot?.attempts.length ?? 0) >= 2 && (
              <AttemptComparisonCard snapshot={deferredSnapshot!} />
            )}

            {/* Action controls */}
            <div
              className="panel"
              style={{ padding: 16, display: "flex", flexDirection: "column", gap: 8 }}
            >
              <p className="eyebrow">Controls</p>

              <button
                className="btn-primary"
                disabled={busy}
                onClick={handleRunDemo}
              >
                {busy ? "Running…" : "Run Demo"}
              </button>

              {awaitingApproval && (
                <>
                  <button
                    className="btn-secondary"
                    disabled={busy}
                    onClick={() => handleApproval(true)}
                  >
                    Approve Result
                  </button>
                  <button
                    className="btn-ghost"
                    disabled={busy}
                    onClick={() => handleApproval(false)}
                  >
                    Reject
                  </button>
                </>
              )}

              {error && (
                <p
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--danger)",
                    margin: 0,
                    lineHeight: 1.45,
                  }}
                >
                  {error}
                </p>
              )}

              {/* Run meta */}
              {deferredSnapshot && (
                <div style={{ display: "flex", flexDirection: "column", gap: 0, marginTop: 4 }}>
                  {[
                    { label: "Phase", value: deferredSnapshot.phase },
                    { label: "Node", value: deferredSnapshot.current_node ?? "—" },
                    { label: "Decision", value: deferredSnapshot.supervisor_decision ?? "—" },
                  ].map(({ label, value }) => (
                    <div key={label} className="kv-row">
                      <span className="kv-label">{label}</span>
                      <span
                        className="kv-value"
                        style={{ fontSize: "0.75rem", fontFamily: "monospace" }}
                      >
                        {value}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* ── Right column ──────────────────────────────────── */}
          <ArtifactPane snapshot={deferredSnapshot} />
        </div>
      ) : (
        <div
          style={{
            maxWidth: 1680,
            margin: "0 auto",
            padding: "20px 20px 40px",
          }}
        >
          <WorkflowGraphView snapshot={deferredSnapshot} />
        </div>
      )}
    </div>
  );
}
