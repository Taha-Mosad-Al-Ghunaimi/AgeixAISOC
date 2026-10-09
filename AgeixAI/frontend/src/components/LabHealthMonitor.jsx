import { useEffect, useState } from 'react';
import { Server, Database, Shield, Wifi, AlertTriangle, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { labApi } from '../api';

const LAB_NODES = [
  { id: 'kali', name: 'Kali Linux', icon: Server, description: 'Attack Platform', endpoint: 'kali' },
  { id: 'wazuh', name: 'Wazuh SIEM', icon: Database, description: 'Log Collection & Detection', endpoint: 'wazuh' },
  { id: 'fortigate', name: 'FortiGate', icon: Shield, description: 'SOAR Enforcement', endpoint: 'fortigate' },
];

export function LabHealthMonitor({ onLaunchAttack }) {
  const [status, setStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [attacking, setAttacking] = useState(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await labApi.getStatus();
        setStatus(res.data);
        setLastUpdate(new Date());
      } catch (error) {
        console.error('[LabHealthMonitor] Failed to fetch status:', error);
        setStatus({});
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleLaunchAttack = async (nodeId) => {
    setAttacking(nodeId);
    try {
      await labApi.launchAttack('atomic_red', nodeId);
    } catch (error) {
      console.error('[LabHealthMonitor] Attack launch failed:', error);
    } finally {
      setTimeout(() => setAttacking(null), 2000);
    }
  };

  const getNodeStatus = (nodeId) => {
    const nodeStatus = status[nodeId];
    if (!nodeStatus) return 'unknown';
    return nodeStatus.reachable ? 'online' : 'offline';
  };

  const getNodeDetails = (nodeId) => {
    const nodeStatus = status[nodeId];
    if (!nodeStatus) return { latency: 'N/A', ip: 'N/A', services: [] };
    return {
      latency: nodeStatus.latency_ms ? `${nodeStatus.latency_ms}ms` : 'N/A',
      ip: nodeStatus.ip || 'N/A',
      services: nodeStatus.services || [],
    };
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {LAB_NODES.map((node) => {
        const nodeStatus = getNodeStatus(node.id);
        const details = getNodeDetails(node.id);
        const Icon = node.icon;
        const isAttacking = attacking === node.id;

        return (
          <div
            key={node.id}
            className={`relative rounded-2xl p-5 bg-gradient-to-br from-gray-900 to-gray-800 border transition-all duration-300 ${
              nodeStatus === 'online'
                ? 'border-cyan-500/30 shadow-[0_0_20px_rgba(6,182,212,0.1)]'
                : nodeStatus === 'warning'
                ? 'border-yellow-500/30 shadow-[0_0_20px_rgba(234,179,8,0.1)]'
                : 'border-red-500/30 shadow-[0_0_20px_rgba(239,68,68,0.1)]'
            }`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div
                  className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                    nodeStatus === 'online'
                      ? 'bg-cyan-500/20 text-cyan-400'
                      : nodeStatus === 'warning'
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : 'bg-red-500/20 text-red-400'
                  }`}
                >
                  <Icon className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-white font-semibold text-lg">{node.name}</h3>
                  <p className="text-xs text-gray-500">{node.description}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div
                  className={`w-3 h-3 rounded-full transition-all duration-500 ${
                    nodeStatus === 'online'
                      ? 'bg-green-400 shadow-[0_0_10px_theme(colors.green.400)] animate-pulse'
                      : nodeStatus === 'warning'
                      ? 'bg-yellow-400 shadow-[0_0_10px_theme(colors.yellow.400)] animate-pulse'
                      : 'bg-red-400'
                  }`}
                />
              </div>
            </div>

            <div className="space-y-3 mb-4">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">IP Address</span>
                <span className="text-gray-300 font-mono">{details.ip}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Latency</span>
                <span className={`font-mono ${nodeStatus === 'online' ? 'text-green-400' : 'text-red-400'}`}>
                  {details.latency}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Status</span>
                <span className={`font-medium ${
                  nodeStatus === 'online' ? 'text-green-400' :
                  nodeStatus === 'warning' ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {nodeStatus.toUpperCase()}
                </span>
              </div>
            </div>

            {details.services.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-4">
                {details.services.slice(0, 5).map((svc) => (
                  <span
                    key={svc}
                    className="px-2 py-0.5 text-xs rounded bg-gray-800/50 text-gray-300 border border-gray-700"
                  >
                    {svc}
                  </span>
                ))}
                {details.services.length > 5 && (
                  <span className="px-2 py-0.5 text-xs rounded bg-gray-800/50 text-gray-500 border border-gray-700">
                    +{details.services.length - 5}
                  </span>
                )}
              </div>
            )}

            <button
              onClick={() => handleLaunchAttack(node.id)}
              disabled={loading || isAttacking || nodeStatus !== 'online'}
              className={`w-full py-2.5 rounded-xl font-medium text-sm transition-all duration-200 flex items-center justify-center gap-2 ${
                isAttacking
                  ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 cursor-wait'
                  : nodeStatus === 'online'
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 hover:bg-cyan-500/20 hover:border-cyan-500/40'
                  : 'bg-gray-800 text-gray-500 border border-gray-700 cursor-not-allowed'
              }`}
            >
              {isAttacking ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Deploying Atomic Test...
                </>
              ) : (
                <>
                  <Wifi className="w-4 h-4" />
                  Launch Attack
                </>
              )}
            </button>

            {isAttacking && (
              <div className="absolute inset-0 bg-black/50 rounded-2xl flex items-center justify-center z-10">
                <div className="text-center">
                  <Loader2 className="w-10 h-10 animate-spin text-cyan-400 mx-auto mb-2" />
                  <p className="text-cyan-400 font-medium">Executing on {node.name}...</p>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}