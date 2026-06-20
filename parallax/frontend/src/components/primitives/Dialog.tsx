import { useEffect } from "react";
import { AlertTriangle, X } from "lucide-react";

/**
 * Lightweight modal dialog. Closes on backdrop click or Escape, traps nothing
 * fancy — just enough for confirmations and error popups. Renders nothing when
 * `open` is false.
 */
export function Dialog({
  open,
  onClose,
  title,
  children,
  tone = "default",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  tone?: "default" | "danger";
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm animate-[fadeIn_0.15s_ease-out]"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md bg-bone border border-ink shadow-[8px_8px_0_0_rgba(10,10,10,1)]"
      >
        <div className="flex items-center justify-between gap-3 px-5 h-12 border-b border-ink">
          <div className="flex items-center gap-2">
            {tone === "danger" && <AlertTriangle className="w-4 h-4 text-oxblood" strokeWidth={2} />}
            <span className="font-display text-lg leading-none">{title}</span>
          </div>
          <button onClick={onClose} className="text-ink/50 hover:text-ink" aria-label="Close">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

/** Convenience error popup with a single dismiss action. */
export function ErrorDialog({
  message,
  onClose,
  title = "Invalid file",
}: {
  message: string | null;
  onClose: () => void;
  title?: string;
}) {
  return (
    <Dialog open={!!message} onClose={onClose} title={title} tone="danger">
      <p className="text-sm text-ink/80 leading-relaxed">{message}</p>
      <div className="mt-5 flex justify-end">
        <button onClick={onClose} className="btn-primary h-10 px-5">
          Got it
        </button>
      </div>
    </Dialog>
  );
}
