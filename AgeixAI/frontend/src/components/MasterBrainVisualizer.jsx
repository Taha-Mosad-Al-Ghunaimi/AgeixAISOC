import { useState, useEffect } from 'react';
import { Brain, Search, AlertTriangle, Shield, Activity, GitBranch, Target, ChevronRight, ChevronDown, Zap } from 'lucide-react';
import api from '../api';

const PIPELINE_NODES = [
  { id: 'forensics', label: 'Forensics', icon: Search, color: 'text-purple-400', bg: 'bg-purple-500/20', border: 'border-purple-500/30' },
  { id: 'threat_hunt', label: 'Threat Hunt', icon: Activity, color: 'text-blue-400', bg: 'bg-blue-500/20', border: 'border-blue-500/30' },
  { id: 'threat_detection', label: 'Detection', icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/30' },
  { id: 'risk_scoring', label: 'Risk Score', icon: Shield, color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30' },
  { id: 'recommendation', label: 'Recommend', icon: GitBranch, color: 'text-green-400', bg: 'bg-green-500/20', border: 'border-green-500/30' },
  { id: 'red_team', label: 'Red Team', icon: Target, color: 'text-orange-400', bg: 'bg-orange-500/20', border: 'border-orange-500/30' },
];

export function MasterBrainVisualizer() {
  const [activePipeline, setActivePipeline] = useState(null);
  const [stats, setStats] = useState({ enabled: false, count: 0 });
  const [recentIncidents, setRecentIncidents] = useState([]);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await api.get('/api/rag/stats');
        setStats(res.data);
      } catch { /* ignore */ }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-br from-gray-900 to-gray-800/50 rounded-2xl border border-cyan-500/20 p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <Brain className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Master Brain</h2>
              <p className="text-sm text-gray-400">AI Orchestrator — 6-Agent LangGraph Pipeline</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="px-3 py-1.5 rounded-full bg-gray-800 border border-gray-700 text-xs text-gray-300 font-mono">
              RAG: {stats.count} incidents
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-800 border border-gray-700">
              <div className="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.5)]" />
              <span className="text-xs font-mono text-green-400">ACTIVE</span>
            </div>
          </div>
        </div>

        <div className="relative">
          <PipelineFlow activeNode={activePipeline} onNodeClick={setActivePipeline} />
        </div>
      </div>

      {activePipeline && <AgentDetailPanel agentId={activePipeline} onClose={() => setActivePipeline(null)} />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-gradient-to-br from-gray-900 to-gray-800/50 rounded-2xl border border-gray-800 p-5">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-cyan-400" />
            Memory & Learning
          </h3>
          <MemoryPanel stats={stats} />
        </div>

        <div className="bg-gradient-to-br from-gray-900 to-gray-800/50 rounded-2xl border border-gray-800 p-5">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Brain className="w-4 h-4 text-purple-400" />
            Agent Status
          </h3>
          <AgentStatusList stats={stats} />
        </div>
      </div>
    </div>
  );
}

function PipelineFlow({ activeNode, onNodeClick }) {
  return (
    <div className="flex items-start justify-between gap-2 overflow-x-auto pb-4">
      {PIPELINE_NODES.map((node, idx) => {
        const Icon = node.icon;
        const isActive = activeNode === node.id;
        return (
          <div key={node.id} className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => onNodeClick(isActive ? null : node.id)}
              className={`group flex flex-col items-center gap-2 p-4 rounded-xl transition-all duration-200 border cursor-pointer
                ${isActive
                  ? `${node.bg} ${node.border} shadow-lg`
                  : 'border-gray-800 hover:border-gray-600 hover:bg-gray-800/30'
                }`}
            >
              <div className={`w-10 h-10 rounded-xl ${node.bg} border ${node.border} flex items-center justify-center transition-transform group-hover:scale-110`}>
                <Icon className={`w-5 h-5 ${node.color}`} />
              </div>
              <span className="text-xs font-medium text-gray-300 whitespace-nowrap">{node.label}</span>
              <span className="text-[10px] text-gray-500 font-mono">Agent {idx + 1}</span>
            </button>
            {idx < PIPELINE_NODES.length - 1 && (
              <ChevronRight className="w-5 h-5 text-gray-600 flex-shrink-0" />
            )}
          </div>
        );
      })}
    </div>
  );
}

function AgentDetailPanel({ agentId, onClose }) {
  const node = PIPELINE_NODES.find(n => n.id === agentId);
  if (!node) return null;

  const Icon = node.icon;
  const details = {
    forensics: {
      title: 'Digital Forensics Analyst',
      model: 'qwen2.5:14b (master_brain)',
      description: 'Queries past incident memory (RAG) for similar threats and response patterns. Maintains a knowledge base of past attacks and their resolution playbooks.',
      inputs: ['Raw SIEM alert', 'RAG memory context'],
      outputs: ['Similar incidents', 'Recurrence patterns', 'Past recommendations', 'Lessons learned'],
      tools: ['ChromaDB RAG Query'],
    },
    threat_hunt: {
      title: 'Threat Hunter',
      model: 'llama3.1 (osint)',
      description: 'Proactively searches for CVEs, IoCs, and threat reports related to the alert. Uses open-source intelligence to enrich every alert with real-world context.',
      inputs: ['Alert context', 'IOC list'],
      outputs: ['CVEs found', 'Related campaigns', 'IOC enrichment', 'OSINT notes'],
      tools: ['WebSearch (DuckDuckGo)'],
    },
    threat_detection: {
      title: 'Threat Detection Specialist',
      model: 'llama3.1 (triage)',
      description: 'Classifies raw SIEM alerts, maps to MITRE ATT&CK techniques, and identifies IOCs with confidence scoring.',
      inputs: ['Alert JSON', 'MITRE ATT&CK framework'],
      outputs: ['Threat name', 'MITRE technique ID', 'IOC list', 'Confidence score'],
      tools: ['MITRE ATT&CK mapping'],
    },
    risk_scoring: {
      title: 'Risk Scoring Analyst',
      model: 'llama3.1 (triage)',
      description: 'Computes quantitative risk scores (0–100) with business impact assessment using FAIR / ISO 27005 models.',
      inputs: ['Alert context', 'Forensics report', 'Threat intel'],
      outputs: ['Risk score', 'Impact level', 'Financial impact (USD)', 'Likelihood', 'Affected assets'],
      tools: ['FAIR risk model'],
    },
    recommendation: {
      title: 'SOAR Playbook Advisor',
      model: 'qwen2.5-coder:7b (coder)',
      description: 'Drafts ISO 27001-aligned remediation actions and structured SOAR playbooks with precise FortiGate CLI commands.',
      inputs: ['Risk assessment', 'Alert context'],
      outputs: ['Recommended action', 'Playbook steps', 'FortiGate commands', 'Containment estimate'],
      tools: ['n8n SOAR webhook', 'FortiGate API'],
    },
    red_team: {
      title: 'Red Team Operator',
      model: 'qwen2.5-coder:7b (coder)',
      description: 'Simulates attacker paths and identifies security gaps. Maps potential attack chains and recommends defensive improvements.',
      inputs: ['Alert context', 'SOAR playbook'],
      outputs: ['Attack paths', 'Security gaps', 'Recommended defenses', 'Priority level'],
      tools: ['WebSearch', 'Attack path modeling'],
    },
  };

  const info = details[agentId] || {};

  return (
    <div className={`bg-gradient-to-br from-gray-900 to-gray-800/50 rounded-2xl border ${node.border} p-5`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl ${node.bg} flex items-center justify-center`}>
            <Icon className={`w-5 h-5 ${node.color}`} />
          </div>
          <div>
            <h3 className="text-white font-semibold">{info.title}</h3>
            <p className="text-xs text-gray-400 font-mono">{info.model}</p>
          </div>
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
          <ChevronDown className="w-5 h-5" />
        </button>
      </div>

      <p className="text-sm text-gray-300 mb-4">{info.description}</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Inputs</h4>
          <ul className="space-y-1">
            {info.inputs?.map((inp, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-gray-300">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 flex-shrink-0" />
                {inp}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Outputs</h4>
          <ul className="space-y-1">
            {info.outputs?.map((out, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-gray-300">
                <div className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
                {out}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {info.tools?.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-800">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Tools</h4>
          <div className="flex flex-wrap gap-2">
            {info.tools.map((tool, i) => (
              <span key={i} className="px-2 py-1 text-xs rounded-full bg-gray-800 border border-gray-700 text-gray-300">
                {tool}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MemoryPanel({ stats }) {
  return (
    <div className="space-y-4">
      {stats.enabled ? (
        <div className="flex items-center gap-4">
          <div className="flex-1 p-4 rounded-xl bg-gray-800/50 border border-gray-700">
            <p className="text-2xl font-bold text-cyan-400">{stats.count}</p>
            <p className="text-xs text-gray-400 mt-1">Incidents in RAG Memory</p>
          </div>
          <div className="flex-1 p-4 rounded-xl bg-gray-800/50 border border-gray-700">
            <p className="text-2xl font-bold text-green-400">ChromaDB</p>
            <p className="text-xs text-gray-400 mt-1">Vector Store Engine</p>
          </div>
        </div>
      ) : (
        <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-sm">
          ChromaDB not installed — RAG memory is disabled. Run: pip install chromadb
        </div>
      )}

      <p className="text-sm text-gray-400">
        RAG Memory enables agents to learn from past incidents and avoid repeating the same mistakes.
        Each decision package is embedded and stored for similarity search.
      </p>
    </div>
  );
}

function AgentStatusList({ stats }) {
  return (
    <div className="space-y-2">
      {PIPELINE_NODES.map((node) => {
        const Icon = node.icon;
        return (
          <div key={node.id} className="flex items-center gap-3 p-2.5 rounded-lg bg-gray-800/30 border border-gray-800">
            <div className={`w-8 h-8 rounded-lg ${node.bg} flex items-center justify-center`}>
              <Icon className={`w-4 h-4 ${node.color}`} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{node.label}</p>
              <p className="text-xs text-gray-500">Online</p>
            </div>
            <div className="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.5)]" />
          </div>
        );
      })}
    </div>
  );
}
