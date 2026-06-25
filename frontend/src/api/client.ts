import * as mock from './mock';
import type { BatchSummary, ModelGateway, ModelSummary, ReportFile, RiskComparison, SeedRequest, SeedResponse, SettingsResponse, WorldStatus } from './types';

export const api = {
  saveSeed(_payload: SeedRequest): Promise<SeedResponse> {
    return mock.delay(mock.seedResponse);
  },
  getModels(): Promise<ModelSummary[]> {
    return mock.delay(mock.models);
  },
  getModelGateways(): Promise<ModelGateway[]> {
    return mock.delay(mock.modelGateways);
  },
  getWorlds(): Promise<WorldStatus[]> {
    return mock.delay(mock.worlds);
  },
  getLogs(): Promise<string> {
    return mock.delay(mock.logs);
  },
  getReview(): Promise<RiskComparison[]> {
    return mock.delay(mock.riskComparison);
  },
  getReports(): Promise<ReportFile[]> {
    return mock.delay(mock.reportFiles);
  },
  getHistory(): Promise<BatchSummary[]> {
    return mock.delay(mock.history);
  },
  getSettings(): Promise<SettingsResponse> {
    return mock.delay(mock.settings);
  },
  ping(): Promise<Response> {
    return fetch('/api/ping');
  },
};
