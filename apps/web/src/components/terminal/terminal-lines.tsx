import type { TerminalLine, TerminalLineKind } from "@/types/dashboard";

const KIND_STYLES: Record<TerminalLineKind, string> = {
  command: "text-accent",
  stdout: "text-foreground/90",
  stderr: "text-danger",
  system: "text-muted",
};

const KIND_PREFIX: Record<TerminalLineKind, string> = {
  command: "",
  stdout: "",
  stderr: "",
  system: "# ",
};

export function TerminalLines({ lines }: { lines: TerminalLine[] }) {
  return (
    <div className="scrollbar-thin scanline max-h-72 space-y-1 overflow-y-auto rounded-md border border-border bg-black/40 p-4 font-mono text-xs">
      {lines.map((line) => (
        <p key={line.id} className={KIND_STYLES[line.kind]}>
          <span className="mr-2 text-muted/60">{line.timestamp}</span>
          {KIND_PREFIX[line.kind]}
          {line.text}
        </p>
      ))}
    </div>
  );
}
