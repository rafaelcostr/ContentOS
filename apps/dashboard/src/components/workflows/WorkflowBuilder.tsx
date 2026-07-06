"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type WorkflowStepCatalogItem, type WorkflowTemplate } from "@/lib/api";
import { stepLabel } from "@/lib/pipeline-steps";

export function WorkflowBuilder() {
  const qc = useQueryClient();
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [steps, setSteps] = useState<string[]>([]);
  const [editingSlug, setEditingSlug] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [dragIndex, setDragIndex] = useState<number | null>(null);

  const { data: catalog = [] } = useQuery({
    queryKey: ["workflow-step-catalog"],
    queryFn: api.getWorkflowStepCatalog,
  });

  const { data: workflows = [] } = useQuery({
    queryKey: ["workflows"],
    queryFn: api.getWorkflows,
  });

  const customWorkflows = workflows.filter((w) => !w.is_builtin);

  const saveWorkflow = useMutation({
    mutationFn: async () => {
      if (editingSlug) {
        return api.updateCustomWorkflow(editingSlug, { description: description || undefined, steps });
      }
      return api.createCustomWorkflow({
        slug: slug.trim(),
        description: description || undefined,
        steps,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workflows"] });
      setSlug("");
      setDescription("");
      setSteps([]);
      setEditingSlug(null);
      setError("");
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Erro ao salvar workflow"),
  });

  const deleteWorkflow = useMutation({
    mutationFn: (s: string) => api.deleteCustomWorkflow(s),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });

  const addStep = useCallback((key: string) => {
    setSteps((prev) => (prev.includes(key) ? prev : [...prev, key]));
  }, []);

  const removeStep = (key: string) => setSteps((prev) => prev.filter((s) => s !== key));

  const moveStep = (from: number, to: number) => {
    setSteps((prev) => {
      const next = [...prev];
      const [item] = next.splice(from, 1);
      next.splice(to, 0, item);
      return next;
    });
  };

  function loadForEdit(w: WorkflowTemplate) {
    if (!w.slug) return;
    setEditingSlug(w.slug);
    setSlug(w.slug);
    setDescription(w.description ?? "");
    setSteps([...w.steps]);
    setError("");
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (steps.length === 0) {
      setError("Adicione ao menos um step");
      return;
    }
    if (!editingSlug && !slug.trim()) {
      setError("Informe um slug");
      return;
    }
    saveWorkflow.mutate();
  }

  function onDropCanvas(e: React.DragEvent, targetIndex: number) {
    e.preventDefault();
    const key = e.dataTransfer.getData("text/step-key");
    if (key && !steps.includes(key)) {
      setSteps((prev) => {
        const next = [...prev];
        next.splice(targetIndex, 0, key);
        return next;
      });
      setDragIndex(null);
      return;
    }
    if (dragIndex !== null && dragIndex !== targetIndex) {
      moveStep(dragIndex, targetIndex);
    }
    setDragIndex(null);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Workflow Builder</h1>
        <p className="text-sm text-muted-foreground">
          Arraste steps para montar um pipeline customizado por organização.
        </p>
      </div>
      {error && <p className="text-sm text-red-500">{error}</p>}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Steps disponíveis</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {catalog.map((item: WorkflowStepCatalogItem) => (
              <button
                key={item.key}
                type="button"
                draggable
                onDragStart={(e) => e.dataTransfer.setData("text/step-key", item.key)}
                onClick={() => addStep(item.key)}
                className="rounded-md border border-border bg-muted px-2 py-1 text-xs hover:bg-muted/80"
                title={`Tier ${item.tier}`}
              >
                {stepLabel(item.key)}
              </button>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Sequência ({steps.length})</CardTitle>
          </CardHeader>
          <CardContent
            className="min-h-[200px] space-y-2 rounded-md border border-dashed border-border p-3"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => onDropCanvas(e, steps.length)}
          >
            {steps.length === 0 ? (
              <p className="text-sm text-muted-foreground">Arraste steps aqui ou clique na paleta.</p>
            ) : (
              steps.map((key, index) => (
                <div
                  key={`${key}-${index}`}
                  draggable
                  onDragStart={() => setDragIndex(index)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => onDropCanvas(e, index)}
                  className="flex cursor-grab items-center justify-between rounded-md border border-border bg-card px-3 py-2 text-sm"
                >
                  <span>
                    {index + 1}. {stepLabel(key)}
                  </span>
                  <Button type="button" variant="ghost" size="sm" onClick={() => removeStep(key)}>
                    ×
                  </Button>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>{editingSlug ? `Editar: ${editingSlug}` : "Salvar workflow"}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="grid gap-3 sm:grid-cols-2">
            <Input
              placeholder="slug (ex: quality-lite)"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              disabled={!!editingSlug}
            />
            <Input
              placeholder="Descrição"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <div className="flex gap-2 sm:col-span-2">
              <Button type="submit" disabled={saveWorkflow.isPending}>
                {saveWorkflow.isPending ? "Salvando..." : editingSlug ? "Atualizar" : "Criar workflow"}
              </Button>
              {editingSlug && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setEditingSlug(null);
                    setSlug("");
                    setDescription("");
                    setSteps([]);
                  }}
                >
                  Cancelar
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
      {customWorkflows.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Workflows customizados</CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-border">
            {customWorkflows.map((w) => (
              <div key={w.name} className="flex items-center justify-between gap-4 py-3 text-sm">
                <div>
                  <p className="font-medium">{w.slug}</p>
                  <p className="text-xs text-muted-foreground">
                    {w.steps.length} steps · <code>{w.name}</code>
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => loadForEdit(w)}>
                    Editar
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => w.slug && deleteWorkflow.mutate(w.slug)}
                    disabled={deleteWorkflow.isPending}
                  >
                    Excluir
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
