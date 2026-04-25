import React from "react";

export default function RecommendationsPanel({ recs }) {
  return (
    <section style={{ border: "1px solid #1f2937", borderRadius: 8, padding: 12 }}>
      <h2 style={{ margin: "0 0 8px", fontSize: 14, color: "#fbbf24" }}>
        OPTIMIZER AGENT RECOMMENDATIONS
      </h2>
      <ol style={{ paddingLeft: 18, margin: 0 }}>
        {recs.map((r, i) => (
          <li key={i} style={{ marginBottom: 8, fontSize: 13, lineHeight: 1.4 }}>
            <strong style={{ color: "#e2e8f0" }}>{r.name}</strong>
            {r.expected_savings_ms > 0 && (
              <span style={{ color: "#34d399", marginLeft: 6 }}>
                — saves ~{(r.expected_savings_ms / 1000).toFixed(2)}s
              </span>
            )}
            <div style={{ color: "#94a3b8", marginTop: 2 }}>{r.rationale}</div>
            {r.vllm_flag && (
              <code style={codeStyle}>{r.vllm_flag}</code>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}

const codeStyle = {
  display: "inline-block", marginTop: 4, padding: "2px 6px",
  background: "#0f172a", border: "1px solid #1f2937", borderRadius: 4,
  fontFamily: "ui-monospace, monospace", fontSize: 11, color: "#7dd3fc",
};
