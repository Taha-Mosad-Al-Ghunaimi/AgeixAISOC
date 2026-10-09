import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

// ── Context ───────────────────────────────────────────────────────────────────

const ToastContext = createContext(null);

// ── Toast Item ────────────────────────────────────────────────────────────────

const ICONS = {
  success: <CheckCircle className="w-4 h-4 text-green-400" />,
  error:   <XCircle    className="w-4 h-4 text-red-400"   />,
  warning: <AlertTriangle className="w-4 h-4 text-yellow-400" />,
  info:    <Info       className="w-4 h-4 text-cyan-400"  />,
};

const BORDERS = {
  success: 'border-green-500/30',
  error:   'border-red-500/30',
  warning: 'border-yellow-500/30',
  info:    'border-cyan-500/30',
};

const GLOWS = {
  success: '0 0 20px rgba(0,255,136,.15)',
  error:   '0 0 20px rgba(255,68,102,.15)',
  warning: '0 0 20px rgba(255,215,0,.15)',
  info:    '0 0 20px rgba(0,229,255,.15)',
};

function ToastItem({ toast, onRemove }) {
  const [exiting, setExiting] = React.useState(false);

  const dismiss = () => {
    setExiting(true);
    setTimeout(() => onRemove(toast.id), 300);
  };

  React.useEffect(() => {
    const t = setTimeout(dismiss, toast.duration ?? 4000);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className={`
        flex items-start gap-3 p-4 rounded-xl border backdrop-blur-xl
        ${BORDERS[toast.type] ?? BORDERS.info}
        ${exiting ? 'toast-out' : 'toast-slide'}
      `}
      style={{
        background: 'rgba(6,13,26,.97)',
        boxShadow: GLOWS[toast.type] ?? GLOWS.info,
        minWidth: 280,
        maxWidth: 380,
      }}
    >
      <div className="flex-shrink-0 mt-0.5">{ICONS[toast.type] ?? ICONS.info}</div>
      <div className="flex-1 min-w-0">
        {toast.title && (
          <p className="text-sm font-semibold text-slate-200 mb-0.5">{toast.title}</p>
        )}
        <p className="text-xs text-slate-400 leading-relaxed">{toast.message}</p>
      </div>
      <button
        onClick={dismiss}
        className="flex-shrink-0 text-slate-600 hover:text-slate-300 transition-colors mt-0.5"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

// ── Provider ──────────────────────────────────────────────────────────────────

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const counter = useRef(0);

  const addToast = useCallback((toast) => {
    const id = `toast-${++counter.current}`;
    setToasts((prev) => [...prev, { id, ...toast }]);
    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}

      {/* Toast container — fixed bottom-right */}
      <div
        className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 pointer-events-none"
        style={{ pointerEvents: 'none' }}
      >
        {toasts.map((t) => (
          <div key={t.id} style={{ pointerEvents: 'all' }}>
            <ToastItem toast={t} onRemove={removeToast} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within <ToastProvider>');

  return {
    toast: ctx.addToast,
    success: (message, title) => ctx.addToast({ type: 'success', message, title }),
    error:   (message, title) => ctx.addToast({ type: 'error',   message, title }),
    warning: (message, title) => ctx.addToast({ type: 'warning', message, title }),
    info:    (message, title) => ctx.addToast({ type: 'info',    message, title }),
  };
}
