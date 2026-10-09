import React, { useState, useCallback } from 'react';
import { submitHumanDecision } from '../api';
import { useToast } from './Toast';
import {
  AlertTriangle, Shield, CheckCircle, XCircle,
  Brain, Zap, ChevronDown, ChevronUp, Inbox
} from 'lucide-react';

// ── Risk score → badge ────────────────────────────────────────────────────────

function riskBadgeClass(score) {
  if (score >= 80) return 'badge-critical';
  if (score >= 60) return 'badge-high';
  if (score >= 40) return 'badge-medium';
  return 'badge-low';
}

function riskLabel(score) {
  if (score >= 80) return 'CRITICAL';
  if (score >= 60) return 'HIGH';
  if (score >= 40) return 'MEDIUM';
  return 'LOW';
}

function riskBarColor(score) {
  if (score >= 80) return '#ff4466';
  if (score >= 60) return '#ff8c00';
  if (score >= 40) return '#ffd700';
  return '#00ff88';
}

// ── Decision Card ─────────────────────────────────────────────────────────────

function DecisionCard({ decision, onHandled }) {
  const { toast } = useToast();
  const [expanded, setExpanded]   = useState(false);
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);

  const pkgId = decision.package_id ?? decision._localId;
  const riskScore = Number(decision.risk_score ?? 50);

  const mitreList = decision.correlation_data?.mitre_techniques ?? [];
  const firstMitre = mitreList[0];

  async function handle(action) {
    const set = action === 'approved' ? setApproving : setRejecting;
    set(true);
    try {
      await submitHumanDecision({
        decision_id: pkgId,
        action,
        analyst_id: 'human-analyst-soc',
        notes: `${action === 'approved' ? 'Approved' : 'Rejected'} via HITL dashboard`,
      });
      toast({
        type: action === 'approved' ? 'success' : 'warning',
        title: action === 'approved' ? '✅ SOAR Action Dispatched' : '❌ Decision Rejected',
        message: action === 'approved'
          ? `Package ${pkgId.slice(0, 16)} approved. FortiGate block executing…`
          : `Package ${pkgId.slice(0, 16)} rejected and archived.`,
      });
      onHandled(decision._localId);
    } catch (err) {
      toast({ type: 'error', title: 'API Error', message: err.message });
      set(false);
    }
  }

  return (
    <div
      className="soc-card soc-card-danger hitl-appear relative overflow-hidden"
      style={{ padding: '16px' }}
    >
      {/* Critical pulse border */}
      <div
        className="absolute inset-0 rounded-xl pointer-events-none"
        style={{
          border: '1px solid rgba(255,68,102,.18)',
          boxShadow: riskScore >= 80 ? '0 0 20px rgba(255,68,102,.08) inset' : 'none',
        }}
      />

      {/* Top bar */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <span className="text-sm font-bold text-slate-200 truncate">
            {decision.description?.substring(0, 60) || 'Security Event Detected'}
          </span>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={`badge ${riskBadgeClass(riskScore)}`}>
            {riskLabel(riskScore)} {riskScore}
          </span>
        </div>
      </div>

      {/* Risk bar */}
      <div className="progress-bar mb-3">
        <div
          className="progress-fill"
          style={{
            width: `${riskScore}%`,
            background: `linear-gradient(90deg, ${riskBarColor(riskScore)}, ${riskBarColor(riskScore)}88)`,
          }}
        />
      </div>

      {/* Metadata row */}
      <div className="flex flex-wrap gap-2 mb-3 text-xs font-mono">
        {firstMitre && (
          <span className="badge badge-info">{firstMitre.id} · {firstMitre.name?.substring(0, 30)}</span>
        )}
        <span className="badge badge-medium">{decision.threat_level?.toUpperCase() || 'MEDIUM'}</span>
        <span className="text-slate-600 self-center">
          {pkgId?.substring(0, 20)}…
        </span>
      </div>

      {/* AI Recommendation */}
      <div className="flex items-start gap-2 mb-3 px-3 py-2 rounded-lg border border-cyan-500/12 bg-cyan-500/[.04]">
        <Brain className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-cyan-300/80 leading-relaxed">
          <span className="font-semibold text-cyan-400">AI Recommends: </span>
          {decision.recommended_action || 'Block source IP and isolate host.'}
        </p>
      </div>

      {/* Expandable detail */}
      {expanded && (
        <div className="mb-3 p-3 rounded-lg bg-slate-900/60 border border-slate-700/40 text-xs font-mono space-y-1.5 slide-in-top">
          <div><span className="text-slate-500">ISO 27001: </span>
            <span className="text-slate-300">{(decision.iso_27001_refs ?? []).join(', ') || 'A.16.1.5'}</span>
          </div>
          <div><span className="text-slate-500">Financial Risk: </span>
            <span className="text-yellow-400">${(decision.financial_risk ?? 0).toLocaleString()}</span>
          </div>
          <div><span className="text-slate-500">Category: </span>
            <span className="text-slate-300">{decision.financial_category || 'generic'}</span>
          </div>
          {decision.lessons_from_past && (
            <div><span className="text-slate-500">Past Lessons: </span>
              <span className="text-slate-400">{decision.lessons_from_past?.substring(0, 120)}…</span>
            </div>
          )}
        </div>
      )}

      <button
        onClick={() => setExpanded((e) => !e)}
        className="text-[11px] text-slate-600 hover:text-slate-400 flex items-center gap-1 mb-3 transition-colors font-mono"
      >
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {expanded ? 'Less detail' : 'More detail'}
      </button>

      {/* Action buttons */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => handle('approved')}
          disabled={approving || rejecting}
          className="btn btn-green flex-1 justify-center"
        >
          {approving ? (
            <>
              <Zap className="w-3.5 h-3.5 animate-pulse" />
              Dispatching SOAR…
            </>
          ) : (
            <>
              <CheckCircle className="w-3.5 h-3.5" />
              Approve & Execute SOAR
            </>
          )}
        </button>

        <button
          onClick={() => handle('rejected')}
          disabled={approving || rejecting}
          className="btn btn-red"
        >
          {rejecting ? '…' : <XCircle className="w-3.5 h-3.5" />}
        </button>
      </div>
    </div>
  );
}

// ── HITLDecisions ─────────────────────────────────────────────────────────────

export default function HITLDecisions({ pendingDecisions = [], onDecisionHandled }) {
  return (
    <div className="soc-card p-5 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-red-400" />
          <span className="text-sm font-semibold text-red-400 tracking-wide">
            HITL PENDING DECISIONS
          </span>
        </div>

        {pendingDecisions.length > 0 && (
          <span
            className="text-xs font-mono font-bold px-2.5 py-1 rounded-full"
            style={{
              background: 'rgba(255,68,102,.15)',
              color: '#ff4466',
              border: '1px solid rgba(255,68,102,.3)',
              animation: 'pulse-red 1.5s ease-in-out infinite',
            }}
          >
            {pendingDecisions.length} PENDING
          </span>
        )}
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {pendingDecisions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-slate-600 gap-3">
            <Inbox className="w-8 h-8" />
            <div className="text-center">
              <p className="text-sm font-semibold">No Pending Decisions</p>
              <p className="text-xs mt-1">AI decision packages will appear here when threats are detected</p>
            </div>
          </div>
        ) : (
          pendingDecisions.map((d) => (
            <DecisionCard
              key={d._localId}
              decision={d}
              onHandled={onDecisionHandled}
            />
          ))
        )}
      </div>
    </div>
  );
}
