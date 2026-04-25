import React from "react";

export default function MetricsPanel({ baseline, optimized }) {
  const rows = [
    { key: "total_ms", label: "End-to-end latency", fmt: (v) => `${(v / 1000).toFixed(2)} s`, lower: true },
    { key: "avg_ttft_ms", label: "Average TTFT / call", fmt: (v) => `${v?.toFixed(0)} ms`, lower: true },
    { key: "decode_throughput_tps", label: "Decode throughput", fmt: (v) => `${v?.toFixed(0)} tok/s`, lower: false },
    { key: "total_output_tokens", label: "Output tokens", fmt: (v) => `${v}`, lower: null },
  ];

  return (
    <section style={{ border: "1px solid #1f2937", borderRadius: 8, padding: 12 }}>
      <h2 style={{ margin: "0 0 8px", fontSize: 14, color: "#a78bfa" }}>BEFORE / AFTER</h2>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ color: "#94a3b8" }}>
            <th style={th}>metric</th>
            <th style={th}>baseline</th>
            <th style={th}>optimized</th>
            <th style={th}>improvement</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const b = baseline?.[r.key];
            const o = optimized?.[r.key];
            const speedup = improvement(b, o, r.lower);
            return (
              <tr key={r.key} style={{ borderTop: "1px solid #1f2937" }}>
                <td style={td}>{r.label}</td>
                <td style={td}>{b != null ? r.fmt(b) : "—"}</td>
                <td style={td}>{o != null ? r.fmt(o) : "—"}</td>
                <td style={{ ...td, color: speedup?.good ? "#34d399" : "#94a3b8", fontWeight: 600 }}>
                  {speedup?.text ?? "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

function improvement(b, o, lowerIsBetter) {
  if (b == null || o == null || b === 0) return null;
  if (lowerIsBetter == null) return null;
  const ratio = lowerIsBetter ? b / o : o / b;
  return { text: `${ratio.toFixed(2)}× faster`, good: ratio > 1.05 };
}

const th = { textAlign: "left", padding: "6px 8px", fontWeight: 500 };
const td = { textAlign: "left", padding: "6px 8px" };
