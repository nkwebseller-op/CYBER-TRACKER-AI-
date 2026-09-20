import type { TerminalLine } from "@/types/dashboard";

export const MOCK_TERMINAL_SESSION = {
  adapter: "linux" as const,
  status: "connected" as const,
  sessionId: "term-sess-8841",
  host: "cyberai-worker-03",
  startedAt: "04:11:58",
};

export const MOCK_TERMINAL_SESSION_LINES: TerminalLine[] = [
  { id: "t1", kind: "system", text: "session: linux · adapter: LocalProcessAdapter", timestamp: "04:11:58" },
  { id: "t2", kind: "system", text: "policy: read-only preview — execution disabled in this phase", timestamp: "04:11:58" },
  { id: "t3", kind: "command", text: "$ curl -sI https://api.staging.internal", timestamp: "04:12:03" },
  { id: "t4", kind: "stdout", text: "HTTP/2 200", timestamp: "04:12:03" },
  { id: "t5", kind: "stdout", text: "server: nginx/1.25.3", timestamp: "04:12:03" },
  { id: "t6", kind: "stdout", text: "content-type: application/json", timestamp: "04:12:03" },
  { id: "t7", kind: "stderr", text: "strict-transport-security header missing", timestamp: "04:12:04" },
  { id: "t8", kind: "command", text: "$ testssl.sh --quiet api.staging.internal", timestamp: "04:12:10" },
  { id: "t9", kind: "system", text: "awaiting approval before this command may run…", timestamp: "04:12:10" },
];
