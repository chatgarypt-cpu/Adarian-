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
}

export interface ModelGatewayDraft {
  name: string;
  baseUrl: string;
  provider: ModelGateway['provider'];
  apiKey: string;
}

export interface WorldStatus {
  id: string;
  round: string;
  model: string;
  status: 'completed' | 'running' | 'failed' | 'pending' | 'cancelled';
  rows: Array<{ label: string; value: string; tone?: 'ok' | 'warn' | 'bad' }>;
  errorSummary?: string;
}

export interface BatchSummary {
  batchId: string;
  name: string;
  createdAt: string;
  status: 'running' | 'completed' | 'failed';
  risk: string;
}

export interface RiskComparison {
  world: string;
  risks: string;
  level: string;
  levelVariant?: ChipVariant;
  status: string;
  statusVariant?: ChipVariant;
}

export interface ReportFile {
  id: string;
  name: string;
  url: string;
}

export interface SettingsResponse {
  maxConcurrent: number;
  outputDir: string;
  retentionDays: number;
  technicalMode: boolean;
}

export interface SeedRequest {
  seed_text: string;
  task_name: string;
  source: string;
}

export interface SeedResponse {
  id: string;
  checks: StepCheck[];
}

export interface RunRequest {
  seed_text: string;
  models: string[];
  config: {
    parallel_worlds: number;
    ticks: number;
    batch_name: string;
    focuses: string[];
  };
}

export interface RunResponse {
  batch_id: string;
}
