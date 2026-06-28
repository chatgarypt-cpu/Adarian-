import type {
  BatchSummary,
  ActiveRunResponse,
  ActiveReportJobResponse,
  AppendixMode,
  ConfigResponse,
  GatewayDiscoverResponse,
  ModelHealthResult,
  ModelGateway,
  ModelGatewayDraft,
  ModelSummary,
  ReportJobResponse,
  ReportResponse,
  ReportSkill,
  ReportVersion,
  ReportViewResponse,
  RiskReviewResponse,
  RunErrorsResponse,
  RunEventsResponse,
  RunMetricsResponse,
  RunRequest,
  RunStatusResponse,
  SeedRequest,
  SeedResponse,
  SettingsResponse,
  WorldEventsResponse,
  WorldListResponse,
  WorldLogResponse,
  WorldSummaryResponse,
  WorldTicksResponse,
  StatsResponse,
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

const CLIENT_SESSION_KEY = 'adarian:client-session-id';

function clientSessionId() {
  let id = window.localStorage.getItem(CLIENT_SESSION_KEY);
  if (!id) {
    id = `web_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
    window.localStorage.setItem(CLIENT_SESSION_KEY, id);
  }
  return id;
}

async function jsonRequest<T>(url: string, options: RequestInit = {}, timeoutMs = 15000): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        'X-Adarian-Client-Session': clientSessionId(),
        ...(options.headers ?? {}),
      },
      ...options,
      signal: controller.signal,
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    if (!response.ok) {
      throw new ApiError(data.message ?? response.statusText, data.code, data.details);
    }
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('请求超时，请检查服务地址或网络连通性', 'REQUEST_TIMEOUT', { url, timeoutMs });
    }
    throw new ApiError(error instanceof Error ? error.message : '请求失败', 'NETWORK_ERROR', { url });
  } finally {
    window.clearTimeout(timer);
  }
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
    return jsonRequest(`/api/model-gateways/${encodeURIComponent(gatewayId)}/discover-models`, { method: 'POST' }, 15000);
  },
  checkModelsHealth(models: string[], gatewayId = 'env-default'): Promise<ModelHealthResult[]> {
    return jsonRequest('/api/models/health', {
      method: 'POST',
      body: JSON.stringify({ models, gateway_id: gatewayId }),
    }, 15000);
  },
  startRun(payload: RunRequest): Promise<RunStatusResponse> {
    return jsonRequest('/api/run', { method: 'POST', body: JSON.stringify({ ...payload, client_session_id: clientSessionId() }) });
  },
  getRunStatus(batchId: string): Promise<RunStatusResponse> {
    return jsonRequest(`/api/run/${encodeURIComponent(batchId)}/status`);
  },
  getActiveRun(): Promise<ActiveRunResponse> {
    return jsonRequest(`/api/run/active?client_session_id=${encodeURIComponent(clientSessionId())}`);
  },
  getBatchEvents(batchId: string): Promise<RunEventsResponse> {
    return jsonRequest(`/api/run/${encodeURIComponent(batchId)}/events?scope=batch`);
  },
  getRunMetrics(batchId: string): Promise<RunMetricsResponse> {
    return jsonRequest(`/api/run/${encodeURIComponent(batchId)}/metrics`);
  },
  getRunErrors(batchId: string): Promise<RunErrorsResponse> {
    return jsonRequest(`/api/run/${encodeURIComponent(batchId)}/errors`);
  },
  getWorlds(batchId: string): Promise<WorldListResponse> {
    return jsonRequest(`/api/run/${encodeURIComponent(batchId)}/worlds`);
  },
  getWorldSummary(batchId: string, worldIndex: number): Promise<WorldSummaryResponse> {
    return jsonRequest(`/api/run/${encodeURIComponent(batchId)}/worlds/${worldIndex}/summary`);
  },
  getWorldTicks(batchId: string, worldIndex: number): Promise<WorldTicksResponse> {
    return jsonRequest(`/api/run/${encodeURIComponent(batchId)}/worlds/${worldIndex}/ticks`);
  },
  getWorldLog(batchId: string, worldIndex: number): Promise<WorldLogResponse> {
    return jsonRequest(`/api/run/${encodeURIComponent(batchId)}/worlds/${worldIndex}/log`);
  },
  getWorldEvents(batchId: string, worldIndex: number): Promise<WorldEventsResponse> {
    return jsonRequest(`/api/run/${encodeURIComponent(batchId)}/worlds/${worldIndex}/events`);
  },
  getReview(batchId: string): Promise<RiskReviewResponse> {
    return jsonRequest(`/api/review/${encodeURIComponent(batchId)}`);
  },
  generateReport(batchId: string, type: string, audience: string): Promise<ReportResponse> {
    return jsonRequest('/api/report', { method: 'POST', body: JSON.stringify({ batch_id: batchId, type, audience, client_session_id: clientSessionId(), allow_partial: true }) }, 120000);
  },
  createReportJob(payload: {
    batch_id: string;
    versions: ReportVersion[];
    appendix_mode: AppendixMode;
    allow_partial: boolean;
    skill_id?: string;
    gateway_id?: string;
    model_id?: string;
    temperature?: number;
    max_tokens?: number;
  }): Promise<ReportJobResponse> {
    return jsonRequest('/api/report/jobs', {
      method: 'POST',
      body: JSON.stringify({ ...payload, client_session_id: clientSessionId() }),
    }, 15000);
  },
  getReportJobStatus(jobId: string): Promise<ReportJobResponse> {
    return jsonRequest(`/api/report/jobs/${encodeURIComponent(jobId)}/status`);
  },
  getActiveReportJob(): Promise<ActiveReportJobResponse> {
    return jsonRequest(`/api/report/jobs/active?client_session_id=${encodeURIComponent(clientSessionId())}`);
  },
  getReportSkills(): Promise<ReportSkill[]> {
    return jsonRequest('/api/report/skills');
  },
  getReportView(jobId: string, fileId: string): Promise<ReportViewResponse> {
    return jsonRequest(`/api/report/jobs/${encodeURIComponent(jobId)}/view/${encodeURIComponent(fileId)}`);
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
  getStats(): Promise<StatsResponse> {
    return jsonRequest('/api/stats');
  },
};
