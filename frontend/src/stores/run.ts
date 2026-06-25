import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { api } from '../api/client';
import type { ModelGateway, ModelGatewayDraft, ModelSummary, PageState, RiskComparison, WorldStatus } from '../api/types';

export const useRunStore = defineStore('run', () => {
  const config = ref({
    parallelWorlds: 3,
    ticks: 5,
    batchName: '校园食品安全_batch',
    focuses: ['风险扩散'],
  });
  const selectedModels = ref<string[]>([]);
  const models = ref<ModelSummary[]>([]);
  const modelGateways = ref<ModelGateway[]>([]);
  const expandedGatewayIds = ref<string[]>(['internal']);
  const modelsState = ref<PageState>('populated');
  const gatewayDraft = ref<ModelGatewayDraft>({
    name: '',
    baseUrl: '',
    provider: 'openai-compatible',
    apiKey: '',
  });
  const runState = ref<PageState>('populated');
  const reviewState = ref<PageState>('populated');
  const reportState = ref<PageState>('populated');
  const logs = ref('');
  const runError = ref('');
  const reviewRows = ref<RiskComparison[]>([]);
  const activeBatch = ref<{ batchId: string | null; status: 'idle' | 'running' | 'completed' | 'failed'; worlds: WorldStatus[] }>({
    batchId: null,
    status: 'idle',
    worlds: [],
  });

  const completedCount = computed(() => activeBatch.value.worlds.filter((world) => world.status === 'completed').length);
  const runningCount = computed(() => activeBatch.value.worlds.filter((world) => world.status === 'running').length);
  const failedCount = computed(() => activeBatch.value.worlds.filter((world) => world.status === 'failed').length);

  async function hydrate() {
    modelsState.value = 'loading';
    const [gateways, catalog, savedConfig] = await Promise.all([api.getModelGateways(), api.getModels(), api.getConfig()]);
    modelGateways.value = gateways.map((gateway) => ({
      ...gateway,
      models: gateway.models.length ? gateway.models : catalog.map((model) => ({ ...model, gatewayId: gateway.id })),
    }));
    models.value = modelGateways.value.flatMap((gateway) => gateway.models);
    selectedModels.value = models.value.filter((model) => model.selected).map((model) => model.id);
    config.value = {
      parallelWorlds: savedConfig.parallel_worlds,
      ticks: savedConfig.ticks,
      batchName: savedConfig.batch_name,
      focuses: savedConfig.focuses,
    };
    modelsState.value = modelGateways.value.length ? 'populated' : 'empty';
  }

  function toggleModel(id: string) {
    selectedModels.value = selectedModels.value.includes(id)
      ? selectedModels.value.filter((modelId) => modelId !== id)
      : [...selectedModels.value, id];
    models.value = models.value.map((model) => ({ ...model, selected: selectedModels.value.includes(model.id) }));
    modelGateways.value = modelGateways.value.map((gateway) => ({
      ...gateway,
      models: gateway.models.map((model) => ({ ...model, selected: selectedModels.value.includes(model.id) })),
    }));
  }

  function selectAvailableModels() {
    selectedModels.value = models.value.filter((model) => model.available).map((model) => model.id);
    models.value = models.value.map((model) => ({ ...model, selected: selectedModels.value.includes(model.id) }));
    modelGateways.value = modelGateways.value.map((gateway) => ({
      ...gateway,
      models: gateway.models.map((model) => ({ ...model, selected: selectedModels.value.includes(model.id) })),
    }));
  }

  function toggleGateway(id: string) {
    expandedGatewayIds.value = expandedGatewayIds.value.includes(id)
      ? expandedGatewayIds.value.filter((gatewayId) => gatewayId !== id)
      : [...expandedGatewayIds.value, id];
  }

  async function addGateway() {
    if (!gatewayDraft.value.name.trim() || !gatewayDraft.value.baseUrl.trim()) return;
    modelsState.value = 'loading';
    const gateway = await api.createModelGateway(gatewayDraft.value);
    modelGateways.value = [gateway, ...modelGateways.value];
    expandedGatewayIds.value = [gateway.id, ...expandedGatewayIds.value];
    gatewayDraft.value = {
      name: '',
      baseUrl: '',
      provider: 'openai-compatible',
      apiKey: '',
    };
    modelsState.value = 'populated';
  }

  async function discoverModels(gatewayId: string) {
    modelsState.value = 'loading';
    const discovered = await api.discoverGatewayModels(gatewayId);
    modelGateways.value = modelGateways.value.map((gateway) =>
      gateway.id === gatewayId ? { ...gateway, models: discovered.models } : gateway,
    );
    models.value = modelGateways.value.flatMap((gateway) => gateway.models);
    modelsState.value = 'populated';
  }

  async function saveConfig() {
    await api.saveConfig({
      parallel_worlds: config.value.parallelWorlds,
      ticks: config.value.ticks,
      batch_name: config.value.batchName,
      focuses: config.value.focuses,
    });
  }

  async function startRun(seedText: string) {
    runState.value = 'loading';
    runError.value = '';
    await saveConfig();
    const selected = selectedModels.value.length ? selectedModels.value : models.value.filter((model) => model.available).slice(0, config.value.parallelWorlds).map((model) => model.id);
    const result = await api.startRun({
      seed_text: seedText,
      models: selected,
      tag: config.value.batchName,
      config: {
        parallel_worlds: config.value.parallelWorlds,
        ticks: config.value.ticks,
        batch_name: config.value.batchName,
        focuses: config.value.focuses,
      },
    });
    activeBatch.value = {
      batchId: result.batch_id,
      status: result.status === 'completed' ? 'completed' : result.status === 'failed' ? 'failed' : 'running',
      worlds: result.worlds,
    };
    logs.value = result.logs.join('\n');
    runState.value = result.worlds.length ? 'populated' : 'empty';
  }

  async function refreshStatus() {
    if (!activeBatch.value.batchId) return;
    runState.value = 'loading';
    const result = await api.getRunStatus(activeBatch.value.batchId);
    activeBatch.value = {
      batchId: result.batch_id,
      status: result.status === 'completed' ? 'completed' : result.status === 'failed' ? 'failed' : 'running',
      worlds: result.worlds,
    };
    logs.value = result.logs.join('\n');
    runState.value = result.worlds.length ? 'populated' : 'empty';
  }

  async function loadReview() {
    if (!activeBatch.value.batchId) {
      reviewRows.value = [];
      reviewState.value = 'empty';
      return;
    }
    reviewState.value = 'loading';
    const result = await api.getReview(activeBatch.value.batchId);
    reviewRows.value = result.rows;
    reviewState.value = result.rows.length ? 'populated' : 'empty';
  }

  return {
    config,
    selectedModels,
    models,
    modelGateways,
    expandedGatewayIds,
    gatewayDraft,
    modelsState,
    runState,
    reviewState,
    reportState,
    logs,
    runError,
    reviewRows,
    activeBatch,
    completedCount,
    runningCount,
    failedCount,
    hydrate,
    toggleModel,
    toggleGateway,
    addGateway,
    discoverModels,
    selectAvailableModels,
    saveConfig,
    startRun,
    refreshStatus,
    loadReview,
  };
});
