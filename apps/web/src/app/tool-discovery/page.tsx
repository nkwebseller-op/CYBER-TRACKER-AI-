import { ToolsView } from "@/components/tools/tools-view";
import { MOCK_TOOLS } from "@/lib/mock";

export default function ToolDiscoveryPage() {
  return <ToolsView tools={MOCK_TOOLS} />;
}
