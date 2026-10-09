import { useState, useEffect, useCallback } from "react";
import { api } from "../api";
import { showToast } from "./Toast";
import {
  Monitor,
  Terminal,
  Shield,
  Server,
  Wifi,
  WifiOff,
  Activity,
  Skull,
  Loader2,
} from "lucide-react";

const VM_META = {
  wazuh: { label: "Wazuh SIEM", icon: Shield, ip: "192.168.56.30" },
  fortigate: { label: "FortiGate FW", icon: Server, ip: "192.168.56.1" },
  kali: { label: "Kali Attacker", icon: Skull, ip: "192.168.56.10" },
  target: { label: "Ubuntu Target", icon: Terminal, ip: "192.168.56.20" },
};

export default function ControlMatrix() {
  const [labStatus, setLabStatus] = useState(null);
  const [attacking, setAttacking] = useState(false);
  const [attackResult, setAttackResult] = useState(null);

  const fetchLabStatus = useCallback(async () => {
    try {
      const { data } = await api.get("/api/lab/status");
      setLabStatus(data);
    } catch {
      // lab unreachable — keep last known state
    }
  }, []);

  useEffect(() => {
    fetchLabStatus();
    const interval = setInterval(fetchLabStatus, 15000);
    return () => clearInterval(interval);
  }, [fetchLabStatus]);

  const handleLaunchAttack = async (attackType) => {
    setAttacking(true);
    setAttackResult(null);
    try {
      const { data } = await api.post("/api/lab/launch-attack", { attack_type: attackType });
      setAttackResult(data);
      if (data.exit_code === 0) {
        showToast(`Attack completed — ${attackType}`, "success");
      } else {
        showToast(`Attack failed — ${data.stderr?.slice(0, 80) || "unknown error"}`, "error");
      }
    } catch (err) {
      showToast(`Attack error: ${err.message}`, "error");
    } finally {
      setAttacking(false);
    }
  };

  const vms = labStatus?.vms || {};
  const summary = labStatus?.summary || { total: 4, online: 0 };

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4">
        <Activity size={18} className="text-cyan-400" />
        <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-300">
          Lab Control Matrix
        </h3>
        <span className="text-[10px] text-gray-500 ml-auto">
          {summary.online}/{summary.total} online
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-4">
        {Object.entries(VM_META).map(([key, meta]) => {
          const vm = vms[key] || {};
          const isOnline = vm.status === "online";
          const Icon = meta.icon;
          return (
            <div
              key={key}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 border text-xs ${
                isOnline
                  ? "bg-emerald-500/5 border-emerald-500/20"
                  : "bg-slate-900/50 border-slate-700/30"
              }`}
            >
              <div
                className={`p-1.5 rounded ${
                  isOnline ? "bg-emerald-500/10 text-emerald-400" : "bg-slate-800 text-gray-500"
                }`}
              >
                <Icon size={16} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-gray-200 font-medium truncate">{meta.label}</div>
                <div className="text-[10px] text-gray-500 font-mono">{meta.ip}</div>
              </div>
              {isOnline ? (
                <Wifi size={14} className="text-emerald-400 shrink-0" />
              ) : (
                <WifiOff size={14} className="text-rose-400 shrink-0" />
              )}
            </div>
          );
        })}
      </div>

      <div className="space-y-2">
        <button
          onClick={() => handleLaunchAttack("ssh_brute_force")}
          disabled={attacking}
          className="w-full bg-rose-700 hover:bg-rose-600 disabled:bg-slate-700 disabled:text-slate-500
                     text-white text-sm font-bold px-4 py-3 rounded-lg flex items-center justify-center gap-2
                     transition-colors uppercase tracking-wider"
        >
          {attacking ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              Launching Attack...
            </>
          ) : (
            <>
              <Skull size={18} />
              Launch Simulation (SSH Brute Force)
            </>
          )}
        </button>

        <div className="flex gap-2">
          <button
            onClick={() => handleLaunchAttack("port_scan")}
            disabled={attacking}
            className="flex-1 bg-slate-700 hover:bg-slate-600 disabled:opacity-50
                       text-gray-200 text-xs font-medium px-3 py-2 rounded-lg transition-colors"
          >
            Port Scan
          </button>
          <button
            onClick={() => handleLaunchAttack("web_scan")}
            disabled={attacking}
            className="flex-1 bg-slate-700 hover:bg-slate-600 disabled:opacity-50
                       text-gray-200 text-xs font-medium px-3 py-2 rounded-lg transition-colors"
          >
            Web Scan
          </button>
        </div>
      </div>

      {attackResult && (
        <div className="mt-3 bg-slate-900/80 border border-slate-700 rounded-lg p-2 max-h-28 overflow-y-auto">
          <div className="text-[10px] text-gray-500 font-mono mb-1">
            exit code: {attackResult.exit_code} — {attackResult.attack_type}
          </div>
          <pre className="text-[11px] text-emerald-300 font-mono whitespace-pre-wrap break-all">
            {(attackResult.stdout || attackResult.stderr || "No output").slice(0, 600)}
          </pre>
        </div>
      )}
    </div>
  );
}
