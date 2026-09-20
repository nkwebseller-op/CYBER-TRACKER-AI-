import { Eraser, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ChatToolbar({
  onNewTask,
  onClear,
  hasMessages,
}: {
  onNewTask: () => void;
  onClear: () => void;
  hasMessages: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <Button size="sm" variant="secondary" icon={<Plus size={13} aria-hidden="true" />} onClick={onNewTask}>
        New Task
      </Button>
      <Button
        size="sm"
        variant="ghost"
        icon={<Eraser size={13} aria-hidden="true" />}
        onClick={onClear}
        disabled={!hasMessages}
      >
        Clear Conversation
      </Button>
    </div>
  );
}
