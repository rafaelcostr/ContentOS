"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2 } from "lucide-react";
import { useEffect } from "react";
import { api } from "@/lib/api";
import { getOrganizationId, setOrganizationId } from "@/lib/org-context";

export function OrgSelector() {
  const qc = useQueryClient();
  const { data: orgs = [], isLoading } = useQuery({
    queryKey: ["organizations"],
    queryFn: () => api.getOrganizations(),
    staleTime: 60_000,
  });

  const currentId = getOrganizationId() || orgs[0]?.id || "";

  useEffect(() => {
    if (!getOrganizationId() && orgs[0]?.id) {
      setOrganizationId(orgs[0].id);
    }
  }, [orgs]);

  if (isLoading || orgs.length === 0) {
    return null;
  }

  return (
    <div className="border-b border-border px-3 py-3">
      <label className="mb-1 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
        <Building2 className="h-3 w-3" />
        Organização
      </label>
      <select
        className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
        value={currentId}
        onChange={(e) => {
          setOrganizationId(e.target.value);
          qc.invalidateQueries({ queryKey: ["projects"] });
          qc.invalidateQueries({ queryKey: ["pipelines"] });
          qc.invalidateQueries({ queryKey: ["videos"] });
        }}
      >
        {orgs.map((org) => (
          <option key={org.id} value={org.id}>
            {org.name}
            {org.is_personal ? " (pessoal)" : ""} — {org.role}
          </option>
        ))}
      </select>
    </div>
  );
}
