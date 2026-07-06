import { clearAccessTokens, getAccessToken } from "@/lib/auth-token";
import { getOrganizationId } from "@/lib/org-context";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAccessToken();
  const orgId = getOrganizationId();
  const method = options?.method?.toUpperCase() ?? "GET";
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      ...(options?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(orgId ? { "X-Organization-Id": orgId } : {}),
      ...options?.headers,
    },
    cache: method === "GET" ? "default" : "no-store",
  });
  if (res.status === 401) {
    clearAccessTokens();
    throw new Error("API 401: Faça login novamente para continuar.");
  }
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface Project {
  id: string;
  org_id?: string | null;
  name: string;
  description: string | null;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  is_personal: boolean;
  role: string;
}

export interface OrganizationApiKey {
  id: string;
  organization_id: string;
  name: string;
  key_prefix: string;
  scope: "read" | "write";
  rate_limit_per_minute: number;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

export interface OrganizationApiKeyCreated extends OrganizationApiKey {
  api_key: string;
}

export interface BillingPlan {
  slug: string;
  name: string;
  monthly_credits: number;
  monthly_pipeline_quota: number;
  max_concurrent_pipelines: number;
  price_usd_cents: number | null;
  stripe_available: boolean;
}

export interface OrgBilling {
  organization_id: string;
  plan_slug: string;
  plan_name: string;
  monthly_credits: number;
  credits_balance: number;
  subscription_status: string;
  stripe_enabled: boolean;
  has_stripe_customer: boolean;
  credits_period_start: string | null;
  monthly_pipeline_quota: number;
  monthly_pipelines_used: number;
  max_concurrent_pipelines: number;
  concurrent_pipelines_active: number;
}

export interface Pipeline {
  id: string;
  project_id: string;
  org_id?: string | null;
  topic: string;
  workflow_name?: string | null;
  status: string;
  current_step: string | null;
  created_at: string;
}

export interface PipelineSchedule {
  id: string;
  project_id: string;
  org_id?: string | null;
  name: string;
  topic: string;
  workflow_name?: string | null;
  cron_expression: string;
  timezone: string;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  last_pipeline_id: string | null;
  last_error: string | null;
  created_at: string;
}

export interface WorkflowTemplate {
  name: string;
  slug: string | null;
  org_id: string | null;
  description: string | null;
  steps: string[];
  config: Record<string, unknown> | null;
  is_default: boolean;
  is_builtin: boolean;
}

export interface WorkflowStepCatalogItem {
  key: string;
  label: string;
  tier: string;
}

export interface PipelineJob {
  id: string;
  step: string;
  status: string;
  order: number;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface PipelineDetail extends Pipeline {
  jobs: PipelineJob[];
  error_message: string | null;
}

export interface Video {
  id: string;
  project_id: string;
  title: string;
  status: string;
  duration_seconds: number | null;
  width: number;
  height: number;
  created_at: string;
}

export interface Asset {
  id: string;
  category: string;
  object_key: string;
  content_type: string;
  size_bytes: number;
  sha256?: string | null;
  tags?: string[] | null;
  version?: number;
  metadata_?: Record<string, unknown> | null;
  created_at: string;
}

export interface AssetPreview {
  asset_id: string;
  url: string | null;
  content_type: string;
  expires_in: number;
  kind: "image" | "video" | "audio" | "other" | string;
  available: boolean;
  error?: string | null;
}

export interface LogEntry {
  id: string;
  agent: string | null;
  level: string;
  message: string;
  pipeline_id: string | null;
  created_at: string;
}

export interface AnalyticsOverview {
  videos_created: number;
  pipelines_total: number;
  pipelines_completed: number;
  avg_duration_seconds: number;
  error_rate: number;
  agents_online: number;
  queue_pending: number;
}

export interface StorageStats {
  total_assets: number;
  total_bytes: number;
  total_mb: number;
  indexed_hashes?: number;
  by_category: Record<string, { count: number; size_bytes: number }>;
}

export interface ProviderStatus {
  text: string;
  speech: string;
  subtitle: string;
  mode?: string;
  ai_gateway_url?: string | null;
  available_text: string[];
  available_speech: string[];
  available_subtitle: string[];
}

export interface PromptSummary {
  id: string;
  version: string;
  agent: string;
  variables: string[];
  description: string;
  source: string;
}

export interface PromptDetail extends PromptSummary {
  system_template: string;
  user_template: string;
  raw_content: string;
}

export interface AgentModelConfig {
  agent: string;
  provider_type: string;
  provider: string;
  model: string;
  updated_at: string | null;
  editable: boolean;
}

export interface ProjectMemory {
  project_id: string;
  tone: string;
  niche: string;
  hook_style: string;
  goal: string;
  cta: string;
  avg_duration: number | null;
  vocabulary: string[];
  style: Record<string, string>;
  history: { summary?: string }[];
  humor_level?: number | null;
  pace?: string;
  visual_style?: Record<string, string>;
  narrator_persona?: string;
  preferred_formats?: string[];
  hook_patterns?: string[];
  cta_style?: string;
  memory_context_preview: string;
  dna_context_preview?: string;
}

export interface ProjectDna {
  project_id: string;
  humor_level: number | null;
  pace: string;
  visual_style: Record<string, string>;
  narrator_persona: string;
  preferred_formats: string[];
  hook_patterns: string[];
  cta_style: string;
  dna_context_preview: string;
}

export interface KnowledgeHit {
  resource_type: string;
  resource_id: string | null;
  title: string;
  snippet: string;
  similarity: number;
  metadata: Record<string, unknown>;
}

export interface KnowledgeEntry {
  id: string | null;
  project_id: string;
  pipeline_id: string | null;
  resource_type: string;
  resource_id: string | null;
  title: string;
  snippet: string;
  version: number;
  created_at: string | null;
  has_embedding: boolean;
}

export interface ReuseSuggestion {
  resource_type: string;
  resource_id: string | null;
  title: string;
  similarity: number;
  reason: string;
  metadata: Record<string, unknown>;
}

export interface ViralReport {
  viral_score: number;
  retention_prediction: number;
  recommendations: string[];
  hook_score?: number | null;
  rhythm_score?: number | null;
  emotion_score?: number | null;
  scene_score?: number | null;
  cta_score?: number | null;
  details?: Record<string, unknown>;
  reuse_suggestions?: ReuseSuggestion[];
}

export interface AbVariantItem {
  variant_id: string;
  value: string;
  score: number;
  metadata?: Record<string, unknown>;
}

export interface AbDimensionResult {
  dimension: string;
  variants: AbVariantItem[];
  winner_index: number;
  winner: AbVariantItem | null;
}

export interface AbTestReport {
  project_id: string;
  pipeline_id: string | null;
  dimensions: AbDimensionResult[];
  winners: Record<string, AbVariantItem>;
}

export interface AbVariantSet {
  id: string;
  project_id: string;
  pipeline_id: string;
  dimension: string;
  variants: AbVariantItem[];
  winner_index: number;
  winner: AbVariantItem | null;
  created_at: string | null;
}

export interface ContentScoreDimension {
  name: string;
  score: number;
  weight: number;
  source: string;
}

export interface ContentScoreReport {
  total_score: number;
  grade: string;
  mode: string;
  summary: string;
  dimensions: ContentScoreDimension[];
}

export interface SpecialistProfile {
  specialist_id: string;
  name: string;
  niche: string;
  tone?: string;
  prompt_pack?: string;
  pilot?: boolean;
  enabled?: boolean;
  coming_soon?: boolean;
}

export interface SpecialistSelection {
  specialist: SpecialistProfile;
  confidence: number;
  reason: string;
  specialist_context: string;
}

export interface TextArtifact {
  format: string;
  title: string;
  content: string;
  data?: Record<string, unknown>;
  source: string;
}

export interface MultiContentReport {
  project_id: string;
  pipeline_id: string | null;
  topic: string;
  artifact_count: number;
  artifacts: TextArtifact[];
}

export interface CropSpec {
  width: number;
  height: number;
  crop_bias: string;
  max_duration_seconds: number;
  safe_zone: string;
}

export interface VideoPlatformVariant {
  platform: string;
  title: string;
  description: string;
  hashtags: string[];
  crop_spec: CropSpec;
  render_ref?: Record<string, unknown> | null;
  data?: Record<string, unknown>;
  source: string;
}

export interface VideoVariantsReport {
  project_id: string;
  pipeline_id: string | null;
  topic: string;
  variant_count: number;
  variants: VideoPlatformVariant[];
}

export interface LearningSignal {
  signal_type: string;
  value: string;
  score?: number | null;
  source: string;
  metadata?: Record<string, unknown>;
}

export interface LearningReport {
  project_id: string;
  pipeline_id: string | null;
  topic: string;
  content_score?: number | null;
  viral_score?: number | null;
  specialist_id?: string | null;
  hook_text: string;
  cta_text: string;
  signal_count: number;
  signals: LearningSignal[];
  memory_applied: boolean;
  memory_updates: string[];
  kb_indexed_count: number;
}

export interface TrendForecastReport {
  project_id: string;
  pipeline_id: string | null;
  topic: string;
  niche: string;
  trend_score: number;
  expected_growth: string;
  production_recommendation: string;
  pacing_hint: string;
  pattern_count: number;
  sources: string[];
  signals?: Record<string, unknown>;
}

export interface GraphNode {
  id: string;
  type: string;
  node_id: string;
  label: string;
  pipeline_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  source_type: string;
  source_id: string;
  target_type: string;
  target_id: string;
  relation: string;
  pipeline_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface GraphView {
  project_id: string;
  node_count: number;
  edge_count: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ExecutiveModuleStatus {
  key: string;
  label: string;
  status: string;
  metric: string;
  href: string;
  detail: string;
}

export interface ExecutiveSummary {
  project_id: string;
  project_name: string;
  pipelines_total: number;
  pipelines_completed: number;
  knowledge_entries: number;
  learning_insights: number;
  graph_nodes: number;
  graph_edges: number;
  ab_variant_sets: number;
  specialists_available: number;
  avg_content_score: number | null;
  avg_viral_score: number | null;
  latest_trend_score: number | null;
  latest_trend_growth: string | null;
  dna_preview: string;
  hook_patterns: string[];
  latest_learning_topic: string | null;
  modules: ExecutiveModuleStatus[];
}

export interface CostOverview {
  total_cost_usd: number;
  total_tokens_input: number;
  total_tokens_output: number;
  total_operations: number;
  by_provider: Record<string, { cost_usd: number; operations: number }>;
  by_agent: Record<string, { cost_usd: number; operations: number }>;
}

export interface DomainEvent {
  id?: string | null;
  type: string;
  pipeline_id?: string | null;
  project_id?: string | null;
  job_id?: string | null;
  agent?: string | null;
  step?: string | null;
  status?: string | null;
  data?: Record<string, unknown>;
  timestamp?: string | null;
  stream_id?: string | null;
}

export interface EventStreamInfo {
  stream_key: string;
  length?: number;
  error?: string;
}

export interface AnalyticsInsight {
  id: string;
  project_id: string;
  pipeline_id: string;
  video_id?: string | null;
  metrics: Record<string, unknown>;
  analysis: {
    summary?: string;
    strengths?: string[];
    weaknesses?: string[];
    suggestions?: string[];
    recommended_prompt_tweaks?: Record<string, unknown>[];
    score?: number;
  };
  models_used?: Record<string, { provider: string; model: string }>;
  prompts_used?: Record<string, string>;
  applied_to_memory: boolean;
  score?: number;
  summary?: string;
  created_at: string;
}

export interface CacheStats {
  enabled: boolean;
  total_keys: number;
  by_agent: Record<string, number>;
  ttl_seconds: Record<string, number>;
  redis_url?: string;
  error?: string | null;
}

export interface CacheDeleteResult {
  deleted: boolean | number;
  key?: string | null;
  agent?: string | null;
}

export interface ModelCatalog {
  text: string[];
  speech: string[];
  subtitle: string[];
  compute: string[];
}

export interface PromptRenderResult {
  id: string;
  version: string;
  system: string;
  user: string;
}

export interface ProviderHealthItem {
  name: string;
  url: string;
  healthy: boolean;
  detail: string;
}

export interface ProvidersHealthResponse {
  all_healthy: boolean;
  providers: ProviderHealthItem[];
}

export interface AgentStats {
  name: string;
  queue: string;
  description: string;
  status: string;
  provider: string;
  model: string;
  queue_depth: number;
  running: number;
  completed_total: number;
  failed_total: number;
  avg_duration_seconds: number | null;
  last_execution: string | null;
  recent_logs: { message: string; level: string; created_at: string }[];
}

export interface SystemMetrics {
  cpu: { percent: number; cores: number };
  memory: { used_mb: number; total_mb: number; percent: number };
  disk: { used_gb: number; total_gb: number; percent: number };
  gpu: {
    available: boolean;
    name: string;
    utilization: number;
    memory_used_mb: number;
    memory_total_mb: number;
  } | null;
}

export interface InfrastructureMetrics {
  redis: { status: string; memory_mb?: number; connected_clients?: number; error?: string };
  postgres: { status: string; latency_ms?: number; error?: string };
  celery: { workers: number; queues: Record<string, number>; total_pending: number };
}

export interface ProviderAnalytics {
  provider: string;
  steps: string[];
  jobs_total: number;
  jobs_completed: number;
  jobs_failed: number;
  jobs_running: number;
  success_rate: number;
  healthy?: boolean | null;
  endpoint?: string;
}

export interface PlatformPluginInfo {
  name: string;
  version: string;
  description: string;
  platform: string;
  hooks: string[];
  enabled: boolean;
  installed?: boolean;
  source?: string;
}

export interface MarketplacePlugin {
  name: string;
  version: string;
  description: string;
  platform: string;
  hooks: string[];
  builtin: boolean;
  installed: boolean;
  enabled: boolean;
  source: string;
  category: string;
  author: string;
}

export interface UnifiedMarketplaceItem {
  id: string;
  type: string;
  name: string;
  description: string;
  version: string;
  author: string;
  category: string;
  source: string;
  installed?: boolean | null;
  enabled?: boolean | null;
  platform?: string | null;
  hooks?: string[] | null;
  builtin?: boolean | null;
  queue?: string | null;
  tier?: string | null;
  steps?: string[] | null;
  step_count?: number | null;
  slug?: string | null;
  org_id?: string | null;
  is_default?: boolean | null;
  metadata?: Record<string, unknown> | null;
}

export interface UnifiedMarketplaceCatalog {
  summary: Record<string, number>;
  items: UnifiedMarketplaceItem[];
  remote_configured: boolean;
}

export interface PlatformPluginsConfig {
  publish_mode: string;
  enabled_platforms: string[];
  plugins: PlatformPluginInfo[];
}

export interface ContentSourceHealth {
  source_id: string;
  healthy: boolean;
  message?: string;
  latency_ms?: number | null;
}

export interface PipelineAssetCollection {
  pipeline_id: string;
  project_id: string;
  candidates: unknown[];
  assets: unknown[];
  status: string;
}

export interface PipelineCollectionSummary {
  pipeline_id: string;
  project_id: string;
  status: string;
  candidate_scenes: number;
  collected_assets: number;
  updated_at: string;
}

export interface Channel {
  id: string;
  project_id: string;
  platform: string;
  name: string;
  is_active: boolean;
  has_credentials: boolean;
}

export interface PublishPlatformStatus {
  platform: string;
  enabled: boolean;
  oauth_available: boolean;
  connected: boolean;
}

export interface PublishStatus {
  publish_mode: string;
  live_enabled: boolean;
  configured_oauth_platforms: string[];
  enabled_platforms: string[];
  platforms: PublishPlatformStatus[];
  project_id: string | null;
}

export interface PublishChannelStatus {
  id: string;
  project_id: string;
  platform: string;
  name: string;
  is_active: boolean;
  oauth_connected: boolean;
}

export interface OAuthStartResponse {
  platform: string;
  channel_id: string;
  authorize_url: string;
}

export const api = {
  login: (email: string, password: string) =>
    fetchApi<{ access_token: string; refresh_token: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string, full_name: string) =>
    fetchApi<{ id: string; email: string }>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),
  me: () =>
    fetchApi<{
      id: string;
      email: string;
      full_name: string | null;
      role: string;
      org_id?: string | null;
      org_role?: string | null;
    }>("/api/v1/auth/me"),
  getOrganizations: () => fetchApi<Organization[]>("/api/v1/organizations"),
  createOrganization: (name: string) =>
    fetchApi<Organization>("/api/v1/organizations", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  getProjects: () => fetchApi<Project[]>("/api/v1/projects"),
  getProjectMemory: (projectId: string) => fetchApi<ProjectMemory>(`/api/v1/projects/${projectId}/memory`),
  updateProjectMemory: (projectId: string, body: Omit<ProjectMemory, "project_id" | "memory_context_preview" | "dna_context_preview">) =>
    fetchApi<ProjectMemory>(`/api/v1/projects/${projectId}/memory`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  getProjectDna: (projectId: string) => fetchApi<ProjectDna>(`/api/v1/projects/${projectId}/dna`),
  patchProjectDna: (projectId: string, body: Partial<Omit<ProjectDna, "project_id" | "dna_context_preview">>) =>
    fetchApi<ProjectDna>(`/api/v1/projects/${projectId}/dna`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  searchKnowledge: (body: {
    project_id: string;
    query: string;
    resource_types?: string[];
    limit?: number;
    min_similarity?: number;
  }) =>
    fetchApi<KnowledgeHit[]>("/api/v1/knowledge/search", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getKnowledgeHistory: (projectId: string, resourceType?: string) => {
    const qs = resourceType ? `?resource_type=${encodeURIComponent(resourceType)}` : "";
    return fetchApi<KnowledgeEntry[]>(`/api/v1/knowledge/history/${projectId}${qs}`);
  },
  indexPipelineKnowledge: (pipelineId: string) =>
    fetchApi<{ pipeline_id: string; indexed_count: number }>(`/api/v1/knowledge/index/${pipelineId}`, {
      method: "POST",
    }),
  suggestReuse: (body: { project_id: string; topic: string; pipeline_id?: string; payload?: Record<string, unknown> }) =>
    fetchApi<ReuseSuggestion[]>("/api/v1/reuse/suggest", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  analyzeViral: (body: {
    project_id: string;
    topic: string;
    pipeline_id?: string;
    payload?: Record<string, unknown>;
    include_reuse?: boolean;
  }) =>
    fetchApi<ViralReport>("/api/v1/viral/analyze", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  generateAbVariants: (body: {
    project_id: string;
    topic: string;
    pipeline_id?: string;
    payload?: Record<string, unknown>;
    persist?: boolean;
  }) =>
    fetchApi<AbTestReport>("/api/v1/ab-variants/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getAbVariantsByPipeline: (pipelineId: string) =>
    fetchApi<AbVariantSet[]>(`/api/v1/ab-variants/pipeline/${pipelineId}`),
  scoreContent: (body: {
    project_id: string;
    topic: string;
    pipeline_id?: string;
    payload?: Record<string, unknown>;
    full_pipeline?: boolean;
  }) =>
    fetchApi<ContentScoreReport>("/api/v1/content-score/score", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listSpecialists: (includeUpcoming = false) =>
    fetchApi<SpecialistProfile[]>(`/api/v1/specialists?include_upcoming=${includeUpcoming}`),
  selectSpecialist: (body: {
    project_id: string;
    topic: string;
    pipeline_id?: string;
    payload?: Record<string, unknown>;
  }) =>
    fetchApi<SpecialistSelection>("/api/v1/specialists/select", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  generateMultiContent: (body: {
    project_id: string;
    topic: string;
    pipeline_id?: string;
    payload?: Record<string, unknown>;
    formats?: string[];
    persist?: boolean;
  }) =>
    fetchApi<MultiContentReport>("/api/v1/multi-content/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getMultiContentByPipeline: (pipelineId: string) =>
    fetchApi<TextArtifact[]>(`/api/v1/multi-content/pipeline/${pipelineId}`),
  generateVideoVariants: (body: {
    project_id: string;
    topic: string;
    pipeline_id?: string;
    payload?: Record<string, unknown>;
    platforms?: string[];
    persist?: boolean;
  }) =>
    fetchApi<VideoVariantsReport>("/api/v1/multi-content/video-variants/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getVideoVariantsByPipeline: (pipelineId: string) =>
    fetchApi<VideoPlatformVariant[]>(`/api/v1/multi-content/video-variants/pipeline/${pipelineId}`),
  recordLearning: (body: {
    project_id: string;
    pipeline_id: string;
    topic?: string;
    payload?: Record<string, unknown>;
    persist?: boolean;
  }) =>
    fetchApi<LearningReport>("/api/v1/learning/record", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getLearningInsights: (projectId: string, limit = 50) =>
    fetchApi<LearningReport[]>(`/api/v1/learning/insights?project_id=${projectId}&limit=${limit}`),
  forecastTrend: (body: {
    project_id: string;
    topic: string;
    pipeline_id?: string;
    niche?: string;
    persist?: boolean;
  }) =>
    fetchApi<TrendForecastReport>("/api/v1/trend/forecast", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getProjectGraph: (projectId: string, limit = 500) =>
    fetchApi<GraphView>(`/api/v1/graph/project/${projectId}?limit=${limit}`),
  buildGraph: (pipelineId: string) =>
    fetchApi<{ pipeline_id: string; project_id: string; edge_count: number; node_count: number }>(
      `/api/v1/graph/build/${pipelineId}`,
      { method: "POST" }
    ),
  getExecutiveSummary: (projectId: string) =>
    fetchApi<ExecutiveSummary>(`/api/v1/executive/summary?project_id=${projectId}`),
  createProject: (name: string, description?: string) =>
    fetchApi<Project>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),
  getPipelines: () => fetchApi<Pipeline[]>("/api/v1/pipelines"),
  getPipelineDetail: (id: string) => fetchApi<PipelineDetail>(`/api/v1/pipelines/${id}`),
  cancelPipeline: (id: string) =>
    fetchApi<Pipeline>(`/api/v1/pipelines/${id}/cancel`, { method: "POST" }),
  deletePipeline: (id: string) =>
    fetchApi<void>(`/api/v1/pipelines/${id}`, { method: "DELETE" }),
  getPipelinesByProject: (projectId: string) => fetchApi<Pipeline[]>(`/api/v1/projects/${projectId}/pipelines`),
  createPipeline: (projectId: string, topic: string, workflowName?: string) =>
    fetchApi<Pipeline>(`/api/v1/projects/${projectId}/pipelines`, {
      method: "POST",
      body: JSON.stringify({ topic, workflow_name: workflowName || undefined }),
    }),
  listSchedules: (projectId: string) =>
    fetchApi<PipelineSchedule[]>(`/api/v1/projects/${projectId}/schedules`),
  createSchedule: (
    projectId: string,
    body: {
      name: string;
      topic: string;
      cron_expression: string;
      workflow_name?: string;
      timezone?: string;
    }
  ) =>
    fetchApi<PipelineSchedule>(`/api/v1/projects/${projectId}/schedules`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteSchedule: (projectId: string, scheduleId: string) =>
    fetchApi<void>(`/api/v1/projects/${projectId}/schedules/${scheduleId}`, { method: "DELETE" }),
  getWorkflows: () => fetchApi<WorkflowTemplate[]>("/api/v1/workflows"),
  getWorkflowStepCatalog: () => fetchApi<WorkflowStepCatalogItem[]>("/api/v1/workflows/steps/catalog"),
  createCustomWorkflow: (body: { slug: string; description?: string; steps: string[] }) =>
    fetchApi<WorkflowTemplate>("/api/v1/workflows/custom", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateCustomWorkflow: (slug: string, body: { description?: string; steps?: string[] }) =>
    fetchApi<WorkflowTemplate>(`/api/v1/workflows/custom/${slug}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteCustomWorkflow: (slug: string) =>
    fetchApi<void>(`/api/v1/workflows/custom/${slug}`, { method: "DELETE" }),
  getVideos: () => fetchApi<Video[]>("/api/v1/videos"),
  getLogs: (agent?: string) =>
    fetchApi<LogEntry[]>(`/api/v1/logs${agent ? `?agent=${agent}` : ""}`),
  getAssets: (category?: string) =>
    fetchApi<Asset[]>(`/api/v1/assets${category ? `?category=${category}` : ""}`),
  getStorageStats: () => fetchApi<StorageStats>("/api/v1/assets/storage/stats"),
  getAnalytics: () => fetchApi<AnalyticsOverview>("/api/v1/analytics/overview"),
  getAnalyticsInsights: (limit = 20) =>
    fetchApi<AnalyticsInsight[]>(`/api/v1/analytics/insights?limit=${limit}`),
  applyAnalyticsInsight: (pipelineId: string) =>
    fetchApi<{ ok: boolean; pipeline_id: string }>(`/api/v1/analytics/insights/${pipelineId}/apply`, {
      method: "POST",
    }),
  getPerformance: () => fetchApi<{ by_step: Record<string, Record<string, number>> }>("/api/v1/analytics/performance"),
  getProviderAnalytics: () => fetchApi<ProviderAnalyticsResponse>("/api/v1/analytics/providers"),
  getAgents: () => fetchApi<AgentStats[]>("/api/v1/agents"),
  getAgent: (name: string) => fetchApi<AgentStats>(`/api/v1/agents/${name}`),
  getSystemMetrics: () => fetchApi<SystemMetrics>("/api/v1/metrics/system"),
  getInfrastructureMetrics: () => fetchApi<InfrastructureMetrics>("/api/v1/metrics/infrastructure"),
  getProviderStatus: () => fetchApi<ProviderStatus>("/api/v1/providers/status"),
  getProviderHealth: () => fetchApi<ProvidersHealthResponse>("/api/v1/providers/health"),
  getPrompts: () => fetchApi<PromptSummary[]>("/api/v1/prompts"),
  getPrompt: (id: string) => fetchApi<PromptDetail>(`/api/v1/prompts/${id}`),
  updatePrompt: (id: string, content: string) =>
    fetchApi<PromptDetail>(`/api/v1/prompts/${id}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),
  renderPrompt: (id: string, variables: Record<string, string>) =>
    fetchApi<PromptRenderResult>(`/api/v1/prompts/${id}/render`, {
      method: "POST",
      body: JSON.stringify({ variables }),
    }),
  getAgentModels: () => fetchApi<AgentModelConfig[]>("/api/v1/models"),
  getModelCatalog: () => fetchApi<ModelCatalog>("/api/v1/models/catalog"),
  updateAgentModel: (agent: string, provider: string, model: string) =>
    fetchApi<AgentModelConfig>(`/api/v1/models/${agent}`, {
      method: "PUT",
      body: JSON.stringify({ provider, model }),
    }),
  getCacheStats: () => fetchApi<CacheStats>("/api/v1/cache/stats"),
  purgeAgentCache: (agent: string) =>
    fetchApi<CacheDeleteResult>(`/api/v1/cache/agent/${agent}`, { method: "DELETE" }),
  getCostsOverview: () => fetchApi<CostOverview>("/api/v1/costs/overview"),
  getRecentEvents: (limit = 50) => fetchApi<DomainEvent[]>(`/api/v1/events/recent?limit=${limit}`),
  getPipelineEvents: (pipelineId: string, limit = 100) =>
    fetchApi<DomainEvent[]>(`/api/v1/events/pipelines/${pipelineId}?limit=${limit}`),
  getEventStreamInfo: () => fetchApi<EventStreamInfo>("/api/v1/events/stream/info"),
  getPlatformPlugins: () => fetchApi<PlatformPluginsConfig>("/api/v1/plugins"),
  getPluginMarketplace: () => fetchApi<MarketplacePlugin[]>("/api/v1/plugins/marketplace"),
  getUnifiedMarketplace: (type?: string) =>
    fetchApi<UnifiedMarketplaceCatalog>(
      `/api/v1/marketplace${type ? `?type=${encodeURIComponent(type)}` : ""}`
    ),
  installPlugin: (name: string) =>
    fetchApi<MarketplacePlugin>("/api/v1/plugins/install", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  enablePlugin: (name: string, enabled: boolean) =>
    fetchApi<MarketplacePlugin>(`/api/v1/plugins/${name}/enable`, {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),
  uninstallPlugin: (name: string) =>
    fetchApi<{ ok: boolean; name: string }>(`/api/v1/plugins/${name}`, { method: "DELETE" }),
  getContentSources: () => fetchApi<{ sources: string[] }>("/api/v1/content-sources"),
  getContentSourcesHealth: () => fetchApi<{ sources: ContentSourceHealth[] }>("/api/v1/content-sources/health"),
  getPipelineCollections: (limit = 30) =>
    fetchApi<PipelineCollectionSummary[]>(`/api/v1/content-sources/collections?limit=${limit}`),
  getPipelineCollection: (pipelineId: string) =>
    fetchApi<PipelineAssetCollection>(`/api/v1/content-sources/collections/${pipelineId}`),
  getAiGatewayHealth: () =>
    fetchApi<{ healthy: boolean; url: string; status?: string; service?: string; error?: string }>(
      "/api/v1/providers/ai-gateway/health"
    ),
  searchAssets: (
    filters: {
      q?: string;
      category?: string;
      tag?: string;
      theme?: string;
      game?: string;
      character?: string;
      motion?: string;
      color?: string;
      objects?: string;
      limit?: number;
    } = {}
  ) => {
    const params = new URLSearchParams();
    const { limit = 50, ...rest } = filters;
    for (const [key, value] of Object.entries(rest)) {
      if (value) params.set(key, value);
    }
    params.set("limit", String(limit));
    return fetchApi<Asset[]>(`/api/v1/assets/search?${params.toString()}`);
  },
  tagAsset: (id: string, tags: string[]) =>
    fetchApi<Asset>(`/api/v1/assets/${id}/tags`, {
      method: "POST",
      body: JSON.stringify({ tags }),
    }),
  getAssetPreview: (id: string, expires = 3600) =>
    fetchApi<AssetPreview>(`/api/v1/assets/${id}/preview?expires=${expires}`),
  /** Authenticated stream as object URL (revoke with URL.revokeObjectURL). */
  getAssetContentObjectUrl: async (id: string): Promise<{ url: string; contentType: string }> => {
    const token = getAccessToken();
    const res = await fetch(`${API}/api/v1/assets/${id}/content`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    });
    if (res.status === 401) {
      clearAccessTokens();
      throw new Error("API 401: Faça login novamente para continuar.");
    }
    if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
    const blob = await res.blob();
    return {
      url: URL.createObjectURL(blob),
      contentType: res.headers.get("content-type") || blob.type || "application/octet-stream",
    };
  },
  getAssetIndexStats: () => fetchApi<StorageStats & { indexed_hashes: number }>("/api/v1/assets/index/stats"),
  getChannels: (projectId?: string) =>
    fetchApi<Channel[]>(`/api/v1/channels${projectId ? `?project_id=${projectId}` : ""}`),
  createChannel: (projectId: string, platform: string, name: string, credentials?: object) =>
    fetchApi<Channel>("/api/v1/channels", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, platform, name, credentials }),
    }),
  getPipelineJobs: (pipelineId: string) =>
    fetchApi<{ id: string; step: string; status: string; order: number }[]>(`/api/v1/jobs/pipeline/${pipelineId}`),
  uploadTake: (theme: string, label: string, file: File, projectId?: string) => {
    const form = new FormData();
    form.append("theme", theme);
    form.append("label", label);
    form.append("file", file);
    if (projectId) form.append("project_id", projectId);
    return fetchApi<Asset>("/api/v1/assets/takes/upload", { method: "POST", body: form });
  },
  listApiKeys: (orgId: string) => fetchApi<OrganizationApiKey[]>(`/api/v1/organizations/${orgId}/api-keys`),
  createApiKey: (
    orgId: string,
    body: { name: string; scope?: "read" | "write"; rate_limit_per_minute?: number }
  ) =>
    fetchApi<OrganizationApiKeyCreated>(`/api/v1/organizations/${orgId}/api-keys`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  revokeApiKey: (orgId: string, keyId: string) =>
    fetchApi<void>(`/api/v1/organizations/${orgId}/api-keys/${keyId}`, { method: "DELETE" }),
  listBillingPlans: () => fetchApi<BillingPlan[]>("/api/v1/billing/plans"),
  getOrgBilling: (orgId: string) => fetchApi<OrgBilling>(`/api/v1/organizations/${orgId}/billing`),
  startBillingCheckout: (orgId: string, planSlug: string) =>
    fetchApi<{ checkout_url: string; session_id: string }>(
      `/api/v1/organizations/${orgId}/billing/checkout`,
      { method: "POST", body: JSON.stringify({ plan_slug: planSlug }) }
    ),
  openBillingPortal: (orgId: string) =>
    fetchApi<{ portal_url: string }>(`/api/v1/organizations/${orgId}/billing/portal`, {
      method: "POST",
    }),
  getPublishStatus: (projectId?: string) =>
    fetchApi<PublishStatus>(
      `/api/v1/publish/status${projectId ? `?project_id=${projectId}` : ""}`
    ),
  getPublishChannels: (projectId: string) =>
    fetchApi<PublishChannelStatus[]>(`/api/v1/publish/channels?project_id=${projectId}`),
  startOAuth: (platform: string, projectId: string, channelName?: string) =>
    fetchApi<OAuthStartResponse>(`/api/v1/oauth/${platform}/start`, {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, channel_name: channelName }),
    }),
  disconnectPublishChannel: (channelId: string) =>
    fetchApi<void>(`/api/v1/publish/channels/${channelId}/disconnect`, { method: "POST" }),
};
