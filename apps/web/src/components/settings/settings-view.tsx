"use client";

import { Field, Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { Panel } from "@/components/ui/panel";
import { Tabs } from "@/components/ui/tabs";
import { useState } from "react";

const SECTIONS = [
  { id: "general", label: "General" },
  { id: "ai-provider", label: "AI Provider" },
  { id: "terminal", label: "Terminal" },
  { id: "security-policy", label: "Security Policy" },
  { id: "notifications", label: "Notifications" },
  { id: "appearance", label: "Appearance" },
  { id: "audit", label: "Audit / Logging" },
];

export function SettingsView() {
  const [activeSection, setActiveSection] = useState(SECTIONS[0].id);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Providers, policy, and platform configuration. Secrets are configured server-side and never rendered here."
      />

      <Panel>
        <Tabs tabs={SECTIONS} onChange={setActiveSection} />
        <div className="pt-5">
          {activeSection === "general" && (
            <div className="max-w-md space-y-4">
              <Field label="Organization name" htmlFor="org-name">
                <Input id="org-name" defaultValue="Acme Security Operations" />
              </Field>
              <Field label="Default timezone" htmlFor="timezone">
                <Input id="timezone" defaultValue="UTC" />
              </Field>
            </div>
          )}

          {activeSection === "ai-provider" && (
            <div className="max-w-md space-y-4">
              <Field label="Active provider" htmlFor="ai-provider">
                <Input id="ai-provider" defaultValue="Gemini (primary)" disabled />
              </Field>
              <Field
                label="API key"
                htmlFor="ai-key"
                hint="Configured via GEMINI_API_KEY on the API server. Never exposed in this UI."
              >
                <Input id="ai-key" type="password" defaultValue="••••••••••••••••" disabled />
              </Field>
              <Field label="Model" htmlFor="ai-model">
                <Input id="ai-model" defaultValue="gemini-2.5-flash" disabled />
              </Field>
            </div>
          )}

          {activeSection === "terminal" && (
            <div className="max-w-md space-y-4">
              <Field label="Active adapter" htmlFor="adapter">
                <Input id="adapter" defaultValue="linux" disabled />
              </Field>
              <Field label="Default command timeout" htmlFor="timeout" hint="Seconds">
                <Input id="timeout" defaultValue="60" />
              </Field>
            </div>
          )}

          {activeSection === "security-policy" && (
            <div className="max-w-md space-y-4">
              <div className="flex items-center justify-between rounded-md border border-border bg-surface-raised/50 px-3 py-2.5">
                <div>
                  <p className="text-sm text-foreground">Require approval for medium+ risk</p>
                  <p className="text-xs text-muted">Enforced by the Policy Engine — not editable here.</p>
                </div>
                <Badge tone="accent">Enabled</Badge>
              </div>
              <div className="flex items-center justify-between rounded-md border border-border bg-surface-raised/50 px-3 py-2.5">
                <div>
                  <p className="text-sm text-foreground">Deny unregistered action types</p>
                  <p className="text-xs text-muted">Nothing executes until a tool is reviewed and registered.</p>
                </div>
                <Badge tone="accent">Enabled</Badge>
              </div>
            </div>
          )}

          {activeSection === "notifications" && (
            <div className="max-w-md space-y-4">
              <Field label="Notify on approval requests" htmlFor="notify-approvals">
                <Input id="notify-approvals" defaultValue="Email + in-app" />
              </Field>
              <Field label="Notify on report completion" htmlFor="notify-reports">
                <Input id="notify-reports" defaultValue="In-app" />
              </Field>
            </div>
          )}

          {activeSection === "appearance" && (
            <div className="max-w-md space-y-4">
              <Field label="Theme" htmlFor="theme">
                <Input id="theme" defaultValue="Cyber Dark (default)" disabled />
              </Field>
              <p className="text-xs text-muted">Additional themes are planned for a later phase.</p>
            </div>
          )}

          {activeSection === "audit" && (
            <div className="max-w-md space-y-4">
              <Field label="Audit log retention" htmlFor="retention" hint="Days">
                <Input id="retention" defaultValue="365" />
              </Field>
              <p className="text-xs text-muted">
                Every policy decision and execution result is written to an append-only audit
                log (see apps/api/app/db/models.py — AuditLogEntry).
              </p>
            </div>
          )}
        </div>
      </Panel>
    </div>
  );
}
