import { useEffect } from "react";

export interface ToastData {
  id: number;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}

interface ToastProps {
  toast: ToastData;
  onDismiss: () => void;
}

const AUTO_DISMISS_MS = 6000;

export function Toast({ toast, onDismiss }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  return (
    <div className="toast" role="status">
      <span className="toast-message">{toast.message}</span>
      {toast.actionLabel && toast.onAction && (
        <button
          type="button"
          className="toast-action"
          onClick={() => {
            toast.onAction?.();
            onDismiss();
          }}
        >
          {toast.actionLabel}
        </button>
      )}
      <button type="button" className="toast-close" onClick={onDismiss} aria-label="Dismiss">
        &times;
      </button>
    </div>
  );
}
