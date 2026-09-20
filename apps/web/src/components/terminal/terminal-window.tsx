"use client";

import { Check, Copy, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { TerminalLines } from "@/components/terminal/terminal-lines";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { createTerminalSession, type TerminalSessionInfo } from "@/lib/terminal-api";
import { MOCK_TERMINAL_SESSION_LINES } from "@/lib/mock";
import type { TerminalLine } from "@/types/dashboard";

function nowLabel(): string {
  return new Date().toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Real session lifecycle, backed by the Terminal Engine
 * (services/terminal/engine.py) via POST /api/terminal/sessions — this is
 * not mock session info. Command output stays mock/sample content and the
 * input stays non-executing: there is no action-type picker in this UI
 * yet, and this component never sends raw command text to the backend —
 * the execute API only accepts a reviewed `actionType`, never argv.
 */
export function TerminalWindow() {
  const [lines, setLines] = useState<TerminalLine[]>(MOCK_TERMINAL_SESSION_LINES);
  const [input, setInput] = useState("");
  const [copied, setCopied] = useState(false);
  const [session, setSession] = useState<TerminalSessionInfo | null>(null);
  const [connectionError, setConnectionError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    createTerminalSession()
      .then((created) => {
        if (!cancelled) setSession(created);
      })
      .catch(() => {
        if (!cancelled) setConnectionError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleCopy() {
    const text = lines.map((line) => line.text).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard access can be denied by the browser; failing silently is
      // acceptable here since this only copies preview text, not an action.
    }
  }

  function handleClear() {
    setLines([]);
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const command = input.trim();
    if (!command) return;
    setLines((prev) => [
      ...prev,
      {
        id: `local-${prev.length}`,
        kind: "system",
        text: `Command execution is not exposed in this UI — the backend only accepts reviewed action types, never raw text like "${command}".`,
        timestamp: nowLabel(),
      },
    ]);
    setInput("");
  }

  const isConnected = session !== null && !connectionError;

  return (
    <div className="glass-raised flex flex-col rounded-lg">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
        <div className="flex items-center gap-3 text-xs">
          <Badge tone={isConnected ? "accent" : connectionError ? "danger" : "neutral"}>
            <span
              className={`h-1.5 w-1.5 rounded-full bg-current ${isConnected ? "animate-pulse-dot" : ""}`}
              aria-hidden="true"
            />
            {isConnected ? "Connected" : connectionError ? "Unavailable" : "Connecting…"}
          </Badge>
          {session && (
            <>
              <span className="text-muted">
                Platform: <span className="text-muted-strong">{session.platform}</span>
              </span>
              <span className="hidden text-muted sm:inline">
                Session: <span className="font-mono text-muted-strong">{session.id}</span>
              </span>
              <span className="hidden text-muted lg:inline">
                Status: <span className="text-muted-strong">{session.status}</span>
              </span>
            </>
          )}
          {connectionError && (
            <span className="text-danger">Could not reach the Terminal Engine API.</span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="ghost"
            icon={copied ? <Check size={13} /> : <Copy size={13} />}
            onClick={handleCopy}
          >
            {copied ? "Copied" : "Copy"}
          </Button>
          <Button size="sm" variant="ghost" icon={<Trash2 size={13} />} onClick={handleClear}>
            Clear
          </Button>
        </div>
      </div>

      <div className="p-4">
        <TerminalLines lines={lines} />
      </div>

      <form onSubmit={handleSubmit} className="flex items-center gap-2 border-t border-border px-4 py-3">
        <span className="font-mono text-sm text-accent" aria-hidden="true">
          $
        </span>
        <label htmlFor="terminal-command" className="sr-only">
          Terminal command (execution is not exposed in this UI)
        </label>
        <input
          id="terminal-command"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Direct command execution is not exposed here…"
          className="flex-1 bg-transparent font-mono text-sm text-foreground placeholder:text-muted outline-none"
        />
        <Button type="submit" size="sm" variant="secondary">
          Stage
        </Button>
      </form>
    </div>
  );
}
