"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { api } from "@/lib/api";

type GrowthProjectSelectorProps = {
  projectId: string | null;
  onProjectIdChange: (projectId: string) => void;
  className?: string;
};

export function GrowthProjectSelector({ projectId, onProjectIdChange, className }: GrowthProjectSelectorProps) {
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) onProjectIdChange(projects[0].id);
  }, [projects, projectId, onProjectIdChange]);

  return (
    <div className={className}>
      <label className="text-xs font-medium text-muted-foreground">Projeto</label>
      <select
        className="mt-1 block w-full max-w-md rounded-md border border-border bg-background px-3 py-2 text-sm"
        value={projectId ?? ""}
        disabled={isLoading || !projects.length}
        onChange={(event) => onProjectIdChange(event.target.value)}
      >
        {projects.map((project) => (
          <option key={project.id} value={project.id}>
            {project.name}
          </option>
        ))}
      </select>
    </div>
  );
}
