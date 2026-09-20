import type { ChatUIMessage } from "@/types/dashboard";

export const MOCK_CHAT_HISTORY: ChatUIMessage[] = [
  {
    id: "msg-1",
    role: "user",
    content: "Analyze my authorized web application for common security issues.",
    timestamp: "04:10",
    status: "sent",
  },
  {
    id: "msg-2",
    role: "assistant",
    content:
      "Understood. Which authorized target should this apply to — api.staging.internal, or the Corporate Marketing Site?",
    timestamp: "04:10",
    status: "sent",
  },
  {
    id: "msg-3",
    role: "user",
    content: "api.staging.internal",
    timestamp: "04:11",
    status: "sent",
  },
  {
    id: "msg-4",
    role: "system",
    content: "Scope validated: api.staging.internal is authorized and active until 2026-12-01.",
    timestamp: "04:11",
    status: "sent",
  },
  {
    id: "msg-5",
    role: "assistant",
    content:
      "I'll research suitable low-risk reconnaissance techniques first (header analysis, TLS baseline) before proposing anything that needs your approval.",
    timestamp: "04:11",
    status: "sent",
  },
  {
    id: "msg-6",
    role: "system",
    content: "1 action is awaiting your approval in Tasks → task-1042.",
    timestamp: "04:12",
    status: "sent",
  },
];
