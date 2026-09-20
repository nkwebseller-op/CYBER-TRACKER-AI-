import { Card } from "@/components/ui/card";

export default function TerminalPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Terminal</h1>
        <p className="text-sm text-muted">
          Live execution output, streamed over the WebSocket gateway once the Execution
          Controller is wired to real approved actions.
        </p>
      </div>
      <Card className="scanline">
        <pre className="font-mono text-xs text-accent/80">
          $ waiting for an approved execution…
        </pre>
      </Card>
    </div>
  );
}
