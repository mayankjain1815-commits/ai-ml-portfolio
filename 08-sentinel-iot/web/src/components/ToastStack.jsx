import { useEffect } from 'react';
import { Check, Info, TriangleAlert, X } from 'lucide-react';

const ICONS = {
  success: Check,
  error: TriangleAlert,
  warning: TriangleAlert,
  neutral: Info,
};

function Toast({ toast, onDismiss }) {
  const Icon = ICONS[toast.tone] ?? Info;

  useEffect(() => {
    const timer = window.setTimeout(() => onDismiss(toast.id), 5200);
    return () => window.clearTimeout(timer);
  }, [toast.id, onDismiss]);

  return (
    <div className={`toast toast--${toast.tone}`} role="status">
      <span className="toast__icon">
        <Icon size={16} />
      </span>
      <div className="toast__body">
        {toast.title ? <strong>{toast.title}</strong> : null}
        <span>{toast.message}</span>
      </div>
      <button className="toast__close" onClick={() => onDismiss(toast.id)} aria-label="Dismiss notification">
        <X size={14} />
      </button>
    </div>
  );
}

export function ToastStack({ toasts, onDismiss }) {
  return (
    <div className="toast-stack" aria-live="polite" aria-atomic="false">
      {toasts.map((toast) => (
        <Toast toast={toast} key={toast.id} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
