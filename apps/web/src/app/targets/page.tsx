import { TargetsView } from "@/components/targets/targets-view";
import { MOCK_TARGETS } from "@/lib/mock";

export default function TargetsPage() {
  return <TargetsView targets={MOCK_TARGETS} />;
}
