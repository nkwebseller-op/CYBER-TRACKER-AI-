import { AuthorizationBadge, TargetStatusBadge } from "@/components/targets/target-badges";
import { TARGET_TYPE_LABEL } from "@/components/targets/target-icon";
import { Modal } from "@/components/ui/modal";
import { formatRelativeDate, titleCase } from "@/lib/format";
import type { Target } from "@/types/dashboard";

export function TargetDetailModal({
  target,
  isOpen,
  onClose,
}: {
  target: Target | null;
  isOpen: boolean;
  onClose: () => void;
}) {
  if (!target) return null;

  return (
    <Modal title={target.name} isOpen={isOpen} onClose={onClose}>
      <dl className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <dt className="text-xs text-muted">Type</dt>
          <dd className="mt-0.5 text-foreground">{TARGET_TYPE_LABEL[target.type]}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Environment</dt>
          <dd className="mt-0.5 text-foreground">{titleCase(target.environment)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Authorization</dt>
          <dd className="mt-0.5">
            <AuthorizationBadge status={target.authorizationStatus} />
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Status</dt>
          <dd className="mt-0.5">
            <TargetStatusBadge status={target.status} />
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Owner</dt>
          <dd className="mt-0.5 text-foreground">{target.owner}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Last Assessment</dt>
          <dd className="mt-0.5 text-foreground">{formatRelativeDate(target.lastAssessment)}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-xs text-muted">Scope</dt>
          <dd className="mt-0.5 break-all font-mono text-xs text-foreground">
            {target.scopeValue}
          </dd>
        </div>
      </dl>
    </Modal>
  );
}
