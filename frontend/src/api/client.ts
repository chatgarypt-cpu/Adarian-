import type {
  BatchSummary,
  ConfigResponse,
  GatewayDiscoverResponse,
  ModelGateway,
  ModelGatewayDraft,
  ModelSummary,
  ReportResponse,
  RiskReviewResponse,
  RunRequest,
  RunStatusResponse,
  SeedRequest,
  SeedResponse,
  SettingsResponse,
} from './types';

export class ApiError extends Error {
  code: string;
  details: unknown;

  constructor(message: string, code = 'API_ERROR', details: unknown = undefined) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.details = details;
  }
}

async function jsonRequest<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new ApiError(data.message ?? response.statusText, data.code, data.details);
  }
  return data as T;
}

export const api = {
  saveSeed(payload: SeedRequest): Promise<SeedResponse> {
    return jsonRequest('/api/seed', { method: 'POST', body: JSON.stringify(payload) });
  },
  getConfig(): Promise<ConfigResponse> {
    return jsonRequest('/api/config');
  },
  saveConfig(payload: ConfigResponse): Promise<ConfigResponse> {
    return jsonRequest('/api/config', { method: 'POST', body: JSON.stringify(payload) });
  },
  getModels(): Promise<ModelSummary[]> {
    return jsonRequest('/api/models');
  },
  getModelGateways(): Promise<ModelGateway[]> {
    return jsonRequest('/api/model-gateways');
  },
  createModelGateway(payload: ModelGatewayDraft): Promise<ModelGateway> {
    return jsonRequest('/api/model-gateways', { method: 'POST', body: JSON.stringify(payload) });
  },
  discoverGatewayModels(gatewayId: string): Promise<GatewayDiscoverResponse> {
    return jsonRequest(`/api/model-gateways/${encodeURIComponent(gatewayId)}/discover-models`, { method: 'POST' });
  },
  startRun(payload: RunRequest): Promise<RunStatusResponse> {
    return jsonRequest('/api/run', { method: 'POST', body: JSON.stringify(payload) });
  },
  getRunStatus(batchId: string): Promise<RunStatusResponse> {
    return jsonRequest(`/api/run/${encodeURIComponent(batchId)}/status`);
  },
  getReview(batchId: string): Promise<RiskReviewResponse> {
    return jsonRequest(`/api/review/${encodeURIComponent(batchId)}`);
  },
  generateReport(batchId: string, type: string, audience: string): Promise<ReportResponse> {
    return jsonRequest('/api/report', { method: 'POST', body: JSON.stringify({ batch_id: batchId, type, audience }) });
  },
  getHistory(): Promise<BatchSummary[]> {
    return jsonRequest('/api/history');
  },
  getSettings(): Promise<SettingsResponse> {
    return jsonRequest('/api/settings');
  },
  saveSettings(payload: SettingsResponse): Promise<SettingsResponse> {
    return jsonRequest('/api/settings', { method: 'PUT', body: JSON.stringify(payload) });
  },
  ping(): Promise<Response> {
    return fetch('/api/ping');
  },
};
