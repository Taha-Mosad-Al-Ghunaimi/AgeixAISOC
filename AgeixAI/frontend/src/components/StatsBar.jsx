import React from 'react';
import { AlertCircle, CheckCircle, Shield, Activity, TrendingDown } from 'lucide-react';

// ── Individual metric card ────────────────────────────────────────────────────

function MetricCard({ icon: Icon, label, value, sub, color, glow, trend }) {
  return (
    <div
      className="metric-card p-4 cursor-default"
      style={{ '--glow': glow }}
    >
      <div className="flex items-start justify-between mb-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: `${color}18`, border: `1px solid ${color}30` }}
        >
          <Icon className="w-4 h-4" style={{ color }} />
        </div>
        {trend != null && (
          <span
            className="text-xs font-mono"
            style={{ color: trend >= 0 ? '#00ff88' : '#ff4466' }}
          >
            {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%
          </span>
        )}
      </div>

      <div
        className="text-3xl font-bold font-mono mb-0.5"
        style={{ color }}
      >
        {value ?? '—'}
      </div>

      <div className="text-xs font-semibold text-slate-400 tracking-wide uppercase mb-0.5">
        {label}
      </div>

      {sub && (
        <div className="text-[11px] text-slate-600 font-mono">{sub}</div>
      )}
    </div>
  );
}

// ── StatsBar ──────────────────────────────────────────────────────────────────

export default function StatsBar({ socStats, pendingCount }) {
  const stats = socStats ?? {};

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <MetricCard
        icon={AlertCircle}
        label="Active Alerts"
        value={stats.active_alerts ?? 0}
        color="#ff4466"
        glow="rgba(255,68,102,.2)"
      />
      <MetricCard
        icon={Shield}
        label="Pending HITL"
        value={pendingCount ?? 0}
        color="#ffd700"
        glow="rgba(255,215,0,.2)"
        sub="awaiting human approval"
      />
      <MetricCard
        icon={CheckCircle}
        label="Threats Blocked"
        value={stats.threats_blocked ?? 0}
        color="#00ff88"
        glow="rgba(0,255,136,.2)"
      />
      <MetricCard
        icon={TrendingDown}
        label="Noise Reduced"
        value={stats.noise_reduction_pct != null ? `${stats.noise_reduction_pct}%` : '—'}
        color="#00e5ff"
        glow="rgba(0,229,255,.2)"
        sub={`${stats.total_logs_processed ?? 0} logs processed`}
      />
    </div>
  );
}
