import { TerminalWindow } from "@/components/terminal/terminal-window";
import { PageHeader } from "@/components/ui/page-header";

export default function TerminalPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Terminal"
        description="Live execution output, once the Execution Controller is wired to real approved actions. Commands typed here are not executed in this phase."
      />
      <TerminalWindow />
    </div>
  );
}
