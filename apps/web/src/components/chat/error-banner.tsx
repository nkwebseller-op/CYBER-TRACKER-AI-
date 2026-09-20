import { AlertTriangle, X } from "lucide-react";

const FRIENDLY_MESSAGE: Record<string, string> = {
  empty_message: "Type a message before sending.",
  invalid_input: "That message couldn't be processed. Try shortening or rephrasing it.",
  request_failed: "Something went wrong processing your message. Please try again.",
  timeout: "That took longer than expected. Please try again.",
  invalid_task: "Cyber AI couldn't build a valid task plan from that message.",
  unexpected_response: "Received an unexpected response. Please try again.",
};

export function ErrorBanner({
  code,
  message,
  onDismiss,
}: {
  code: string;
  message?: string;
  onDismiss: () => void;
}) {
  const friendly = FRIENDLY_MESSAGE[code] ?? "Something went wrong. Please try again.";

  return (
    <div
      role="alert"
      className="animate-fade-in-up flex items-start gap-2.5 rounded-md border border-danger/30 bg-danger-soft px-3.5 py-2.5 text-sm"
    >
      <AlertTriangle size={16} className="mt-0.5 flex-shrink-0 text-danger" aria-hidden="true" />
      <div className="flex-1">
        <p className="text-danger">{friendly}</p>
        {message && message !== friendly && <p className="mt-0.5 text-xs text-muted">{message}</p>}
      </div>
      <button
        onClick={onDismiss}
        aria-label="Dismiss error"
        className="motion-safe-transition rounded-md p-1 text-muted hover:bg-surface-hover hover:text-foreground"
      >
        <X size={14} />
      </button>
    </div>
  );
}
