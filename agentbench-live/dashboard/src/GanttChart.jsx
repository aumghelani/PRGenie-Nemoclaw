import React from "react";

// Simple SVG Gantt — renders one row per span, color-coded by kind.
// Works with live-streaming spans (end_ms = -1 until span closes).
export default function GanttChart({ spans, accent }) {
  if (!spans.length) {
    return <div style={emptyStyle}>waiting for telemetry…</div>;
  }

  const tEnd = Math.max(
    ...spans.map((s) => (s.end_ms != null && s.end_ms > 0 ? s.end_ms : s.start_ms + 100)),
  );
  const tStart = 0;
  const span = Math.max(1, tEnd - tStart);
  const rows = spans.length;
  const ROW_H = 22;
  const W = 600;

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${rows * ROW_H + 30}`} style={{ display: "block" }}>
      {/* time axis */}
      <line x1="0" y1="20" x2={W} y2="20" stroke="#1f2937" />
      {gridTicks(span).map((t, i) => {
        const x = (t / span) * W;
        return (
          <g key={i}>
            <line x1={x} y1="16" x2={x} y2={rows * ROW_H + 30} stroke="#1f293744" />
            <text x={x + 2} y="14" fontSize="9" fill="#64748b">
              {t.toFixed(0)}ms
            </text>
          </g>
        );
      })}

      {spans.map((s, i) => {
        const isOpen = s.end_ms == null || s.end_ms < 0;
        const end = isOpen ? tEnd : s.end_ms;
        const x = (s.start_ms / span) * W;
        const w = Math.max(2, ((end - s.start_ms) / span) * W);
        const y = 24 + i * ROW_H;
        const fill = colorFor(s.kind, accent);
        return (
          <g key={s.span_id}>
            <rect x={x} y={y} width={w} height={ROW_H - 6} rx="3"
                  fill={fill} fillOpacity={isOpen ? 0.55 : 0.85}
                  stroke={fill} strokeWidth="1" />
            <text x={x + 4} y={y + ROW_H - 12} fontSize="10" fill="#0b0f17"
                  style={{ pointerEvents: "none" }}>
              {label(s)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function colorFor(kind, accent) {
  if (kind === "llm") return accent || "#60a5fa";
  if (kind === "tool") return "#fbbf24";
  return "#9ca3af";
}

function label(s) {
  const dur = s.end_ms != null && s.end_ms > 0 ? s.end_ms - s.start_ms : null;
  const ttft = s.attrs?.ttft_ms;
  const parts = [s.name];
  if (dur != null) parts.push(`${dur.toFixed(0)}ms`);
  if (ttft != null) parts.push(`ttft=${ttft.toFixed(0)}`);
  return parts.join(" · ");
}

function gridTicks(span) {
  const n = 5;
  return Array.from({ length: n + 1 }, (_, i) => (i * span) / n);
}

const emptyStyle = {
  height: 200, display: "flex", alignItems: "center", justifyContent: "center",
  color: "#64748b", fontSize: 13,
};
