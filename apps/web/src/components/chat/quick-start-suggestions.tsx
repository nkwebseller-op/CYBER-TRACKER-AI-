const SUGGESTIONS = [
  "Review my authorized web application.",
  "Analyze my authorized API.",
  "Check my Android environment.",
  "Review an authorized server configuration.",
];

/**
 * Filling the composer, never sending. Selecting a suggestion must not
 * trigger any request or execution on its own.
 */
export function QuickStartSuggestions({ onSelect }: { onSelect: (text: string) => void }) {
  return (
    <div className="flex flex-wrap justify-center gap-2">
      {SUGGESTIONS.map((suggestion) => (
        <button
          key={suggestion}
          type="button"
          onClick={() => onSelect(suggestion)}
          className="motion-safe-transition rounded-full border border-border-strong bg-surface-raised px-3 py-1.5 text-xs text-muted-strong hover:border-accent-soft hover:text-foreground"
        >
          {suggestion}
        </button>
      ))}
    </div>
  );
}
