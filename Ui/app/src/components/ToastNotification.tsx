import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle2, Info, AlertTriangle } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';

const icons = {
  success: CheckCircle2,
  info: Info,
  warning: AlertTriangle,
};

const borderColors = {
  success: 'border-l-[3px] border-l-green-500',
  info: 'border-l-[3px] border-l-blue-500',
  warning: 'border-l-[3px] border-l-amber-500',
};

const iconColors = {
  success: 'text-green-500',
  info: 'text-blue-500',
  warning: 'text-amber-500',
};

export function ToastContainer() {
  const toasts = useAppStore((s) => s.toasts);
  const dismissToast = useAppStore((s) => s.dismissToast);

  return (
    <div className="fixed top-5 right-5 z-[200] flex flex-col gap-2">
      <AnimatePresence>
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={() => dismissToast(toast.id)} />
        ))}
      </AnimatePresence>
    </div>
  );
}

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: { id: string; message: string; type: 'success' | 'info' | 'warning'; action?: { label: string; onClick: () => void } };
  onDismiss: () => void;
}) {
  const Icon = icons[toast.type];

  useEffect(() => {
    const timer = setTimeout(onDismiss, 4000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <motion.div
      initial={{ x: 100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 100, opacity: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      className={`bg-nerve-bg border border-[rgba(0,49,31,0.08)] rounded-xl shadow-lg p-4 max-w-[360px] flex items-start gap-3 ${borderColors[toast.type]}`}
    >
      <Icon className={`w-[18px] h-[18px] mt-0.5 shrink-0 ${iconColors[toast.type]}`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-nerve-dark">{toast.message}</p>
        {toast.action && (
          <button
            onClick={toast.action.onClick}
            className="text-xs text-nerve-blue mt-1 hover:underline"
          >
            {toast.action.label}
          </button>
        )}
      </div>
      <button onClick={onDismiss} className="text-nerve-muted hover:text-nerve-dark transition-colors">
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  );
}
