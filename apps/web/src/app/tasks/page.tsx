import { TasksView } from "@/components/tasks/tasks-view";
import { MOCK_TASKS } from "@/lib/mock";

export default function TasksPage() {
  return <TasksView tasks={MOCK_TASKS} />;
}
