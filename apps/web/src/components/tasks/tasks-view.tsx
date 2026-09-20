"use client";

import { ClipboardList } from "lucide-react";
import { useState } from "react";
import { TaskCards } from "@/components/tasks/task-cards";
import { TaskDetailModal } from "@/components/tasks/task-detail-modal";
import { TaskTable } from "@/components/tasks/task-table";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Panel } from "@/components/ui/panel";
import type { Task } from "@/types/dashboard";

export function TasksView({ tasks }: { tasks: Task[] }) {
  const [selected, setSelected] = useState<Task | null>(null);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tasks"
        description="Planned and running units of work produced by the Task Planner, from objective to report."
      />

      <Panel>
        {tasks.length === 0 ? (
          <EmptyState
            icon={ClipboardList}
            title="No tasks yet"
            description="Tasks appear here once an objective is submitted through the Chat / Command Center."
          />
        ) : (
          <>
            <TaskTable tasks={tasks} onSelect={setSelected} />
            <TaskCards tasks={tasks} onSelect={setSelected} />
          </>
        )}
      </Panel>

      <TaskDetailModal task={selected} isOpen={selected !== null} onClose={() => setSelected(null)} />
    </div>
  );
}
