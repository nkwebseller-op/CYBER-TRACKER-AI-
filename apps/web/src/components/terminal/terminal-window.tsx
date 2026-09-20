"use client";

import { Check, Copy, Trash2 } from "lucide-react";
import { useState } from "react";
import { TerminalLines } from "@/components/terminal/terminal-lines";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MOCK_TERMINAL_SESSION, MOCK_TERMINAL_SESSION_LINES } from "@/lib/mock";
import type { TerminalLine } from "@/types/dashboard";

export function TerminalWindow() {
  const [lines, setLines] = useState<TerminalLine[]>(MOCK_TERMINAL_SESSION_LINES);
  const [input, setInput] = useState("");
  const [copied, setCopied] = useState(false);

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
        text: `Command staging is disabled in Phase 2 — "${command}" was not executed.`,
        timestamp: new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      },
    ]);
    setInput("");
  }

  return (
    <div className="glass-raised flex flex-col rounded-lg">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
        <div className="flex items-center gap-3 text-xs">
          <Badge tone="accent">
            <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse-dot" aria-hidden="true" />
            Connected
          </Badge>
          <span className="text-muted">
            Platform: <span className="text-muted-strong">{MOCK_TERMINAL_SESSION.adapter}</span>
          </span>
          <span className="hidden text-muted sm:inline">
            Session: <span className="font-mono text-muted-strong">{MOCK_TERMINAL_SESSION.sessionId}</span>
          </span>
          <span className="hidden text-muted lg:inline">
            Host: <span className="text-muted-strong">{MOCK_TERMINAL_SESSION.host}</span>
          </span>
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
          Terminal command (execution disabled in this phase)
        </label>
        <input
          id="terminal-command"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Command execution is disabled in Phase 2…"
          className="flex-1 bg-transparent font-mono text-sm text-foreground placeholder:text-muted outline-none"
        />
        <Button type="submit" size="sm" variant="secondary">
          Stage
        </Button>
      </form>
    </div>
  );
}
