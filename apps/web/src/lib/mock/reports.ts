import type { SecurityReport } from "@/types/dashboard";

export const MOCK_REPORTS: SecurityReport[] = [
  {
    id: "rpt-501",
    title: "Staging API — HTTP Header Assessment",
    targetName: "api.staging.internal",
    assessedAt: "2026-09-20T04:20:00Z",
    findingsCount: 4,
    severitySummary: { info: 2, low: 1, medium: 1, high: 0, critical: 0 },
    status: "draft",
  },
  {
    id: "rpt-500",
    title: "Marketing Site — Subdomain & TLS Review",
    targetName: "Corporate Marketing Site",
    assessedAt: "2026-09-19T16:10:00Z",
    findingsCount: 3,
    severitySummary: { info: 3, low: 0, medium: 0, high: 0, critical: 0 },
    status: "final",
  },
  {
    id: "rpt-499",
    title: "Production VPC — IAM Policy Review",
    targetName: "Primary VPC — us-east-1",
    assessedAt: "2026-09-19T11:45:00Z",
    findingsCount: 6,
    severitySummary: { info: 1, low: 2, medium: 2, high: 1, critical: 0 },
    status: "final",
  },
  {
    id: "rpt-498",
    title: "internal-db-01 — TLS Baseline",
    targetName: "internal-db-01",
    assessedAt: "2026-09-18T22:35:00Z",
    findingsCount: 1,
    severitySummary: { info: 1, low: 0, medium: 0, high: 0, critical: 0 },
    status: "final",
  },
  {
    id: "rpt-497",
    title: "Branch Office LAN — Segmentation Findings (Q2)",
    targetName: "Branch Office LAN",
    assessedAt: "2026-06-30T10:00:00Z",
    findingsCount: 9,
    severitySummary: { info: 2, low: 3, medium: 2, high: 1, critical: 1 },
    status: "archived",
  },
];
