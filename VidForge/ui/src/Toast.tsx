import { useEffect, useState } from 'react';
import { CircleAlert, CheckCircle2, Info, X } from 'lucide-react';

type ToastKind = "error" | "success" | "info";

interface ToastItem {
  id: number;
  kind: ToastKind;
  title: string;
  message: string;
}

const DURATION_MS: Record<ToastKind, number> = { error: 7000, success: 4000, info: 5000 };

// Module-level store so any handler can raise a toast without prop drilling
let nextId = 1;
let items: ToastItem[] = [];
const listeners = new Set<(items: ToastItem[]) => void>();

function emit() {
  listeners.forEach(fn => fn(items));
}

function dismiss(id: number) {
  items = items.filter(t => t.id !== id);
  emit();
}

function push(kind: ToastKind, title: string, message = "") {
  // The same message raised twice in a row (e.g. repeated clicks) shows once
  if (items.some(t => t.kind === kind && t.title === title && t.message === message)) return;
  const id = nextId++;
  items = [...items, { id, kind, title, message }].slice(-4);
  emit();
  setTimeout(() => dismiss(id), DURATION_MS[kind]);
}

export const toast = {
  error: (title: string, message?: string) => push("error", title, message),
  success: (title: string, message?: string) => push("success", title, message),
  info: (title: string, message?: string) => push("info", title, message),
};

const ICONS = { error: CircleAlert, success: CheckCircle2, info: Info };

export function Toaster() {
  const [list, setList] = useState<ToastItem[]>(items);

  useEffect(() => {
    listeners.add(setList);
    return () => { listeners.delete(setList); };
  }, []);

  return (
    <div className="toast-stack" aria-live="polite">
      {list.map(t => {
        const Icon = ICONS[t.kind];
        return (
          <div key={t.id} className={`toast toast-${t.kind}`} role={t.kind === "error" ? "alert" : "status"}>
            <Icon size={18} className="toast-icon" />
            <div className="toast-body">
              <strong>{t.title}</strong>
              {t.message && <span>{t.message}</span>}
            </div>
            <button type="button" className="toast-close" onClick={() => dismiss(t.id)} aria-label="Dismiss notification">
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
