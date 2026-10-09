import { Wifi, WifiOff, Shield, Zap } from 'lucide-react';

export function TopBar({ wsConnected, backendHealthy, activeView, onViewChange }) {
  const views = [
    { id: 'command', label: 'Command Center', icon: Shield },
    { id: 'malware', label: 'Malware Triage', icon: Zap },
    { id: 'vuln', label: 'Vulnerability Board', icon: Wifi },
    { id: 'audit', label: 'Audit Trail', icon: WifiOff },
  ];

  return (
    <header className="h-16 bg-gray-900/80 backdrop-blur-sm border-b border-cyan-500/20 flex items-center justify-between px-6 z-50">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-cyan-400 rounded-full border-2 border-gray-900 animate-ping" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">AgeixAISOC</h1>
            <p className="text-xs text-cyan-400/70 font-mono">COMMAND DASHBOARD v2.0</p>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-6 ml-8 border-l border-gray-700 pl-8">
          {views.map((view) => (
            <button
              key={view.id}
              onClick={() => onViewChange(view.id)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-200 ${
                activeView === view.id
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              <view.icon className="w-4 h-4" />
              <span className="font-medium text-sm">{view.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-800/50 border border-gray-700">
          <div
            className={`w-2.5 h-2.5 rounded-full transition-all duration-300 ${
              wsConnected ? 'bg-cyan-400 shadow-[0_0_8px_theme(colors.cyan.400)]' : 'bg-gray-500'
            }`}
          />
          <span className="text-xs font-mono text-gray-300">
            WS: {wsConnected ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-800/50 border border-gray-700">
          <div
            className={`w-2.5 h-2.5 rounded-full transition-all duration-300 ${
              backendHealthy
                ? 'bg-green-400 shadow-[0_0_8px_theme(colors.green.400)]'
                : 'bg-red-400 shadow-[0_0_8px_theme(colors.red.400)] animate-pulse'
            }`}
          />
          <span className="text-xs font-mono text-gray-300">
            API: {backendHealthy ? 'HEALTHY' : 'DEGRADED'}
          </span>
        </div>

        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800/50 border border-gray-700 text-xs text-gray-400 font-mono">
          <span id="current-time" className="text-cyan-400">--:--:--</span>
          <span className="text-gray-600">UTC</span>
        </div>
      </div>
    </header>
  );
}