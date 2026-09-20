import { Eye, Pencil } from "lucide-react";
import { AuthorizationBadge, TargetStatusBadge } from "@/components/targets/target-badges";
import { TARGET_TYPE_ICON, TARGET_TYPE_LABEL } from "@/components/targets/target-icon";
import { Button } from "@/components/ui/button";
import { formatRelativeDate, titleCase } from "@/lib/format";
import type { Target } from "@/types/dashboard";

export function TargetCards({
  targets,
  onView,
  onEdit,
}: {
  targets: Target[];
  onView: (target: Target) => void;
  onEdit: (target: Target) => void;
}) {
  return (
    <div className="space-y-3 md:hidden">
      {targets.map((target) => {
        const Icon = TARGET_TYPE_ICON[target.type];
        return (
          <div key={target.id} className="rounded-md border border-border bg-surface-raised/50 p-4">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2.5">
                <Icon size={16} className="text-muted" aria-hidden="true" />
                <div>
                  <p className="font-medium text-foreground">{target.name}</p>
                  <p className="text-xs text-muted">{TARGET_TYPE_LABEL[target.type]}</p>
                </div>
              </div>
              <TargetStatusBadge status={target.status} />
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div>
                <dt className="text-muted">Environment</dt>
                <dd className="text-muted-strong">{titleCase(target.environment)}</dd>
              </div>
              <div>
                <dt className="text-muted">Last Assessment</dt>
                <dd className="text-muted-strong">{formatRelativeDate(target.lastAssessment)}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-muted">Authorization</dt>
                <dd className="mt-1">
                  <AuthorizationBadge status={target.authorizationStatus} />
                </dd>
              </div>
            </dl>
            <div className="mt-3 flex gap-2">
              <Button size="sm" variant="secondary" icon={<Eye size={13} />} onClick={() => onView(target)}>
                View
              </Button>
              <Button size="sm" variant="ghost" icon={<Pencil size={13} />} onClick={() => onEdit(target)}>
                Edit
              </Button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
