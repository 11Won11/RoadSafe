import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, LineChart, Line, Legend, Area, AreaChart,
} from "recharts";

const SHAP_COLORS = [
  "#ff4d4d","#ff6b6b","#ff8c42","#ffa756","#ffbd6b",
  "#ffd166","#e8c54e","#c9b93c","#aaa82e","#8b9724",
  "#6d861b","#4d7512","#2d640a","#4d9fff","#7db8ff",
  "#b0d3ff","#d4e8ff","#4dffb4","#a0ffd6","#d6fff0","#ffffff",
];

function ShapBar({ data }) {
  const top10 = data.slice(0, 10);
  const maxVal = top10[0]?.value ?? 1;

  return (
    <div>
      {top10.map((item, i) => (
        <div key={item.feature} style={{ marginBottom: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>{item.label}</span>
            <span style={{ fontSize: "0.8rem", fontWeight: 700, fontFamily: "Inter", color: SHAP_COLORS[i] }}>
              {item.value.toFixed(3)}
            </span>
          </div>
          <div className="progress-bar-wrap">
            <div
              className="progress-bar-fill"
              style={{
                width: `${(item.value / maxVal) * 100}%`,
                background: `linear-gradient(90deg, ${SHAP_COLORS[i]}, ${SHAP_COLORS[i]}80)`,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function PAIChart({ data }) {
  const chartData = data.map(r => ({
    name: `상위 ${r.k}%`,
    포착률: r.capture,
    이상적: r.k,
    RRI: r.rri ?? null,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="captureGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#ff4d4d" stopOpacity={0.35} />
            <stop offset="95%" stopColor="#ff4d4d" stopOpacity={0}    />
          </linearGradient>
          <linearGradient id="idealGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#4d9fff" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#4d9fff" stopOpacity={0}    />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="name" tick={{ fill: "#8b95b0", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: "#8b95b0", fontSize: 11 }} axisLine={false} tickLine={false} unit="%" domain={[0, 100]} />
        <Tooltip
          contentStyle={{ background: "#111827", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, fontSize: 12 }}
          labelStyle={{ color: "#f0f4ff", fontWeight: 700 }}
          itemStyle={{ color: "#8b95b0" }}
          formatter={(v) => [`${v}%`]}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: "#8b95b0" }} />
        <Area type="monotone" dataKey="이상적" stroke="#4d9fff" strokeWidth={1.5} strokeDasharray="5 3" fill="url(#idealGrad)" dot={false} />
        <Area type="monotone" dataKey="포착률" stroke="#ff4d4d" strokeWidth={2.5} fill="url(#captureGrad)" dot={{ r: 4, fill: "#ff4d4d", strokeWidth: 0 }} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function AurocCard({ metrics }) {
  const rows = [
    { label: "AUROC (2025 미래 예측)", value: metrics.auroc_2025, color: "var(--accent)" },
    { label: "AUROC (전체 2021-25)",   value: metrics.auroc_all,  color: "var(--accent-orange)" },
    { label: "AUROC (부산 전이성)",     value: metrics.auroc_busan, color: "var(--accent-blue)" },
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {rows.map(r => (
        <div key={r.label}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <span style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>{r.label}</span>
            <span style={{ fontSize: "0.95rem", fontWeight: 800, fontFamily: "Inter", color: r.color }}>
              {r.value.toFixed(4)}
            </span>
          </div>
          <div className="progress-bar-wrap" style={{ height: 6 }}>
            <div
              className="progress-bar-fill"
              style={{ width: `${r.value * 100}%`, background: `linear-gradient(90deg, ${r.color}, ${r.color}99)` }}
            />
          </div>
        </div>
      ))}

      {/* PAI 표 */}
      <div style={{ marginTop: 8 }}>
        <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10 }}>
          PAI 포착률 (2025 기준)
        </div>
        <div className="pai-table-wrapper">
          <table className="pai-table">
            <thead>
              <tr>
                <th>단속 범위</th>
                <th>사고 포착률</th>
                <th>RRI</th>
              </tr>
            </thead>
            <tbody>
              {(metrics.pai_table_2025 ?? []).map(r => (
                <tr key={r.k}>
                  <td>상위 {r.k}%</td>
                  <td className="highlight">{r.capture}%</td>
                  <td style={{ color: r.rri >= 1 ? "var(--accent-green)" : "var(--text-secondary)" }}>
                    {r.rri?.toFixed(2) ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export function AnalysisSection({ metrics, shap }) {
  if (!metrics || !shap) return null;

  return (
    <section className="section" id="analysis">
      <div className="container">
        <div className="section-header">
          <span className="section-eyebrow">Model Performance</span>
          <h2 className="section-title">성능 분석</h2>
          <p className="section-desc">
            AUROC·PAI·SHAP을 통해 모델의 예측력과 핵심 위험 요인을 분석합니다.
          </p>
        </div>

        <div className="charts-grid">
          <div className="glass-card chart-card">
            <div className="chart-title">📈 AUROC & PAI 지표</div>
            <div className="chart-sub">시간적 홀드아웃 + 공간 전이성 검증 결과</div>
            <AurocCard metrics={metrics} />
          </div>

          <div className="glass-card chart-card">
            <div className="chart-title">🎯 포착률 곡선 (2025 미래 예측)</div>
            <div className="chart-sub">상위 k% 단속 시 예방 가능한 사고 비율</div>
            <PAIChart data={metrics.pai_table_2025 ?? []} />
          </div>

          <div className="glass-card chart-card" style={{ gridColumn: "1 / -1" }}>
            <div className="chart-title">🔍 SHAP Feature Importance</div>
            <div className="chart-sub">모델이 위험도 판단 시 각 Feature를 얼마나 중요하게 고려했는지 (평균 절대 SHAP 값)</div>
            <ShapBar data={shap} />
          </div>
        </div>
      </div>
    </section>
  );
}
