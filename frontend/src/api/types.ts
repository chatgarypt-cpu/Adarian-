export type PageState = 'loading' | 'empty' | 'error' | 'populated';
export type ChipVariant = 'ok' | 'warn' | 'bad';
export type EventTone = 'ok' | 'warn' | 'bad' | 'run';

export interface StepCheck {
  label: string;
  note: string;
  status: 'passed' | 'suggested' | 'pending';
}

export interface ModelSummary {
  id: string;
  gatewayId?: string;
  name: string;
  description: string;
  selected: boolean;
  available: boolean;
  latency?: string;
  advice: string;
  healthStatus?: 'untested' | 'testing' | 'ok' | 'fail' | 'timeout';
  healthMessage?: string;
}

export interface ModelGateway {
  id: string;
  name: string;
  baseUrl: string;
  provider: 'openai-compatible' | 'minimax' | 'deepseek' | 'custom';
  status: 'connected' | 'partial' | 'offline';
  note: string;
  models: ModelSummary[];
  hasApiKey?: boolean;
  source?: 'env' | 'user';
  keyStorageMode?: string;
}

export interface ModelGatewayDraft {
  name: string;
  baseUrl: string;
  provider: ModelGateway['provider'];
  apiKey: string;
}

export interface GatewayDiscoverResponse {
  gateway_id: string;
  models: ModelSummary[];
  latency_ms: number;
}

export interface ModelHealthResult {
  id: string;
  gateway_id?: string;
  status: 'ok' | 'fail' | 'timeout';
  latency_ms?: number | null;
  message?: string;
}

export interface WorldStatus {
  id: string;
  round: string;
  model: string;
  status: 'completed' | 'running' | 'failed' | 'pending' | 'cancelled';
  raw_status?: string;
  phase?: string;
  elapsed_seconds?: number | null;
  rows: Array<{ label: string; value: string; tone?: 'ok' | 'warn' | 'bad' }>;
  errorSummary?: string;
  logTail?: string;
}

export interface BatchSummary {
  batchId: string;
  name: string;
  createdAt: string;
  status: 'running' | 'completed' | 'failed' | 'pending';
  risk: string;
}

export interface RiskComparison {
  world: string;
  batchId?: string;
  worldIndex?: number;
  risks: string;
  level: string;
  levelVariant?: ChipVariant;
  status: string;
  statusVariant?: ChipVariant;
  evidence?: string;
  evidenceTail?: string[];
  entities?: number;
  opinions?: number;
}

export interface RiskReviewResponse {
  batch_id: string;
  complete: boolean;
  rows: RiskComparison[];
}

export interface ReportFile {
  id: string;
  version?: 'A' | 'B' | 'C';
  appendix?: 'none' | 'included' | 'data' | 'export';
  name: string;
  url: string;
  path?: string;
  format?: 'md' | 'pdf' | 'docx' | 'html' | 'json' | 'unknown';
  previewable?: boolean;
  downloadable?: boolean;
  internal?: boolean;
  state?: 'ready' | 'planned' | 'failed';
  label?: string;
  note?: string;
  source_view_id?: string;
  size_bytes?: number | null;
}

export type ReportJobStatus = 'idle' | 'running' | 'completed' | 'blocked' | 'failed';
export type ReportUiState = 'setup' | 'generating' | 'report' | 'failed' | 'blocked';
export type ReportVersion = 'A' | 'B' | 'C';
export type AppendixMode = 'none' | 'included' | 'both';

export interface ReportAuditSummary {
  fatal: number;
  high: number;
  medium: number;
  passed: number;
  blocked_reasons: string[];
}

export interface ReportJobResponse {
  job_id: string;
  report_id?: string;
  batch_id: string;
  status: ReportJobStatus;
  ui_state?: ReportUiState;
  progress: number;
  current_step: string;
  events?: ReportEvent[];
  selected_versions: ReportVersion[];
  version?: ReportVersion;
  appendix_mode: AppendixMode;
  partial: boolean;
  completed_worlds_count: number;
  failed_worlds_count: number;
  skill_id: string;
  model: { resolved_from: 'payload' | 'settings' | 'env' | 'missing'; gateway_id?: string; model_id?: string };
  files: ReportFile[];
  artifacts?: ReportArtifact[];
  report_view?: NativeReportView | null;
  appendix_b: {
    available: boolean;
    path?: string;
    worlds_count: number;
    confirmed_risks: number;
    preview: Record<string, unknown>;
  };
  audit_summary: ReportAuditSummary;
  error_code?: string;
  error_message?: string;
}

export interface ActiveReportJobResponse {
  active: boolean;
  job: ReportJobResponse | null;
}

export interface ReportResponse {
  report_id: string;
  batch_id: string;
  status?: ReportJobStatus;
  files: ReportFile[];
}

export interface ReportSkill {
  id: string;
  label: string;
  description: string;
  dir: string;
}

export interface ReportViewBlock {
  type: 'paragraph' | 'list' | 'preformatted' | 'callout';
  text?: string;
  items?: string[];
  title?: string;
  tone?: 'info' | 'warn' | 'good' | 'bad';
}

export interface ReportViewSection {
  id?: string;
  heading: string;
  eyebrow?: string;
  kind?: 'summary' | 'judgement' | 'risk' | 'countermeasure' | 'appendix';
  blocks: ReportViewBlock[];
  children?: ReportViewSection[];
}

export interface ReportKpi {
  label: string;
  value: string;
  note?: string;
  tone?: 'good' | 'warn' | 'bad' | 'info';
}

export interface ReportAppendixView {
  mode: 'hidden' | 'summary' | 'references';
  event_name: string;
  worlds_count: number;
  confirmed_risks: number;
  risk_distribution?: string;
  references: string[];
}

export interface ReportQualityItem {
  label: string;
  status: 'passed' | 'warning' | 'blocked';
  detail: string;
}

export interface NativeReportView {
  id: string;
  job_id: string;
  batch_id: string;
  version: ReportVersion;
  title: string;
  subtitle: string;
  generated_at?: string;
  source: {
    batch_id: string;
    completed_worlds: number;
    failed_worlds: number;
    dataset_ready: boolean;
    model: string;
    skill_id: string;
  };
  kpis: ReportKpi[];
  sections: ReportViewSection[];
  appendix: ReportAppendixView;
  quality: ReportQualityItem[];
}

export interface ReportArtifact {
  id: string;
  label: string;
  format: 'md' | 'html' | 'docx' | 'pdf' | 'json' | 'unknown';
  state: 'ready' | 'planned' | 'failed';
  previewable: boolean;
  downloadable: boolean;
  url?: string;
  size_bytes?: number | null;
  source_view_id?: string;
  note?: string;
}

export interface ReportEvent {
  label: string;
  detail: string;
  status: 'done' | 'current' | 'pending';
  at?: string;
}

export interface ReportViewResponse {
  file_id: string;
  name: string;
  format: ReportFile['format'];
  version: string;
  appendix: string;
  preview_supported: boolean;
  message?: string;
  title: string;
  sections: ReportViewSection[];
  raw_available: boolean;
}

export interface SystemCheck {
  label: string;
  status: 'ok' | 'failed' | 'pending';
  message: string;
}

export interface SettingsResponse {
  maxConcurrent: number;
  outputDir: string;
  retentionDays: number;
  technicalMode: boolean;
  report_gateway_id: string;
  report_model_id: string;
  report_temperature: number;
  report_max_tokens: number;
  report_skill_id: string;
  systemChecks?: SystemCheck[];
}

export interface ConfigResponse {
  parallel_worlds: number;
  ticks: number;
  batch_name: string;
  focuses: string[];
  pending_fields?: string[];
}

export interface SeedRequest {
  seed_text: string;
  seed_path?: string;
  task_name: string;
  source: string;
}

export interface SeedResponse {
  id: string;
  seed_id?: string;
  source?: string;
  seed_path?: string;
  content?: string;
  checks: StepCheck[];
}

export interface RunRequest {
  seed_text: string;
  seed_path?: string;
  models: string[];
  tag: string;
  base_url?: string;
  client_session_id?: string;
  config: {
    parallel_worlds: number;
    ticks: number;
    batch_name: string;
    focuses: string[];
  };
}

export interface RunStatusResponse {
  batch_id: string;
  status: 'running' | 'completed' | 'failed' | 'pending';
  raw_status?: string;
  all_completed: boolean;
  worlds: WorldStatus[];
  logs: string[];
}

export interface ActiveRunResponse {
  active: boolean;
  batch: RunStatusResponse | null;
}

export interface RunEvent {
  id: string;
  scope: 'batch' | 'world';
  kind: string;
  tone: EventTone;
  title: string;
  message: string;
  timestamp?: string;
  world_index?: number | null;
  model?: string;
  phase?: string;
  meta?: Record<string, unknown>;
}

export interface RunEventsResponse {
  batch_id: string;
  scope: 'batch';
  events: RunEvent[];
}

export interface WorldEventsResponse {
  batch_id: string;
  world_index: number;
  scope: 'world';
  events: RunEvent[];
}

export interface RunMetricsResponse {
  batch_id: string;
  status: string;
  elapsed_seconds?: number | null;
  report_count?: number;
  counts: { total: number; completed: number; running: number; failed: number; pending: number };
  worlds: Array<{
    world_index: number;
    model: string;
    status: string;
    elapsed_seconds?: number | null;
    phase_summary: Record<string, { elapsed_seconds: number }>;
    token_summary: Record<string, unknown>;
  }>;
  tokens: {
    total_tokens: number;
    per_model: Record<string, { total_tokens: number }>;
    per_phase: Record<string, { elapsed_seconds: number; total_tokens?: number; calls?: number; llm_elapsed_seconds?: number }>;
  };
}

export interface RunErrorReason {
  world_index: number;
  model: string;
  reason: string;
  message: string;
  suggestion: string;
}

export interface RunErrorsResponse {
  batch_id: string;
  errors: RunErrorReason[];
}

export interface WorldListResponse {
  batch_id: string;
  worlds: Array<{
    id: string;
    world_index: number;
    model: string;
    status: WorldStatus['status'];
    run_dir: string;
    dataset_path: string;
    elapsed_seconds?: number | null;
    error?: string;
  }>;
}

export interface WorldSummaryResponse {
  id: string;
  batch_id: string;
  world_index: number;
  model: string;
  status: WorldStatus['status'];
  raw_status?: string;
  run_dir: string;
  dataset: {
    available: boolean;
    state: string;
    dataset_path: string;
    event_entities_count: number;
    opinions_count: number;
    risk_verdict: Record<string, unknown>;
    risk_type_classification: Record<string, unknown>;
    source_context: Record<string, unknown>;
    agent_stance_matrix?: unknown[];
  };
  run_meta: Record<string, unknown>;
  elapsed_seconds?: number | null;
  error?: string;
}

export interface WorldTicksResponse {
  world_index: number;
  model: string;
  state: string;
  tick_logs_path: string;
  ticks: Array<Record<string, unknown>>;
}

export interface WorldLogResponse {
  batch_id: string;
  world_index: number;
  state: string;
  path: string;
  lines: string[];
}

export interface StatsResponse {
  todayBatches: number;
}
