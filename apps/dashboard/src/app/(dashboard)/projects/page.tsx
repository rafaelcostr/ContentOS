"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, MouseEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { ProjectSchedules } from "@/components/projects/ProjectSchedules";
import { getAccessToken } from "@/lib/auth-token";
import { parseApiError, statusLabel } from "@/lib/i18n";
import { WORKFLOW_OPTIONS } from "@/lib/pipeline-steps";
import { formatDate, statusColor } from "@/lib/utils";

export default function ProjectsPage() {
  const [name, setName] = useState("");
  const [topic, setTopic] = useState("");
  const [workflowName, setWorkflowName] = useState("v1-default");
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const qc = useQueryClient();

  const {
    data: projects = [],
    isLoading,
    isError,
    error: loadError,
  } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
    retry: false,
  });

  const { data: pipelines = [] } = useQuery({
    queryKey: ["pipelines", selectedProject],
    queryFn: () => api.getPipelinesByProject(selectedProject!),
    enabled: !!selectedProject,
  });

  const createProject = useMutation({
    mutationFn: () => {
      if (!getAccessToken()) {
        throw new Error("Você não está logado. Acesse a página de login.");
      }
      return api.createProject(name.trim());
    },
    onSuccess: (project) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      setName("");
      setSelectedProject(project.id);
      setErrorMsg("");
      setSuccessMsg(`Projeto "${project.name}" criado com sucesso!`);
    },
    onError: (err) => {
      setSuccessMsg("");
      const msg = parseApiError(err);
      setErrorMsg(msg);
      if (msg.includes("login") || msg.includes("401")) {
        setTimeout(() => {
          window.location.href = "/login";
        }, 1500);
      }
    },
  });

  const { data: workflowTemplates = [] } = useQuery({
    queryKey: ["workflows"],
    queryFn: api.getWorkflows,
  });

  const workflowOptions = workflowTemplates.length
    ? workflowTemplates.map((w) => ({
        value: w.name,
        label: w.is_builtin ? w.name : `${w.slug ?? w.name} (custom)`,
      }))
    : [...WORKFLOW_OPTIONS];

  const createPipeline = useMutation({
    mutationFn: () => {
      if (!getAccessToken()) {
        throw new Error("Você não está logado. Acesse a página de login.");
      }
      return api.createPipeline(selectedProject!, topic.trim(), workflowName);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipelines", selectedProject] });
      qc.invalidateQueries({ queryKey: ["pipelines"] });
      setTopic("");
      setErrorMsg("");
      setSuccessMsg("Pipeline iniciado! Acompanhe em Produção.");
    },
    onError: (err) => {
      setSuccessMsg("");
      setErrorMsg(parseApiError(err));
    },
  });

  const deletePipeline = useMutation({
    mutationFn: (id: string) => api.deletePipeline(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ["pipelines", selectedProject] });
      qc.invalidateQueries({ queryKey: ["pipelines"] });
      qc.removeQueries({ queryKey: ["pipeline", id] });
      setErrorMsg("");
      setSuccessMsg("Pipeline excluído.");
    },
    onError: (err) => {
      setSuccessMsg("");
      setErrorMsg(parseApiError(err));
    },
  });

  const deleteProject = useMutation({
    mutationFn: (id: string) => api.deleteProject(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["pipelines"] });
      if (selectedProject === id) setSelectedProject(null);
      setErrorMsg("");
      setSuccessMsg("Projeto excluído.");
    },
    onError: (err) => {
      setSuccessMsg("");
      setErrorMsg(parseApiError(err));
    },
  });

  function handleDeleteProject(e: MouseEvent, projectId: string, projectName: string) {
    e.stopPropagation();
    if (
      !window.confirm(
        `Excluir o projeto "${projectName}" e todos os pipelines? Esta ação não pode ser desfeita.`
      )
    ) {
      return;
    }
    deleteProject.mutate(projectId);
  }

  function handleDeletePipeline(pipelineId: string, pipelineTopic: string) {
    if (!window.confirm(`Excluir o pipeline "${pipelineTopic}"? Esta ação não pode ser desfeita.`)) return;
    deletePipeline.mutate(pipelineId);
  }

  function handleCreateProject(e: FormEvent) {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");
    const trimmed = name.trim();
    if (!trimmed) {
      setErrorMsg("Digite um nome para o projeto.");
      return;
    }
    if (createProject.isPending) return;
    createProject.mutate();
  }

  function handleCreatePipeline(e: FormEvent) {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");
    if (!topic.trim()) {
      setErrorMsg("Digite um tema para o pipeline.");
      return;
    }
    if (!selectedProject) {
      setErrorMsg("Selecione um projeto antes de iniciar o pipeline.");
      return;
    }
    if (createPipeline.isPending) return;
    createPipeline.mutate();
  }

  return (
    <div className="p-8">
      <h1 className="mb-2 text-2xl font-bold">Projetos</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Crie um projeto, selecione-o e inicie um pipeline com um tema.
      </p>

      {(errorMsg || successMsg) && (
        <div
          className={`mb-6 rounded-md border px-4 py-3 text-sm ${
            errorMsg
              ? "border-red-500/50 bg-red-500/10 text-red-400"
              : "border-emerald-500/50 bg-emerald-500/10 text-emerald-400"
          }`}
        >
          {errorMsg || successMsg}
        </div>
      )}

      <div className="mb-8 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Novo projeto</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateProject} className="flex gap-2">
              <Input
                placeholder="Nome do projeto (ex: GTA 6 atualizações)"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={createProject.isPending}
              />
              <Button type="submit" disabled={createProject.isPending}>
                {createProject.isPending ? "Criando..." : "Criar"}
              </Button>
            </form>
            <p className="mt-2 text-xs text-muted-foreground">Pressione Enter para criar</p>
          </CardContent>
        </Card>

        {selectedProject && (
          <Card>
            <CardHeader>
              <CardTitle>Novo pipeline</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreatePipeline} className="space-y-3">
                <div className="flex gap-2">
                  <Input
                    placeholder="Tema (ex: GTA 6)"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    disabled={createPipeline.isPending}
                  />
                  <Button type="submit" disabled={createPipeline.isPending}>
                    {createPipeline.isPending ? "Iniciando..." : "Iniciar"}
                  </Button>
                </div>
                <select
                  value={workflowName}
                  onChange={(e) => setWorkflowName(e.target.value)}
                  disabled={createPipeline.isPending}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                >
                  {workflowOptions.map((w) => (
                    <option key={w.value} value={w.value}>
                      {w.label}
                    </option>
                  ))}
                </select>
              </form>
              <p className="mt-2 text-xs text-muted-foreground">Pressione Enter para iniciar o pipeline</p>
            </CardContent>
          </Card>
        )}

        {selectedProject && <ProjectSchedules projectId={selectedProject} />}
      </div>

      {isLoading && <p className="text-muted-foreground">Carregando projetos...</p>}
      {isError && (
        <p className="mb-4 text-sm text-red-400">{parseApiError(loadError)}</p>
      )}

      {!isLoading && !isError && projects.length === 0 && (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            Nenhum projeto ainda. Crie o primeiro acima.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {projects.map((p) => (
          <Card
            key={p.id}
            className={`cursor-pointer transition-colors ${
              selectedProject === p.id ? "border-primary ring-1 ring-primary" : ""
            }`}
            onClick={() => {
              setSelectedProject(p.id);
              setSuccessMsg("");
              setErrorMsg("");
            }}
          >
            <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
              <div className="min-w-0">
                <CardTitle className="text-base">{p.name}</CardTitle>
                <p className="text-xs text-muted-foreground">{formatDate(p.created_at)}</p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={deleteProject.isPending}
                className="shrink-0 border-red-500/40 text-red-400 hover:bg-red-500/10"
                onClick={(e) => handleDeleteProject(e, p.id, p.name)}
              >
                {deleteProject.isPending ? "..." : "Excluir"}
              </Button>
            </CardHeader>
            {p.description && (
              <CardContent>
                <p className="text-sm text-muted-foreground">{p.description}</p>
              </CardContent>
            )}
            {selectedProject === p.id && (
              <CardContent>
                <p className="text-xs text-primary">Selecionado — inicie um pipeline acima</p>
              </CardContent>
            )}
          </Card>
        ))}
      </div>

      {selectedProject && pipelines.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-4 font-semibold">Pipelines deste projeto</h2>
          <div className="space-y-2">
            {pipelines.map((pl) => (
              <div
                key={pl.id}
                className="flex items-center justify-between gap-3 rounded-lg border border-border p-4"
              >
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{pl.topic}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(pl.created_at)}
                    {pl.workflow_name ? ` · ${pl.workflow_name}` : ""}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge className={statusColor(pl.status)}>{statusLabel(pl.status)}</Badge>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={deletePipeline.isPending}
                    className="border-red-500/40 text-red-400 hover:bg-red-500/10"
                    onClick={() => handleDeletePipeline(pl.id, pl.topic)}
                  >
                    {deletePipeline.isPending ? "Excluindo..." : "Excluir"}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
