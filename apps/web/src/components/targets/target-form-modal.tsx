"use client";

import { Field, Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import type { Target } from "@/types/dashboard";

export function TargetFormModal({
  target,
  isOpen,
  onClose,
}: {
  target: Target | null;
  isOpen: boolean;
  onClose: () => void;
}) {
  const isEditing = target !== null;

  return (
    <Modal title={isEditing ? "Edit Target" : "Add Target"} isOpen={isOpen} onClose={onClose}>
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          onClose();
        }}
      >
        <Field label="Name" htmlFor="target-name">
          <Input id="target-name" defaultValue={target?.name} placeholder="e.g. api.staging.internal" />
        </Field>
        <Field label="Scope value" htmlFor="target-scope" hint="Domain, IP range, host, or account identifier.">
          <Input id="target-scope" defaultValue={target?.scopeValue} placeholder="e.g. 10.20.0.0/24" />
        </Field>
        <Field label="Authorization evidence" htmlFor="target-evidence" hint="Reference to the signed authorization on file — not stored as free text in production.">
          <Input id="target-evidence" placeholder="e.g. SOW-2026-0417" />
        </Field>
        <p className="rounded-md border border-border bg-surface-raised/60 px-3 py-2 text-xs text-muted">
          Phase 2 UI only — submitting this form does not create or modify a target. Target
          persistence goes through the Policy Engine&apos;s authorization checks
          (see services/policy/engine.py).
        </p>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary">
            {isEditing ? "Save changes" : "Add target"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
