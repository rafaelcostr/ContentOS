/** Pipeline step labels — V1 (9), V2 dynamic (14), V3 quality (10). */

export const V1_PIPELINE_STEPS = [
  { key: "research", label: "Pesquisa" },
  { key: "script", label: "Roteiro" },
  { key: "scene", label: "Cenas" },
  { key: "takes", label: "Takes" },
  { key: "voice", label: "Voz" },
  { key: "subtitle", label: "Legendas" },
  { key: "editor", label: "Editor" },
  { key: "quality", label: "Qualidade" },
  { key: "publisher", label: "Publicação" },
] as const;

export const V2_PIPELINE_STEPS = [
  { key: "research", label: "Pesquisa" },
  { key: "script", label: "Roteiro" },
  { key: "scene", label: "Cenas" },
  { key: "clip_research", label: "Clip Research" },
  { key: "asset_collector", label: "Coleta de Assets" },
  { key: "asset_index", label: "Indexação" },
  { key: "takes", label: "Takes" },
  { key: "voice", label: "Voz" },
  { key: "subtitle", label: "Legendas" },
  { key: "editor", label: "Editor" },
  { key: "quality", label: "Qualidade" },
  { key: "publisher", label: "Publicação" },
  { key: "thumbnail", label: "Thumbnail" },
  { key: "analytics", label: "Analytics AI" },
] as const;

export const V3_QUALITY_STEPS = [
  { key: "trend_intelligence", label: "Trend Intelligence" },
  { key: "research", label: "Pesquisa" },
  { key: "hook", label: "Hook" },
  { key: "script", label: "Roteiro" },
  { key: "script_review", label: "Revisão de Roteiro" },
  { key: "emotion", label: "Emoção" },
  { key: "scene", label: "Cenas" },
  { key: "storyboard", label: "Storyboard" },
  { key: "scene_director", label: "Scene Director" },
  { key: "takes", label: "Takes" },
  { key: "voice", label: "Voz" },
  { key: "subtitle", label: "Legendas" },
  { key: "editor", label: "Editor" },
  { key: "quality", label: "Qualidade" },
  { key: "video_review", label: "Revisão de Vídeo" },
  { key: "publisher", label: "Publicação" },
] as const;

export const V4_INTELLIGENCE_STEPS = [
  { key: "trend_intelligence", label: "Trend Intelligence" },
  { key: "research", label: "Pesquisa" },
  { key: "hook", label: "Hook" },
  { key: "script", label: "Roteiro" },
  { key: "script_review", label: "Revisão de Roteiro" },
  { key: "emotion", label: "Emoção" },
  { key: "content_intelligence", label: "Content Intelligence" },
  { key: "scene", label: "Cenas" },
  { key: "storyboard", label: "Storyboard" },
  { key: "scene_director", label: "Scene Director" },
  { key: "takes", label: "Takes" },
  { key: "voice", label: "Voz" },
  { key: "subtitle", label: "Legendas" },
  { key: "editor", label: "Editor" },
  { key: "quality", label: "Qualidade" },
  { key: "video_review", label: "Revisão de Vídeo" },
  { key: "publisher", label: "Publicação" },
] as const;

export const V4_MULTI_TEXT_STEPS = [
  ...V4_INTELLIGENCE_STEPS,
  { key: "multi_content", label: "Multi Content" },
] as const;

export const V4_MULTI_FULL_STEPS = [
  ...V4_MULTI_TEXT_STEPS,
  { key: "multi_content_video", label: "Video Variants" },
] as const;

const STEP_LABELS: Record<string, string> = Object.fromEntries(
  [
    ...V1_PIPELINE_STEPS,
    ...V2_PIPELINE_STEPS,
    ...V3_QUALITY_STEPS,
    ...V4_INTELLIGENCE_STEPS,
    ...V4_MULTI_TEXT_STEPS,
    ...V4_MULTI_FULL_STEPS,
  ].map((s) => [s.key, s.label])
);

export function stepLabel(key: string): string {
  return STEP_LABELS[key] ?? key;
}

export function stepsForPipeline(
  jobs: { step: string; order: number }[],
  workflowName?: string | null
): { key: string; label: string }[] {
  if (jobs.length > 0) {
    return [...jobs]
      .sort((a, b) => a.order - b.order)
      .map((j) => ({ key: j.step, label: stepLabel(j.step) }));
  }
  if (workflowName === "v2-dynamic") {
    return [...V2_PIPELINE_STEPS];
  }
  if (workflowName === "v3-quality") {
    return [...V3_QUALITY_STEPS];
  }
  if (workflowName === "v4-intelligence") {
    return [...V4_INTELLIGENCE_STEPS];
  }
  if (workflowName === "v4-multi-text") {
    return [...V4_MULTI_TEXT_STEPS];
  }
  if (workflowName === "v4-multi-full") {
    return [...V4_MULTI_FULL_STEPS];
  }
  return [...V1_PIPELINE_STEPS];
}

export const WORKFLOW_OPTIONS = [
  { value: "v1-default", label: "V1 — 9 steps" },
  { value: "v2-full", label: "V2 Full — async agents" },
  { value: "v2-dynamic", label: "V2 Dynamic — 14 steps" },
  { value: "v3-quality", label: "V3 Quality — Trend + Director (16 steps)" },
  { value: "v4-intelligence", label: "V4 Intelligence — Viral + Reuse (17 steps)" },
  { value: "v4-multi-text", label: "V4 Multi Text — + Thread, LinkedIn, SEO (18 steps)" },
  { value: "v4-multi-full", label: "V4 Multi Full — + TikTok, Shorts, Reels (19 steps)" },
] as const;
