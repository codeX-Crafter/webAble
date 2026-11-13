import React from "react";
import { scorePresentation } from "../scoringPresentation.mjs";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { format, list, readable } from "../utils";

const isNumber = (value) => typeof value === "number" && Number.isFinite(value);

export default function ReportAnalytics({ scoring }) {
  const presentation = scorePresentation(scoring);
  const criteria = list(scoring.criteria);
  const dimensions = list(scoring.dimensions)
    .filter((dimension) => dimension.implemented)
    .map((dimension) => ({
      name: dimension.name,
      Score: isNumber(dimension.score) ? dimension.score : null,
      Coverage: isNumber(dimension.coverage_percentage)
        ? dimension.coverage_percentage
        : null,
    }));
  const statusCounts = new Map();
  for (const criterion of criteria) {
    const status = readable(criterion.status);
    statusCounts.set(status, (statusCounts.get(status) || 0) + 1);
  }
  const distribution = [...statusCounts].map(([name, value]) => ({ name, value }));
  const statusColor = (status) => {
    const normalized = status.toLowerCase();
    if (/\b(pass|passed|success|completed)\b/.test(normalized)) return "var(--theme-success)";
    if (/\b(fail|failed|error|critical|blocked)\b/.test(normalized)) return "var(--theme-danger)";
    if (/\b(warn|warning|moderate|needs review|in progress|partial)\b/.test(normalized)) return "var(--theme-warning)";
    return "var(--theme-text-muted)";
  };

  return (
    <section className="analytics-section" aria-labelledby="analytics-title">
      <h3 id="analytics-title">Audit analytics</h3>
      <p className="field-help">
        Charts summarize only checks and evidence returned by this scan.
      </p>
      <p className="field-help analytics-score-summary">Overall score: {presentation.available ? `${format(scoring.overall_score)} / 100` : "unavailable"} · {format(scoring.overall_coverage)}% evidence coverage · {presentation.label}</p>

      <div className="analytics-grid">
        <article className="panel analytics-chart">
          <h4>Dimension score and coverage</h4>
          {dimensions.length && dimensions.some((item) => item.Score !== null || item.Coverage !== null) ? (
            <>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={dimensions} margin={{ top: 8, right: 12, left: -18, bottom: 8 }}>
                  <CartesianGrid stroke="var(--theme-border)" strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fill: "var(--theme-text-secondary)", fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fill: "var(--theme-text-muted)", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: "var(--theme-container)", border: "1px solid var(--theme-border)", color: "var(--theme-text)" }}
                    formatter={(value, name) => value == null ? "Unavailable" : name === "Score" ? `${value} / 100` : `${value}%`}
                  />
                  <Legend />
                  <Bar dataKey="Score" fill="var(--theme-text)" />
                  <Bar dataKey="Coverage" fill="var(--theme-text-muted)" />
                </BarChart>
              </ResponsiveContainer>
              <p className="field-help">Unavailable dimension values are not plotted as zero.</p>
            </>
          ) : <p className="empty-state">No dimension score or coverage data was returned.</p>}
        </article>
        <article className="panel analytics-chart">
          <h4>Scoring criteria by status</h4>
          {distribution.length ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={distribution}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={58}
                  outerRadius={88}
                  paddingAngle={2}
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {distribution.map((item) => (
                    <Cell key={item.name} fill={statusColor(item.name)} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: "var(--theme-container)", border: "1px solid var(--theme-border)", color: "var(--theme-text)" }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="empty-state">No criterion status data was returned.</p>}
        </article>
      </div>
      <div className="visually-hidden" aria-label="Analytics data table">
        {dimensions.map((item) => (
          <p key={item.name}>{item.name}: score {item.Score ?? "unavailable"}, coverage {item.Coverage ?? "unavailable"}</p>
        ))}
        {distribution.map((item) => <p key={item.name}>{item.name}: {item.value}</p>)}
      </div>
    </section>
  );
}
