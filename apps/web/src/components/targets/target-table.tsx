import { Eye, Pencil } from "lucide-react";
import { AuthorizationBadge, TargetStatusBadge } from "@/components/targets/target-badges";
import { TARGET_TYPE_ICON, TARGET_TYPE_LABEL } from "@/components/targets/target-icon";
import { formatRelativeDate, titleCase } from "@/lib/format";
import type { Target } from "@/types/dashboard";

export function TargetTable({
  targets,
  onView,
  onEdit,
}: {
  targets: Target[];
  onView: (target: Target) => void;
  onEdit: (target: Target) => void;
}) {
  return (
    <table className="hidden w-full text-left text-sm md:table">
      <caption className="sr-only">Authorized targets</caption>
      <thead>
        <tr className="border-b border-border text-xs text-muted">
          <th scope="col" className="py-2.5 pr-4 font-medium">
            Name
          </th>
          <th scope="col" className="py-2.5 pr-4 font-medium">
            Type
          </th>
          <th scope="col" className="py-2.5 pr-4 font-medium">
            Environment
          </th>
          <th scope="col" className="py-2.5 pr-4 font-medium">
            Authorization
          </th>
          <th scope="col" className="py-2.5 pr-4 font-medium">
            Last Assessment
          </th>
          <th scope="col" className="py-2.5 pr-4 font-medium">
            Status
          </th>
          <th scope="col" className="py-2.5 pr-4 text-right font-medium">
            Actions
          </th>
        </tr>
      </thead>
      <tbody>
        {targets.map((target) => {
          const Icon = TARGET_TYPE_ICON[target.type];
          return (
            <tr
              key={target.id}
              className="motion-safe-transition border-b border-border/60 hover:bg-surface-raised/40"
            >
              <td className="py-3 pr-4">
                <div className="flex items-center gap-2.5">
                  <Icon size={15} className="text-muted" aria-hidden="true" />
                  <div>
                    <p className="font-medium text-foreground">{target.name}</p>
                    <p className="text-xs text-muted">{target.scopeValue}</p>
                  </div>
                </div>
              </td>
              <td className="py-3 pr-4 text-muted-strong">{TARGET_TYPE_LABEL[target.type]}</td>
              <td className="py-3 pr-4 text-muted-strong">{titleCase(target.environment)}</td>
              <td className="py-3 pr-4">
                <AuthorizationBadge status={target.authorizationStatus} />
              </td>
              <td className="py-3 pr-4 text-muted-strong">
                {formatRelativeDate(target.lastAssessment)}
              </td>
              <td className="py-3 pr-4">
                <TargetStatusBadge status={target.status} />
              </td>
              <td className="py-3 pr-4 text-right">
                <div className="flex justify-end gap-1">
                  <button
                    onClick={() => onView(target)}
                    aria-label={`View ${target.name}`}
                    className="motion-safe-transition rounded-md p-1.5 text-muted hover:bg-surface-hover hover:text-foreground"
                  >
                    <Eye size={15} />
                  </button>
                  <button
                    onClick={() => onEdit(target)}
                    aria-label={`Edit ${target.name}`}
                    className="motion-safe-transition rounded-md p-1.5 text-muted hover:bg-surface-hover hover:text-foreground"
                  >
                    <Pencil size={15} />
                  </button>
                </div>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
