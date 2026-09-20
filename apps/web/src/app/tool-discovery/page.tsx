"use client";

import { useEffect, useState } from "react";
import { ToolsView } from "@/components/tools/tools-view";
import { listTools } from "@/lib/tools-api";
import type { RegistryTool } from "@/types/tools";

export default function ToolDiscoveryPage() {
  const [tools, setTools] = useState<RegistryTool[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listTools()
      .then((result) => {
        if (!cancelled) setTools(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return <ToolsView tools={tools} isLoading={isLoading} error={error} />;
}
