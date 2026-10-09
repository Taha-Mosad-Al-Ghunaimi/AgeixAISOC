import { Shield, AlertTriangle, Ban, Activity } from "lucide-react";

export default function TopMetrics({ metrics }) {
  if (!metrics) return null;

  const cards = [
    {
      label: "Active Alerts",
      value: metrics.active_alerts ?? 0,
      icon: AlertTriangle,
      color: "text-rose-400",
      bg: "bg-rose-500/10",
      border: "border-rose-500/20",
    },
    {
      label: "Pending Decisions",
      value: metrics.pending_decisions ?? 0,
      icon: Shield,
      color: "text-amber-400",
      bg: "bg-amber-500/10",
      border: "border-amber-500/20",
    },
    {
      label: "Threats Blocked",
      value: metrics.threats_blocked ?? 0,
      icon: Ban,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20",
    },
    {
      label: "Logs Processed",
      value: metrics.total_logs_processed ?? 0,
      icon: Activity,
      color: "text-cyan-400",
      bg: "bg-cyan-500/10",
      border: "border-cyan-500/20",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`${card.bg} ${card.border} border rounded-xl p-4 flex items-center gap-4`}
        >
          <div className={`${card.color} ${card.bg} p-3 rounded-lg`}>
            <card.icon size={24} />
          </div>
          <div>
            <div className={`text-2xl font-bold ${card.color}`}>{card.value}</div>
            <div className="text-xs text-gray-400 uppercase tracking-wider">{card.label}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
