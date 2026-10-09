import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: DashboardIcon, badge: null },
  { path: '/triaje', label: 'Malware Triage', icon: ShieldAlertIcon, badge: 'NEW' },
  { path: '/vulnerabilidades', label: 'Vulnerability Board', icon: BugIcon, badge: '3' },
  { path: '/cracs', label: 'CRACS Engine', icon: ZapIcon, badge: null },
  { path: '/ueba', label: 'UEBA Anomalies', icon: ActivityIcon, badge: null },
  { path: '/lab', label: 'Lab Control', icon: ServerIcon, badge: 'LIVE' },
  { path: '/soar', label: 'SOAR Playbooks', icon: GitBranchIcon, badge: null },
  { path: '/config', label: 'Configuration', icon: SettingsIcon, badge: null },
];

export function Sidebar({ isCollapsed, onToggle }) {
  const location = useLocation();
  const [hoveredItem, setHoveredItem] = useState(null);

  return (
    <aside
      className={`fixed left-0 top-0 z-40 h-full bg-gray-900/95 backdrop-blur-sm border-r border-gray-800 transition-all duration-300 ${
        isCollapsed ? 'w-20' : 'w-72'
      }`}
      onMouseEnter={() => !isCollapsed && onToggle(false)}
      onMouseLeave={() => !isCollapsed && onToggle(true)}
    >
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-800">
          {!isCollapsed && (
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-gray-900 animate-pulse" />
              </div>
              <div>
                <h1 className="text-white font-bold text-lg tracking-tight">AgeixAISOC</h1>
                <p className="text-xs text-gray-500">Master Brain v2.1</p>
              </div>
            </div>
          )}
          <button
            onClick={() => onToggle(!isCollapsed)}
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <ChevronIcon className={`w-5 h-5 transition-transform duration-300 ${isCollapsed ? 'rotate-180' : ''}`} />
          </button>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto" role="navigation" aria-label="Main navigation">
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive: active }) => `
                  flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200
                  ${active
                    ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/10 text-white border border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                  }
                  ${isCollapsed ? 'justify-center' : ''}
                `}
                title={isCollapsed ? item.label : undefined}
                onMouseEnter={() => setHoveredItem(item.path)}
                onMouseLeave={() => setHoveredItem(null)}
                style={{ '--icon-color': isActive ? '#06b6d4' : '#9ca3af' }}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" style={{ color: 'var(--icon-color)' }} aria-hidden="true" />
                {!isCollapsed && (
                  <>
                    <span className="font-medium text-sm">{item.label}</span>
                    {item.badge && (
                      <span className={`ml-auto px-2 py-0.5 text-xs font-bold rounded-full ${
                        item.badge === 'LIVE'
                          ? 'bg-green-500/20 text-green-400 border border-green-500/30 animate-pulse'
                          : item.badge === 'NEW'
                          ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                          : 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                      }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        {!isCollapsed && (
          <div className="p-4 border-t border-gray-800">
            <div className="rounded-xl bg-gradient-to-br from-gray-800/50 to-gray-900/50 p-4 border border-gray-800">
              <div className="flex items-center gap-2 text-gray-400 text-xs mb-3">
                <ServerIcon className="w-4 h-4" />
                <span>Lab Status</span>
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse ml-auto" />
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <LabStatusMini label="Kali" status="online" />
                <LabStatusMini label="Wazuh" status="online" />
                <LabStatusMini label="FortiGate" status="warning" />
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

function LabStatusMini({ label, status }) {
  const colors = {
    online: 'bg-green-400 text-green-400',
    warning: 'bg-yellow-400 text-yellow-400',
    offline: 'bg-red-400 text-red-400',
  };
  return (
    <div className="rounded-lg bg-gray-800/50 p-2">
      <div className={`w-2 h-2 mx-auto rounded-full ${colors[status]} shadow-[0_0_6px_currentColor]`} />
      <p className="text-xs text-gray-400 mt-1 font-medium">{label}</p>
    </div>
  );
}

// Icons
function DashboardIcon({ className, style }) {
  return <svg className={className} style={style} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>;
}
function ShieldAlertIcon({ className, style }) {
  return <svg className={className} style={style} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 3h.01" /></svg>;
}
function BugIcon({ className, style }) {
  return <svg className={className} style={style} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>;
}
function ZapIcon({ className, style }) {
  return <svg className={className} style={style} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>;
}
function ActivityIcon({ className, style }) {
  return <svg className={className} style={style} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>;
}
function ServerIcon({ className, style }) {
  return <svg className={className} style={style} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" /></svg>;
}
function GitBranchIcon({ className, style }) {
  return <svg className={className} style={style} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" /></svg>;
}
function SettingsIcon({ className, style }) {
  return <svg className={className} style={style} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>;
}
function ChevronIcon({ className }) {
  return <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 17l-5-5 5-5" /></svg>;
}