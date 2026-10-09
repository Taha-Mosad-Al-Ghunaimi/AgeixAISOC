import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Toaster } from 'sonner';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { LabHealthMonitor } from './LabHealthMonitor';
import { LiveFeedTerminal } from './LiveFeedTerminal';
import { PendingHITLCard } from './PendingHITLCard';
import { MalwareTriageView } from './MalwareTriageView';
import { VulnerabilityBoardView } from './VulnerabilityBoardView';
import { DashboardWebSocket } from '../api';
import { dashboardApi, decisionApi } from '../api';

const VIEWS = {
  command: 'Command Center',
  malware: 'Malware Triage',
  vuln: 'Vulnerability Board',
  audit: 'Audit Trail',
};

function SOCDashboard() {
  const [wsConnected, setWsConnected] = useState(false);
  const [backendHealthy, setBackendHealthy] = useState(false);
  const [activeView, setActiveView] = useState('command');
  const [hitlDecisions, setHitlDecisions] = useState([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [metrics, setMetrics] = useState({
    alerts_24h: 0,
    active_threats: 0,
    hitl_pending: 0,
    soar_executed: 0,
  });
  
  const wsRef = useRef(null);
  const location = useLocation();
  const navigate = useNavigate();
  
  useEffect(() => {
    const path = location.pathname;
    if (path === '/' || path === '/dashboard') setActiveView('command');
    else if (path === '/triaje') setActiveView('malware');
    else if (path === '/vulnerabilidades') setActiveView('vuln');
    else if (path === '/audit') setActiveView('audit');
  }, [location.pathname]);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await dashboardApi.getHealth();
        setBackendHealthy(res.data.status === 'healthy');
      } catch {
        setBackendHealthy(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    wsRef.current = new DashboardWebSocket(
      handleWsMessage,
      setWsConnected
    );
    return () => wsRef.current?.close();
  }, []);

  const handleWsMessage = useCallback((data) => {
    switch (data.type) {
      case 'decision_package':
      case 'hitl_request':
        setHitlDecisions(prev => {
          if (prev.some(d => d.decision_id === data.decision_id)) return prev;
          return [...prev, { ...data, received_at: new Date().toISOString() }];
        });
        break;
      case 'human_decision':
      case 'decision_resolved':
        setHitlDecisions(prev => prev.filter(d => d.decision_id !== data.decision_id));
        break;
      case 'metrics_update':
        setMetrics(prev => ({ ...prev, ...data.metrics }));
        break;
      case 'agent_log':
      case 'system_log':
      case 'alert':
        break;
    }
  }, []);

  const handleDecision = (decisionId) => {
    setHitlDecisions(prev => prev.filter(d => d.decision_id !== decisionId));
  };

  const renderCommandCenter = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="ALERTS (24h)"
          value={metrics.alerts_24h || 1247}
          icon="🔔"
          color="cyan"
          trend="+12%"
          trendColor="green"
        />
        <MetricCard
          title="ACTIVE THREATS"
          value={metrics.active_threats || 23}
          icon="🎯"
          color="red"
          trend="+3"
          trendColor="red"
        />
        <MetricCard
          title="HITL PENDING"
          value={hitlDecisions.length || metrics.hitl_pending || 5}
          icon="🛡️"
          color="yellow"
          trend="0"
          trendColor="gray"
        />
        <MetricCard
          title="SOAR EXECUTED"
          value={metrics.soar_executed || 156}
          icon="⚡"
          color="green"
          trend="+8"
          trendColor="green"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <LiveFeedTerminal wsConnected={wsConnected} />
        </div>
        <div className="space-y-6">
          <div className="bg-gradient-to-br from-gray-900 to-gray-800/50 rounded-2xl border border-gray-800 p-5">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <span className="w-8 h-8 rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
              </span>
              Lab Health Monitor
            </h3>
            <LabHealthMonitor />
          </div>

          <div className="bg-gradient-to-br from-gray-900 to-gray-800/50 rounded-2xl border border-gray-800 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-semibold flex items-center gap-2">
                <span className="w-8 h-8 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                </span>
                Pending HITL Decisions
              </h3>
              <span className={`px-2 py-1 text-xs font-bold rounded-full ${hitlDecisions.length > 0 ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-green-500/20 text-green-400 border border-green-500/30'}`}>
                {hitlDecisions.length > 0 ? `${hitlDecisions.length} PENDING` : 'ALL CLEAR'}
              </span>
            </div>
            {hitlDecisions.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <svg className="w-16 h-16 mx-auto mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 3h.01" /></svg>
                <p className="text-lg font-medium">No Pending Decisions</p>
                <p className="text-sm mt-1">All threats have been reviewed</p>
              </div>
            ) : (
              <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
                {hitlDecisions.map((decision) => (
                  <PendingHITLCard
                    key={decision.decision_id}
                    decision={decision}
                    onClose={handleDecision}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  const viewComponents = {
    command: renderCommandCenter,
    malware: () => <MalwareTriageView />,
    vuln: () => <VulnerabilityBoardView />,
    audit: () => <AuditTrailView />,
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <Toaster position="top-right" theme="dark" />
      
      <Sidebar isCollapsed={sidebarCollapsed} onToggle={setSidebarCollapsed} />
      
      <div className={`transition-all duration-300 ${sidebarCollapsed ? 'ml-20' : 'ml-72'}`}>
        <TopBar
          wsConnected={wsConnected}
          backendHealthy={backendHealthy}
          activeView={activeView}
          onViewChange={(view) => {
            setActiveView(view);
            navigate(`/${view === 'command' ? '' : view}`);
          }}
        />
        
        <main className="p-6 pb-12">
          {viewComponents[activeView]?.()}
        </main>
      </div>
    </div>
  );
}

function MetricCard({ title, value, icon, color, trend, trendColor }) {
  const colors = {
    cyan: { bg: 'bg-cyan-500/20', border: 'border-cyan-500/30', text: 'text-cyan-400' },
    red: { bg: 'bg-red-500/20', border: 'border-red-500/30', text: 'text-red-400' },
    yellow: { bg: 'bg-yellow-500/20', border: 'border-yellow-500/30', text: 'text-yellow-400' },
    green: { bg: 'bg-green-500/20', border: 'border-green-500/30', text: 'text-green-400' },
    purple: { bg: 'bg-purple-500/20', border: 'border-purple-500/30', text: 'text-purple-400' },
  };
  const c = colors[color] || colors.cyan;
  const trendColors = {
    green: 'text-green-400',
    red: 'text-red-400',
    gray: 'text-gray-400',
  };

  return (
    <div className={`bg-gradient-to-br from-gray-900 to-gray-800/50 rounded-2xl p-5 border ${c.bg} ${c.border} relative overflow-hidden`}>
      <div className="absolute top-4 right-4 w-16 h-16 opacity-10">
        <span className="text-4xl">{icon}</span>
      </div>
      <div className="relative z-10">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{title}</p>
        <div className="flex items-baseline gap-2">
          <p className="text-3xl font-bold text-white">{value.toLocaleString()}</p>
          <span className={`text-sm font-medium ${trendColors[trendColor] || 'text-gray-400'}`}>
            {trend.startsWith('+') ? '▲' : '▼'} {trend}
          </span>
        </div>
      </div>
    </div>
  );
}

function AuditTrailView() {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center py-16">
        <svg className="w-16 h-16 text-gray-700 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>
        <h3 className="text-xl text-white font-semibold mb-2">Audit Trail</h3>
        <p className="text-gray-500">Complete history of all SOC decisions, SOAR executions, and analyst actions</p>
      </div>
    </div>
  );
}

export { SOCDashboard };