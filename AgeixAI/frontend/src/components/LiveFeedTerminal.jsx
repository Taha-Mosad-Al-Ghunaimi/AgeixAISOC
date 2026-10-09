import { useRef, useEffect, useState } from 'react';
import { Terminal, X, Maximize2, Minimize2, Trash2, Filter, ChevronDown, Pause, Play } from 'lucide-react';

const LOG_COLORS = {
  siem: { bg: 'bg-blue-500/10', border: 'border-blue-500/20', text: 'text-blue-300', icon: 'text-blue-400', label: 'SIEM' },
  agent: { bg: 'bg-green-500/10', border: 'border-green-500/20', text: 'text-green-300', icon: 'text-green-400', label: 'AGENT' },
  threat: { bg: 'bg-red-500/10', border: 'border-red-500/20', text: 'text-red-300', icon: 'text-red-400', label: 'THREAT' },
  soar: { bg: 'bg-purple-500/10', border: 'border-purple-500/20', text: 'text-purple-300', icon: 'text-purple-400', label: 'SOAR' },
  ueba: { bg: 'bg-orange-500/10', border: 'border-orange-500/20', text: 'text-orange-300', icon: 'text-orange-400', label: 'UEBA' },
  system: { bg: 'bg-gray-500/10', border: 'border-gray-500/20', text: 'text-gray-300', icon: 'text-gray-400', label: 'SYS' },
  default: { bg: 'bg-gray-500/10', border: 'border-gray-500/20', text: 'text-gray-300', icon: 'text-gray-400', label: 'LOG' },
};

const AGENT_ICONS = {
  threat_detection: '🔍',
  risk_scoring: '📊',
  recommendation: '📋',
  threat_hunter: '🎯',
  red_team: '⚔️',
  forensics: '🔬',
  master_brain: '🧠',
};

export function LiveFeedTerminal({ wsConnected, onClear }) {
  const [logs, setLogs] = useState([]);
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState('all');
  const [expanded, setExpanded] = useState(false);
  const terminalRef = useRef(null);
  const logCountRef = useRef(0);
  const maxLogs = 500;

  useEffect(() => {
    if (terminalRef.current && !paused) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs, paused]);

  const addLog = (entry) => {
    if (paused) return;
    
    const logEntry = {
      id: ++logCountRef.current,
      timestamp: new Date(),
      type: entry.type || 'system',
      source: entry.source || 'system',
      message: entry.message || JSON.stringify(entry),
      raw: entry,
    };

    setLogs((prev) => {
      const next = [...prev, logEntry];
      return next.slice(-maxLogs);
    });
  };

  const handleWsMessage = (data) => {
    if (data.type === 'agent_log' || data.type === 'system_log' || data.type === 'alert') {
      addLog({
        type: data.level === 'error' ? 'threat' : data.source === 'siem' ? 'siem' : 'agent',
        source: data.source || data.agent,
        message: data.message || data.content || JSON.stringify(data),
      });
    } else if (data.type === 'decision_package') {
      addLog({
        type: 'threat',
        source: 'master_brain',
        message: `DECISION PACKAGE: ${data.threat_name} | MITRE: ${data.mitre_technique} | Risk: ${data.risk_score}`,
      });
    } else if (data.type === 'ueba_alert') {
      addLog({
        type: 'ueba',
        source: 'ueba',
        message: `Anomaly detected: ${data.user} - ${data.description} (score: ${data.anomaly_score})`,
      });
    }
  };

  const filteredLogs = logs.filter((log) => filter === 'all' || log.type === filter);

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const getAgentIcon = (source) => AGENT_ICONS[source] || '🤖';

  return (
    <div className={`flex flex-col h-full bg-gray-950/50 border border-gray-800 rounded-2xl overflow-hidden ${expanded ? 'fixed inset-4 z-50' : ''}`}>
      <div className="flex items-center justify-between px-4 py-3 bg-gray-900/80 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <Terminal className="w-5 h-5 text-cyan-400" />
          <h3 className="text-white font-semibold">LIVE FEED TERMINAL</h3>
          <span className={`px-2 py-0.5 text-xs rounded-full ${wsConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {wsConnected ? 'STREAMING' : 'DISCONNECTED'}
          </span>
          <span className="px-2 py-0.5 text-xs text-gray-500 bg-gray-800 rounded font-mono">
            {filteredLogs.length} / {logs.length}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-white text-sm px-3 py-1.5 rounded-lg focus:outline-none focus:border-cyan-500"
          >
            <option value="all">ALL SOURCES</option>
            <option value="siem">SIEM</option>
            <option value="agent">AGENTS</option>
            <option value="threat">THREATS</option>
            <option value="soar">SOAR</option>
            <option value="ueba">UEBA</option>
            <option value="system">SYSTEM</option>
          </select>

          <button
            onClick={() => setPaused(!paused)}
            className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1 transition-colors ${
              paused ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' : 'bg-gray-800 text-gray-300 border border-gray-700 hover:bg-gray-700'
            }`}
            title={paused ? 'Resume' : 'Pause'}
          >
            {paused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            <span className="hidden sm:inline">{paused ? 'RESUME' : 'PAUSE'}</span>
          </button>

          <button
            onClick={() => { setLogs([]); onClear?.(); }}
            className="px-3 py-1.5 rounded-lg text-sm bg-gray-800 text-gray-300 border border-gray-700 hover:bg-gray-700 hover:text-white transition-colors"
            title="Clear Logs"
          >
            <Trash2 className="w-4 h-4" />
          </button>

          <button
            onClick={() => setExpanded(!expanded)}
            className="px-3 py-1.5 rounded-lg text-sm bg-gray-800 text-gray-300 border border-gray-700 hover:bg-gray-700 hover:text-white transition-colors"
            title={expanded ? 'Minimize' : 'Expand'}
          >
            {expanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

          {expanded && (
            <button
              onClick={() => setExpanded(false)}
              className="px-3 py-1.5 rounded-lg text-sm bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      <div
        ref={terminalRef}
        className="flex-1 overflow-y-auto p-4 space-y-2 font-mono text-sm"
        style={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace" }}
      >
        {filteredLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-600">
            <Terminal className="w-12 h-12 mb-4 opacity-30" />
            <p className="text-center">Waiting for WebSocket events...</p>
            <p className="text-xs text-gray-700 mt-1">Connect backend to see live agent logs</p>
          </div>
        ) : (
          filteredLogs.map((log) => {
            const colors = LOG_COLORS[log.type] || LOG_COLORS.default;
            return (
              <div
                key={log.id}
                className={`flex gap-3 px-3 py-2 rounded-lg border transition-all ${colors.bg} ${colors.border}`}
              >
                <span className={`flex-shrink-0 w-20 text-right font-mono text-xs ${colors.text}`}>
                  {formatTime(log.timestamp)}
                </span>
                <span className={`flex-shrink-0 w-16 text-center text-xs font-medium ${colors.icon}`}>
                  {LOG_COLORS[log.type]?.label || 'LOG'}
                </span>
                <span className={`flex-shrink-0 w-20 text-center text-xs ${colors.icon}`}>
                  {getAgentIcon(log.source)}
                </span>
                <span className={`flex-1 min-w-0 ${colors.text} break-all`}>
                  {log.message}
                </span>
              </div>
            );
          })
        )}
      </div>

      {paused && (
        <div className="absolute inset-0 bg-black/60 flex items-center justify-center z-10 pointer-events-none">
          <div className="bg-gray-900 border border-yellow-500/30 rounded-xl px-6 py-4 text-center">
            <Pause className="w-8 h-8 text-yellow-400 mx-auto mb-2" />
            <p className="text-yellow-400 font-medium">LOG STREAM PAUSED</p>
            <p className="text-xs text-gray-500 mt-1">Click RESUME to continue</p>
          </div>
        </div>
      )}
    </div>
  );
}