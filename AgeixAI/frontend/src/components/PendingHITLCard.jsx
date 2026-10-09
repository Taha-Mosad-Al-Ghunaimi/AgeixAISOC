import { useState } from 'react';
import { CheckCircle, XCircle, Eye, Copy, ExternalLink, Loader2, AlertTriangle, Shield, Ban, Zap, Target } from 'lucide-react';
import { decisionApi } from '../api';

const RISK_CONFIG = {
  critical: { label: 'CRITICAL', bg: 'bg-red-500/20', border: 'border-red-500/30', text: 'text-red-400', icon: 'text-red-400' },
  high: { label: 'HIGH', bg: 'bg-orange-500/20', border: 'border-orange-500/30', text: 'text-orange-400', icon: 'text-orange-400' },
  medium: { label: 'MEDIUM', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30', text: 'text-yellow-400', icon: 'text-yellow-400' },
  low: { label: 'LOW', bg: 'bg-green-500/20', border: 'border-green-500/30', text: 'text-green-400', icon: 'text-green-400' },
};

const ACTION_CONFIG = {
  block_ip: { label: 'BLOCK IP', icon: Shield },
  isolate_host: { label: 'ISOLATE HOST', icon: Zap },
  quarantine_file: { label: 'QUARANTINE FILE', icon: Ban },
  investigate: { label: 'INVESTIGATE', icon: Target },
  no_action: { label: 'NO ACTION', icon: AlertTriangle },
};

function ActionIcon({ icon: Icon, className }) {
  return <Icon className={className} />;
}

export function PendingHITLCard({ decision, onClose }) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const risk = RISK_CONFIG[decision.risk_level?.toLowerCase()] || RISK_CONFIG.medium;
  const actionConfig = ACTION_CONFIG[decision.recommended_action] || ACTION_CONFIG.investigate;

  const handleApprove = async () => {
    setLoading(true);
    try {
      await decisionApi.submit(decision.decision_id, 'approve', {
        timestamp: new Date().toISOString(),
        source: 'dashboard',
        src_ip: decision.src_ip || '',
        dst_ip: decision.dst_ip || '',
        recommended_action: decision.recommended_action || 'investigate',
        risk_score: decision.risk_score,
        mitre_technique: decision.mitre_technique,
        threat_name: decision.threat_name,
      });
      onClose?.(decision.decision_id);
    } catch (error) {
      console.error('[HITL] Approve failed:', error);
      alert('Failed to approve decision. Check backend connection.');
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    try {
      await decisionApi.submit(decision.decision_id, 'reject', {
        timestamp: new Date().toISOString(),
        source: 'dashboard',
        reason: 'Manual rejection',
      });
      onClose?.(decision.decision_id);
    } catch (error) {
      console.error('[HITL] Reject failed:', error);
      alert('Failed to reject decision. Check backend connection.');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`relative group bg-gray-900/50 border rounded-2xl p-5 transition-all duration-300 ${risk.bg} ${risk.border} shadow-[0_0_20px_rgba(0,0,0,0.3)]`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-4">
            <div className={`p-3 rounded-xl ${risk.bg} ${risk.border}`}>
              <ActionIcon icon={actionConfig.icon} className={`w-6 h-6 ${risk.icon}`} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h4 className="text-white font-bold text-lg truncate">{decision.threat_name || 'Unknown Threat'}</h4>
                <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${risk.bg} ${risk.text} border ${risk.border}`}>
                  {risk.label}
                </span>
                <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30">
                  HITL REQUIRED
                </span>
              </div>
              <p className="text-gray-400 text-sm mt-1">{decision.threat_description || 'No description available'}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <div className="bg-gray-800/50 rounded-xl p-3 border border-gray-700">
              <p className="text-xs text-gray-500 uppercase tracking-wider">MITRE ATT&CK</p>
              <p className="text-white font-mono font-medium text-sm">{decision.mitre_technique || 'T0000'}</p>
              <p className="text-xs text-gray-500 mt-1">{decision.mitre_tactic || 'Unknown'}</p>
            </div>
            <div className="bg-gray-800/50 rounded-xl p-3 border border-gray-700">
              <p className="text-xs text-gray-500 uppercase tracking-wider">RISK SCORE</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${risk.text.replace('text', 'bg')}`}
                    style={{ width: `${decision.risk_score}%` }}
                  />
                </div>
                <span className={`text-lg font-bold ${risk.text}`}>{decision.risk_score}/100</span>
              </div>
            </div>
            <div className="bg-gray-800/50 rounded-xl p-3 border border-gray-700">
              <p className="text-xs text-gray-500 uppercase tracking-wider">RECOMMENDED ACTION</p>
              <div className="flex items-center gap-2 mt-1">
                <ActionIcon icon={actionConfig.icon} className={`w-5 h-5 ${risk.icon}`} />
                <span className="text-white font-medium text-sm">{actionConfig.label}</span>
              </div>
            </div>
            <div className="bg-gray-800/50 rounded-xl p-3 border border-gray-700">
              <p className="text-xs text-gray-500 uppercase tracking-wider">CONFIDENCE</p>
              <p className="text-white font-bold text-lg">{decision.confidence || 0}%</p>
            </div>
          </div>

          {expanded && (
            <div className="border-t border-gray-800 pt-4 mt-4 space-y-3 animate-slide-down">
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">AFFECTED ENTITIES</p>
                <div className="flex flex-wrap gap-2">
                  {decision.affected_entities?.map((entity, i) => (
                    <span key={i} className="px-2 py-1 bg-gray-800 rounded-lg text-sm text-gray-300 font-mono">
                      {entity}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">AI REASONING</p>
                <p className="text-gray-300 text-sm bg-gray-800/50 p-3 rounded-lg border border-gray-700">
                  {decision.ai_reasoning || 'No reasoning provided'}
                </p>
              </div>

              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">EXTRACTED IOCS</p>
                <div className="flex flex-wrap gap-2">
                  {decision.iocs?.map((ioc, i) => (
                    <span
                      key={i}
                      className="px-2 py-1 bg-gray-800 rounded-lg text-sm text-cyan-300 font-mono cursor-pointer hover:bg-gray-700"
                      onClick={() => copyToClipboard(ioc)}
                      title="Click to copy"
                    >
                      {ioc}
                      {copied && <CheckCircle className="w-3 h-3 inline ml-1 text-green-400" />}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2 shrink-0">
          <button
            onClick={handleApprove}
            disabled={loading}
            className="w-full px-4 py-2.5 rounded-xl bg-gradient-to-r from-green-500 to-green-600 text-white font-bold text-sm flex items-center justify-center gap-2 hover:from-green-600 hover:to-green-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(34,197,94,0.3)]"
          >
            <CheckCircle className="w-5 h-5" />
            <span>{loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'APPROVE & EXECUTE SOAR'}</span>
          </button>

          <button
            onClick={handleReject}
            disabled={loading}
            className="w-full px-4 py-2 rounded-xl bg-gray-800 border border-gray-700 text-gray-300 font-medium text-sm flex items-center justify-center gap-2 hover:bg-gray-700 hover:text-white hover:border-gray-600 transition-colors disabled:opacity-50"
          >
            <XCircle className="w-5 h-5" />
            REJECT
          </button>

          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full px-4 py-1.5 rounded-lg bg-gray-800/50 border border-gray-700 text-gray-400 text-xs flex items-center justify-center gap-1 hover:bg-gray-800 hover:text-white transition-colors"
          >
            <Eye className={`w-4 h-4 ${expanded ? 'rotate-180' : ''}`} />
            {expanded ? 'COLLAPSE' : 'EXPAND DETAILS'}
          </button>
        </div>
      </div>

      <div className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={() => copyToClipboard(JSON.stringify(decision, null, 2))}
          className="p-2 rounded-lg bg-gray-800/50 border border-gray-700 text-gray-400 hover:text-white hover:bg-gray-800 hover:border-gray-600 transition-colors"
          title="Copy JSON"
        >
          <Copy className="w-4 h-4" />
        </button>
        <button
          onClick={() => window.open(`/decision/${decision.decision_id}`, '_blank')}
          className="p-2 rounded-lg bg-gray-800/50 border border-gray-700 text-gray-400 hover:text-white hover:bg-gray-800 hover:border-gray-600 transition-colors"
          title="View Details"
        >
          <ExternalLink className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}