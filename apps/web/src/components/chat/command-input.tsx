"use client";

import { Paperclip, Send, Square } from "lucide-react";
import { type FormEvent } from "react";
import { Button } from "@/components/ui/button";

const MAX_LENGTH = 4000;
const WARN_THRESHOLD = 400;

export function CommandInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  isRunning = false,
  onStop,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  disabled?: boolean;
  isRunning?: boolean;
  onStop?: () => void;
}) {
  const remaining = MAX_LENGTH - value.length;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} className="glass-raised rounded-lg p-3">
      <label htmlFor="command-center-input" className="sr-only">
        Describe the authorized security task you want Cyber AI to perform
      </label>
      <textarea
        id="command-center-input"
        value={value}
        onChange={(event) => onChange(event.target.value.slice(0, MAX_LENGTH))}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            handleSubmit(event);
          }
        }}
        disabled={disabled}
        rows={2}
        maxLength={MAX_LENGTH}
        placeholder="Describe the authorized security task you want Cyber AI to perform…"
        className="w-full resize-none bg-transparent text-sm text-foreground placeholder:text-muted outline-none disabled:cursor-not-allowed disabled:opacity-60"
      />
      <div className="mt-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <button
            type="button"
            disabled
            aria-disabled="true"
            title="Attachments — coming in a later phase"
            className="motion-safe-transition flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs text-muted disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Paperclip size={14} aria-hidden="true" />
            Attach evidence
          </button>
          {remaining <= WARN_THRESHOLD && (
            <span className={`text-xs ${remaining < 100 ? "text-warning" : "text-muted"}`}>
              {remaining} characters left
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isRunning && (
            <Button
              type="button"
              variant="danger"
              size="sm"
              icon={<Square size={13} aria-hidden="true" />}
              onClick={onStop}
            >
              Stop
            </Button>
          )}
          <Button
            type="submit"
            variant="primary"
            size="sm"
            disabled={disabled || value.trim().length === 0}
            icon={<Send size={13} aria-hidden="true" />}
          >
            Send
          </Button>
        </div>
      </div>
    </form>
  );
}
