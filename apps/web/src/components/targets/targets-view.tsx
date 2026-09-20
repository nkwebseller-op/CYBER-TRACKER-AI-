"use client";

import { Plus, Target as TargetIcon } from "lucide-react";
import { useState } from "react";
import { TargetCards } from "@/components/targets/target-cards";
import { TargetDetailModal } from "@/components/targets/target-detail-modal";
import { TargetFormModal } from "@/components/targets/target-form-modal";
import { TargetTable } from "@/components/targets/target-table";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Panel } from "@/components/ui/panel";
import type { Target } from "@/types/dashboard";

export function TargetsView({ targets }: { targets: Target[] }) {
  const [viewing, setViewing] = useState<Target | null>(null);
  const [editing, setEditing] = useState<Target | null>(null);
  const [isAddOpen, setAddOpen] = useState(false);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Targets"
        description="Authorized scope entries. Nothing may be executed against a target without an active, non-expired authorization record — enforced by the Policy Engine, not this UI."
        actions={
          <Button variant="primary" icon={<Plus size={14} />} onClick={() => setAddOpen(true)}>
            Add Target
          </Button>
        }
      />

      <Panel>
        {targets.length === 0 ? (
          <EmptyState
            icon={TargetIcon}
            title="No authorized targets yet"
            description="Add a target with signed authorization evidence to begin planning assessments against it."
          />
        ) : (
          <>
            <TargetTable targets={targets} onView={setViewing} onEdit={setEditing} />
            <TargetCards targets={targets} onView={setViewing} onEdit={setEditing} />
          </>
        )}
      </Panel>

      <TargetDetailModal target={viewing} isOpen={viewing !== null} onClose={() => setViewing(null)} />
      <TargetFormModal target={editing} isOpen={editing !== null} onClose={() => setEditing(null)} />
      <TargetFormModal target={null} isOpen={isAddOpen} onClose={() => setAddOpen(false)} />
    </div>
  );
}
