import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { api } from '../api/client';
import type { ModelGateway, ModelGatewayDraft, ModelSummary, PageState, WorldStatus } from '../api/types';

export const useRunStore = defineStore('run', () => {
  const config = ref({
    parallelWorlds: 3,
    ticks: 40,
    batchName: '校园食品安全_batch',
    focuses: ['风险扩散'],
  });
  const selectedModels = ref<string[]>(['qwen80b', 'minimax']);
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
  const activeBatch = ref<{ batchId: string | null; status: 'idle' | 'running' | 'completed' | 'failed'; worlds: WorldStatus[] }>({
    batchId: 'campus-food',
    status: 'running',
    worlds: [],
  });

  const completedCount = computed(() => activeBatch.value.worlds.filter((world) => world.status === 'completed').length);
  const runningCount = computed(() => activeBatch.value.worlds.filter((world) => world.status === 'running').length);
  const failedCount = computed(() => activeBatch.value.worlds.filter((world) => world.status === 'failed').length);

  async function hydrate() {
    modelGateways.value = await api.getModelGateways();
    models.value = modelGateways.value.flatMap((gateway) => gateway.models);
    activeBatch.value.worlds = await api.getWorlds();
    logs.value = await api.getLogs();
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

  function addGateway() {
    if (!gatewayDraft.value.name.trim() || !gatewayDraft.value.baseUrl.trim()) return;
    const id = `custom-${Date.now()}`;
    const gateway: ModelGateway = {
      id,
      name: gatewayDraft.value.name.trim(),
      baseUrl: gatewayDraft.value.baseUrl.trim(),
      provider: gatewayDraft.value.provider,
      status: 'partial',
      note: 'v1.5.0a mock：已添加服务地址，真实保存和模型识别将在 v1.5.0b 接入后端。',
      hasApiKey: Boolean(gatewayDraft.value.apiKey.trim()),
      models: [],
    };
    modelGateways.value = [gateway, ...modelGateways.value];
    expandedGatewayIds.value = [id, ...expandedGatewayIds.value];
    gatewayDraft.value = {
      name: '',
      baseUrl: '',
      provider: 'openai-compatible',
      apiKey: '',
    };
  }

  function cancelBatch() {
    activeBatch.value.status = 'failed';
    activeBatch.value.worlds = activeBatch.value.worlds.map((world) =>
      world.status === 'running' ? { ...world, status: 'cancelled' as const } : world,
    );
  }

  function retryWorld(worldId: string, newModel?: string) {
    activeBatch.value.worlds = activeBatch.value.worlds.map((world) =>
      world.id === worldId
        ? { ...world, model: newModel ?? world.model, status: 'running' as const, errorSummary: undefined }
        : world,
    );
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
    activeBatch,
    completedCount,
    runningCount,
    failedCount,
    hydrate,
    toggleModel,
    toggleGateway,
    addGateway,
    selectAvailableModels,
    cancelBatch,
    retryWorld,
  };
});
