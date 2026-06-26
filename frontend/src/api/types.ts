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
  name: string;
  url: string;
  path?: string;
}

export interface ReportResponse {
  report_id: string;
  batch_id: string;
  files: ReportFile[];
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
