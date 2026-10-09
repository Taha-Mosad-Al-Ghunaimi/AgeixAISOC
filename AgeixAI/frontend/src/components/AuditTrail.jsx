import React, { useState, useEffect, useCallback } from 'react';
import { fetchLongTermMemory } from '../api';
import { useToast } from './Toast';
import {
  Brain, RefreshCw, BookOpen, Clock, Shield,
  AlertTriangle, CheckCircle, XCircle, TrendingUp
} from 'lucide-react';

// ── Decision action badge ─────────────────────────────────────────────────────

function ActionBadge({ action }) {
  const cfg = {
    approved: { cls: 'badge-low',     icon: CheckCircle, label: 'APPROVED' },
    rejected: { cls: 'badge-critical', icon: XCircle,    label: 'REJECTED' },
    modified: { cls: 'badge-medium',   icon: AlertTriangle, label: 'MODIFIED' },
  }[action] ?? { cls: 'badge-info', icon: Shield, label: action?.toUpperCase() };

  const Icon = cfg.icon;

  return (
    <span className={`badge ${cfg.cls} gap-1`}>
      <Icon className="w-2.5 h-2.5" />
      {cfg.label}
    </span>
  );
}

// ── Incident row ──────────────────────────────────────────────────────────────

function IncidentRow({ incident, index }) {
  return (
    <div
      className="flex items-start gap-4 px-4 py-3 rounded-xl border border-slate-700/30 hover:border-cyan-500/15 transition-all duration-200 fade-in-up"
      style={{ background: 'rgba(6,13,26,.7)', animationDelay: `${index * 60}ms` }}
    >
      {/* Index */}
      <div
        className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold font-mono"
        style={{ background: 'rgba(0,229,255,.08)', color: '#00e5ff', border: '1px solid rgba(0,229,255,.18)' }}
      >
        {index + 1}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {incident.summary && (
          <p className="text-sm text-slate-300 font-medium mb-1 truncate">{incident.summary}</p>
        )}

        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <ActionBadge action={incident.human_action} />

          {incident.risk_score && (
            <span className="text-slate-500">
              Risk: <span className="text-yellow-400">{incident.risk_score}</span>
            </span>
          )}
          {incident.severity && (
            <span className="text-slate-500">
              Sev: <span className="text-cyan-400">{incident.severity}</span>
            </span>
          )}
          {incident.source && (
            <span className="text-slate-600">{incident.source}</span>
          )}
          {incident.ioc && (
            <span className="text-red-400/70 truncate max-w-[120px]">{incident.ioc}</span>
          )}
        </div>
      </div>

      {/* Similarity score */}
      {incident.similarity != null && (
        <div className="flex-shrink-0 text-right">
          <div className="text-[11px] text-slate-600 font-mono">SIMILARITY</div>
          <div
            className="text-sm font-bold font-mono"
            style={{ color: incident.similarity > 0.7 ? '#00ff88' : incident.similarity > 0.4 ? '#ffd700' : '#94a3b8' }}
          >
            {(incident.similarity * 100).toFixed(0)}%
          </div>
        </div>
      )}
    </div>
  );
}

// ── AuditTrail ────────────────────────────────────────────────────────────────

export default function AuditTrail() {
  const [data, setData]         = useState(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);
  const { toast } = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data: d } = await fetchLongTermMemory();
      setData(d);
      setError(null);
    } catch (err) {
      setError(err.message);
      toast({ type: 'error', title: 'Memory Load Failed', message: err.message });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="fade-in-up space-y-5 h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: 'rgba(0,229,255,.12)', border: '1px solid rgba(0,229,255,.25)' }}
          >
            <Brain className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-200">Audit Trail & AI Memory</h2>
            <p className="text-xs text-slate-500">Long-term RAG memory · Human decision history</p>
          </div>
        </div>

        <button onClick={load} disabled={loading} className="btn btn-cyan">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="soc-card soc-card-danger p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 rounded-xl bg-slate-800/40 animate-pulse" />
          ))}
        </div>
      )}

      {/* Content */}
      {!loading && data && (
        <>
          {/* Stats summary */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="metric-card p-4">
              <div className="flex items-center gap-2 mb-2">
                <BookOpen className="w-4 h-4 text-cyan-400" />
                <span className="text-xs text-slate-500 font-mono">DECISIONS STORED</span>
              </div>
              <div className="text-3xl font-bold font-mono text-cyan-400">
                {data.total_decisions_stored}
              </div>
            </div>

            <div className="metric-card p-4">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-green-400" />
                <span className="text-xs text-slate-500 font-mono">LESSONS AVAILABLE</span>
              </div>
              <div className="text-xl font-bold font-mono text-green-400">
                {data.lessons_available ? 'YES' : 'NO'}
              </div>
            </div>

            <div className="metric-card p-4">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-yellow-400" />
                <span className="text-xs text-slate-500 font-mono">LAST UPDATED</span>
              </div>
              <div className="text-xs font-mono text-yellow-400">
                {data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : '—'}
              </div>
            </div>
          </div>

          {/* Lessons learned */}
          {data.lessons_learned && data.lessons_learned !== 'No similar past incidents found in SOC memory.' && (
            <div
              className="soc-card p-4 flex items-start gap-3"
              style={{ borderColor: 'rgba(0,229,255,.18)' }}
            >
              <Brain className="w-4 h-4 text-cyan-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-cyan-400 mb-1">AI LESSONS LEARNED</p>
                <p className="text-sm text-slate-300 leading-relaxed">{data.lessons_learned}</p>
              </div>
            </div>
          )}

          {/* Empty state */}
          {data.total_decisions_stored === 0 && (
            <div className="soc-card p-10 flex flex-col items-center gap-4 text-slate-600">
              <Brain className="w-12 h-12 opacity-30" />
              <div className="text-center">
                <p className="text-base font-semibold">Memory Is Empty</p>
                <p className="text-sm mt-1">
                  Approve or reject HITL decisions to start building the AI's long-term memory.
                </p>
              </div>
            </div>
          )}

          {/* Incident list */}
          {data.recent_incidents_sample?.length > 0 && (
            <div className="soc-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Clock className="w-4 h-4 text-slate-400" />
                <span className="text-sm font-semibold text-slate-300">
                  Recent Incident Samples
                </span>
                <span className="badge badge-info">{data.recent_incidents_sample.length}</span>
              </div>

              <div className="space-y-2">
                {data.recent_incidents_sample.map((incident, i) => (
                  <IncidentRow key={incident.doc_id ?? i} incident={incident} index={i} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
