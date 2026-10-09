import React from 'react';
import StatsBar from './StatsBar';
import LabHealthMonitor from './LabHealthMonitor';
import LiveFeedTerminal from './LiveFeedTerminal';
import HITLDecisions from './HITLDecisions';
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import { useMemo } from 'react';

// ── Micro risk-trend chart from ws messages ───────────────────────────────────

function RiskTrendChart({ wsMessages }) {
  const data = useMemo(() => {
    const aiDecisions = wsMessages
      .filter((m) => m.type === 'ai_decision' && m.data?.risk_score != null)
      .slice(0, 20)
      .reverse();
    return aiDecisions.map((m, i) => ({
      i,
      risk: Number(m.data.risk_score),
      time: m._time,
    }));
  }, [wsMessages]);

  if (data.length < 2) return null;

  return (
    <div className="soc-card p-4">
      <p className="text-xs text-slate-500 font-mono tracking-wide mb-3">
        RISK SCORE TREND (last {data.length} decisions)
      </p>
      <ResponsiveContainer width="100%" height={80}>
        <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#ff4466" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ff4466" stopOpacity={0}   />
            </linearGradient>
          </defs>
          <XAxis dataKey="time" hide />
          <Tooltip
            contentStyle={{ background: '#0a1428', border: '1px solid rgba(0,229,255,.2)', borderRadius: 8, fontSize: 11 }}
            labelStyle={{ color: '#00e5ff' }}
            itemStyle={{ color: '#ff4466' }}
          />
          <Area
            type="monotone"
            dataKey="risk"
            stroke="#ff4466"
            strokeWidth={2}
            fill="url(#riskGrad)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── CommandCenter ─────────────────────────────────────────────────────────────

export default function CommandCenter({
  wsStatus,
  wsMessages,
  pendingDecisions,
  socStats,
  onDecisionHandled,
}) {
  return (
    <div className="flex flex-col gap-4 h-full min-h-0">

      {/* Row 1 — Metrics */}
      <div className="flex-shrink-0">
        <StatsBar socStats={socStats} pendingCount={pendingDecisions.length} />
      </div>

      {/* Risk trend if we have data */}
      {wsMessages.some((m) => m.type === 'ai_decision') && (
        <div className="flex-shrink-0">
          <RiskTrendChart wsMessages={wsMessages} />
        </div>
      )}

      {/* Row 2 — Lab + Terminal */}
      <div className="flex gap-4 flex-shrink-0">
        {/* Lab health — fixed height */}
        <div className="w-[420px] flex-shrink-0">
          <LabHealthMonitor />
        </div>

        {/* Live feed terminal — takes remaining width */}
        <div className="flex-1 min-w-0" style={{ height: 300 }}>
          <LiveFeedTerminal wsMessages={wsMessages} wsStatus={wsStatus} />
        </div>
      </div>

      {/* Row 3 — HITL decisions */}
      <div className="flex-1 min-h-[240px]">
        <HITLDecisions
          pendingDecisions={pendingDecisions}
          onDecisionHandled={onDecisionHandled}
        />
      </div>
    </div>
  );
}
