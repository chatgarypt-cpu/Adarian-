export type PageState = 'loading' | 'empty' | 'error' | 'populated';
export type ChipVariant = 'ok' | 'warn' | 'bad';

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
  risks: string;
  level: string;
  levelVariant?: ChipVariant;
  status: string;
  statusVariant?: ChipVariant;
  evidence?: string;
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
  task_name: string;
  source: string;
}

export interface SeedResponse {
  id: string;
  seed_id?: string;
  checks: StepCheck[];
}

export interface RunRequest {
  seed_text: string;
  models: string[];
  tag: string;
  base_url?: string;
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
