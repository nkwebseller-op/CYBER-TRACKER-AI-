import { Card } from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Settings</h1>
        <p className="text-sm text-muted">
          AI provider and policy configuration. API keys are configured server-side via
          environment variables and are never exposed to this page.
        </p>
      </div>
      <Card title="AI Provider" subtitle="Configured server-side">
        <p className="text-sm text-foreground">Gemini (primary)</p>
        <p className="mt-1 text-xs text-muted">
          Set <code className="text-accent">GEMINI_API_KEY</code> in the API&apos;s environment.
        </p>
      </Card>
    </div>
  );
}
