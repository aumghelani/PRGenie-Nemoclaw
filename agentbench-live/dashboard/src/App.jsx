import React, { useEffect, useState, useRef } from "react";
import GanttChart from "./GanttChart.jsx";
import MetricsPanel from "./MetricsPanel.jsx";
import RecommendationsPanel from "./RecommendationsPanel.jsx";
import { listTasks, startRun, streamRun, getRun } from "./api.js";

export default function App() {
  const [tasks, setTasks] = useState([]);
  const [taskId, setTaskId] = useState(null);
  const [baselineRun, setBaselineRun] = useState(null);   // { runId, spans, summary, recs }
  const [optimizedRun, setOptimizedRun] = useState(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    listTasks().then((ts) => {
      setTasks(ts);
      if (ts.length) setTaskId(ts[0].id);
    });
  }, []);

  async function runBoth() {
    if (!taskId) return;
    setRunning(true);
    setBaselineRun({ runId: null, spans: [], summary: null, recs: [] });
    setOptimizedRun({ runId: null, spans: [], summary: null, recs: [] });

    await runMode(taskId, "baseline", setBaselineRun);
    await runMode(taskId, "optimized", setOptimizedRun);
    setRunning(false);
  }

  async function runMode(taskId, mode, setter) {
    const { run_id } = await startRun(taskId, mode);
    setter((s) => ({ ...s, runId: run_id }));
    return new Promise((resolve) => {
      const close = streamRun(run_id, async (evt) => {
        if (evt.event === "span.start" || evt.event === "span.end") {
          setter((s) => upsertSpan(s, evt.span));
        } else if (evt.event === "done") {
          const r = await getRun(run_id);
          setter((s) => ({ ...s, summary: r.trace.summary, recs: r.recommendations || [] }));
          close();
          resolve();
        } else if (evt.event === "error") {
          console.error("run error", evt);
          close();
          resolve();
        }
      });
    });
  }

  return (
    <div style={{ padding: 16, maxWidth: 1400, margin: "0 auto" }}>
      <header style={{ borderBottom: "1px solid #1f2937", paddingBottom: 8, marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>
          AgentBench Live <span style={{ color: "#7dd3fc" }}>·</span> real-time vLLM agent profiler
        </h1>
        <p style={{ color: "#94a3b8", margin: "4px 0 0", fontSize: 13 }}>
          Pick a task → baseline run → optimized run → see the deltas. Powered by vLLM + NeMo Agent Toolkit.
        </p>
      </header>

      <div style={{ display: "flex", gap: 12, marginBottom: 12, alignItems: "center" }}>
        <select
          value={taskId ?? ""}
          onChange={(e) => setTaskId(e.target.value)}
          style={selectStyle}
          disabled={running}
        >
          {tasks.map((t) => (
            <option key={t.id} value={t.id}>{t.title}</option>
          ))}
        </select>
        <button onClick={runBoth} disabled={running || !taskId} style={buttonStyle}>
          {running ? "Running…" : "Run baseline → optimized"}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Pane title="BASELINE (no optimizations)" run={baselineRun} accent="#f87171" />
        <Pane title="OPTIMIZED (prefix cache + headers + spec decode)" run={optimizedRun} accent="#34d399" />
      </div>

      <div style={{ marginTop: 16 }}>
        <MetricsPanel baseline={baselineRun?.summary} optimized={optimizedRun?.summary} />
      </div>

      {optimizedRun?.recs?.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <RecommendationsPanel recs={optimizedRun.recs} />
        </div>
      )}
    </div>
  );
}

function Pane({ title, run, accent }) {
  return (
    <section style={{ border: `1px solid ${accent}33`, borderRadius: 8, padding: 12 }}>
      <h2 style={{ margin: "0 0 8px", fontSize: 14, color: accent }}>{title}</h2>
      <GanttChart spans={run?.spans ?? []} accent={accent} />
    </section>
  );
}

function upsertSpan(state, span) {
  const i = state.spans.findIndex((s) => s.span_id === span.span_id);
  const next = i === -1 ? [...state.spans, span] : state.spans.map((s, j) => (j === i ? span : s));
  return { ...state, spans: next };
}

const selectStyle = {
  background: "#0f172a", color: "#e2e8f0", border: "1px solid #1f2937",
  padding: "6px 10px", borderRadius: 6, minWidth: 280, fontSize: 13,
};

const buttonStyle = {
  background: "#2563eb", color: "white", border: "none",
  padding: "6px 14px", borderRadius: 6, cursor: "pointer", fontSize: 13,
};
