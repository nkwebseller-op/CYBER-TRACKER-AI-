import { ShieldCheck } from "lucide-react";
import { QuickStartSuggestions } from "@/components/chat/quick-start-suggestions";

export function ChatEmptyState({ onSelectSuggestion }: { onSelectSuggestion: (text: string) => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 px-4 text-center">
      <div className="rounded-full border border-border bg-surface-raised p-3 text-accent">
        <ShieldCheck size={22} aria-hidden="true" />
      </div>
      <div>
        <p className="text-sm font-medium text-foreground">Describe an authorized security objective</p>
        <p className="mt-1 max-w-sm text-xs text-muted">
          Cyber AI will turn it into a structured task plan for your review — nothing is
          researched, approved, or executed until you confirm it.
        </p>
      </div>
      <QuickStartSuggestions onSelect={onSelectSuggestion} />
    </div>
  );
}
