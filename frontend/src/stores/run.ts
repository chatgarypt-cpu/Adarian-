import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { api } from '../api/client';
import type { ModelGateway, ModelGatewayDraft, ModelSummary, PageState, RiskComparison, RunErrorReason, RunEvent, RunMetricsResponse, WorldStatus } from '../api/types';

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
  const expandedGatewayIds = ref<string[]>(['env-default']);
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
  const modelsError = ref('');
  const modelToast = ref('');
  const reviewError = ref('');
  const observabilityError = ref('');
  const healthChecking = ref(false);
  const healthSummary = ref({ total: 0, ok: 0, failed: 0, timeout: 0 });
  const reviewRows = ref<RiskComparison[]>([]);
  const batchEvents = ref<RunEvent[]>([]);
  const worldEvents = ref<Record<number, RunEvent[]>>({});
  const runMetrics = ref<RunMetricsResponse | null>(null);
  const runErrors = ref<RunErrorReason[]>([]);
  const activeBatch = ref<{ batchId: string | null; status: 'idle' | 'running' | 'completed' | 'failed'; worlds: WorldStatus[] }>({
    batchId: null,
    status: 'idle',
    worlds: [],
  });
  let toastTimer: number | undefined;
  let pollTimer: ReturnType<typeof setInterval> | undefined;
  let pollInFlight = false;

  const BATCH_STORAGE_KEY = 'adarian:active-batch';

  function saveActiveBatch() {
    if (activeBatch.value.batchId) {
      localStorage.setItem(BATCH_STORAGE_KEY, JSON.stringify({
        batchId: activeBatch.value.batchId,
        savedAt: Date.now(),
      }));
    } else {
      localStorage.removeItem(BATCH_STORAGE_KEY);
    }
  }

  function applyRunStatus(result: { batch_id: string; status: string; worlds: WorldStatus[]; logs: string[] }) {
    activeBatch.value = {
      batchId: result.batch_id,
      status: result.status === 'completed' ? 'completed' : result.status === 'failed' ? 'failed' : 'running',
      worlds: result.worlds,
    };
    logs.value = result.logs.join('\n');
    runState.value = result.worlds.length ? 'populated' : 'empty';
  }

  async function restoreActiveBatch() {
    try {
      const raw = localStorage.getItem(BATCH_STORAGE_KEY);
      if (raw) {
        const data = JSON.parse(raw);
        if (data.batchId && Date.now() - data.savedAt <= 3600000) {
          activeBatch.value.batchId = data.batchId;
          activeBatch.value.status = 'running';
          await refreshStatus({ silent: true });
          return;
        }
        localStorage.removeItem(BATCH_STORAGE_KEY);
      }

      const active = await api.getActiveRun();
      if (active.active && active.batch) {
        applyRunStatus(active.batch);
        await loadObservability();
        saveActiveBatch();
        if (activeBatch.value.status === 'running') startPolling();
      }
    } catch {
      localStorage.removeItem(BATCH_STORAGE_KEY);
    }
  }

  const completedCount = computed(() => activeBatch.value.worlds.filter((world) => world.status === 'completed').length);
  const runningCount = computed(() => activeBatch.value.worlds.filter((world) => world.status === 'running').length);
  const failedCount = computed(() => activeBatch.value.worlds.filter((world) => world.status === 'failed').length);
  const loadedModelCount = computed(() => models.value.length);
  const availableModelCount = computed(() => models.value.filter((model) => model.available).length);
  const selectedModelCount = computed(() => selectedModels.value.length);
  const allModelsSelected = computed(() => models.value.length > 0 && selectedModels.value.length === models.value.length);

  function showModelToast(message: string) {
    modelToast.value = message;
    if (toastTimer) window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      if (modelToast.value === message) modelToast.value = '';
    }, 3600);
  }

  function normalizeModels(gatewayId: string, incoming: ModelSummary[]) {
    return incoming.map((model) => ({
      ...model,
      gatewayId,
      selected: selectedModels.value.includes(model.id) || model.selected,
      available: false,
      latency: model.latency || '',
      advice: '等待可用性检测',
      healthStatus: model.healthStatus ?? 'untested',
      healthMessage: model.healthMessage ?? '',
    }));
  }

  function flattenGatewayModels() {
    models.value = modelGateways.value.flatMap((gateway) => gateway.models);
  }

  function syncSelectedModels(nextSelected = selectedModels.value) {
    selectedModels.value = nextSelected;
    models.value = models.value.map((model) => ({ ...model, selected: selectedModels.value.includes(model.id) }));
    modelGateways.value = modelGateways.value.map((gateway) => ({
      ...gateway,
      models: gateway.models.map((model) => ({ ...model, selected: selectedModels.value.includes(model.id) })),
    }));
  }

  async function hydrate() {
    modelsState.value = 'loading';
    modelsError.value = '';
    try {
      const [gateways, savedConfig] = await Promise.all([api.getModelGateways(), api.getConfig()]);
      modelGateways.value = gateways.map((gateway) => ({ ...gateway, models: gateway.models ?? [] }));
      flattenGatewayModels();
      syncSelectedModels(selectedModels.value.filter((id) => models.value.some((model) => model.id === id)));
      config.value = {
        parallelWorlds: savedConfig.parallel_worlds,
        ticks: savedConfig.ticks,
        batchName: savedConfig.batch_name,
        focuses: savedConfig.focuses,
      };
      modelsState.value = modelGateways.value.length ? 'populated' : 'empty';
      // Restore batch session from localStorage
      await restoreActiveBatch();
    } catch (error) {
      modelsError.value = error instanceof Error ? error.message : '模型配置加载失败';
      modelsState.value = 'error';
    }
  }

  function toggleModel(id: string) {
    const nextSelected = selectedModels.value.includes(id)
      ? selectedModels.value.filter((modelId) => modelId !== id)
      : [...selectedModels.value, id];
    syncSelectedModels(nextSelected);
  }

  function selectAvailableModels() {
    syncSelectedModels(models.value.filter((model) => model.available).map((model) => model.id));
    showModelToast(`已选择 ${selectedModels.value.length} 个可用模型`);
  }

  function toggleAllModels(checked: boolean) {
    syncSelectedModels(checked ? models.value.map((model) => model.id) : []);
  }

  function toggleGateway(id: string) {
    expandedGatewayIds.value = expandedGatewayIds.value.includes(id)
      ? expandedGatewayIds.value.filter((gatewayId) => gatewayId !== id)
      : [...expandedGatewayIds.value, id];
  }

  async function addGateway() {
    if (!gatewayDraft.value.name.trim() || !gatewayDraft.value.baseUrl.trim()) return;
    modelsState.value = 'loading';
    modelsError.value = '';
    try {
      const gateway = await api.createModelGateway(gatewayDraft.value);
      modelGateways.value = [{ ...gateway, models: [] }, ...modelGateways.value];
      expandedGatewayIds.value = [gateway.id, ...expandedGatewayIds.value];
      gatewayDraft.value = {
        name: '',
        baseUrl: '',
        provider: 'openai-compatible',
        apiKey: '',
      };
      flattenGatewayModels();
      modelsState.value = 'populated';
      showModelToast('API 服务已保存，点击识别模型后加载列表');
    } catch (error) {
      modelsError.value = error instanceof Error ? error.message : 'API 服务保存失败';
      modelsState.value = 'error';
    }
  }

  async function loadCatalogModels(gatewayId = 'env-default') {
    modelsState.value = 'loading';
    modelsError.value = '';
    try {
      const catalog = normalizeModels(gatewayId, await api.getModels());
      modelGateways.value = modelGateways.value.map((gateway) =>
        gateway.id === gatewayId ? { ...gateway, models: catalog } : gateway,
      );
      flattenGatewayModels();
      if (selectedModels.value.length === 0) {
        syncSelectedModels(catalog.slice(0, Math.min(2, catalog.length)).map((model) => model.id));
      } else {
        syncSelectedModels();
      }
      modelsState.value = 'populated';
      healthSummary.value = { total: 0, ok: 0, failed: 0, timeout: 0 };
      showModelToast(`已加载 ${catalog.length} 个模型，0 个已检测可用`);
    } catch (error) {
      modelsError.value = error instanceof Error ? error.message : '内置模型加载失败';
      modelsState.value = 'error';
    }
  }

  async function discoverModels(gatewayId: string) {
    modelsState.value = 'loading';
    modelsError.value = '';
    try {
      const discovered = await api.discoverGatewayModels(gatewayId);
      const gatewayModels = normalizeModels(gatewayId, discovered.models);
      modelGateways.value = modelGateways.value.map((gateway) =>
        gateway.id === gatewayId ? { ...gateway, models: gatewayModels, status: 'connected' } : gateway,
      );
      flattenGatewayModels();
      if (selectedModels.value.length === 0) {
        syncSelectedModels(gatewayModels.slice(0, Math.min(2, gatewayModels.length)).map((model) => model.id));
      } else {
        syncSelectedModels();
      }
      modelsState.value = 'populated';
      healthSummary.value = { total: 0, ok: 0, failed: 0, timeout: 0 };
      showModelToast(`已识别 ${gatewayModels.length} 个模型，0 个已检测可用`);
    } catch (error) {
      modelsError.value = error instanceof Error ? error.message : '模型识别失败，可检查 Base URL 是否支持 /models';
      modelsState.value = 'error';
    }
  }

  function updateModels(updater: (model: ModelSummary) => ModelSummary) {
    models.value = models.value.map(updater);
    modelGateways.value = modelGateways.value.map((gateway) => ({
      ...gateway,
      models: gateway.models.map(updater),
    }));
  }

  async function checkSelectedModels() {
    const selected = models.value.filter((model) => selectedModels.value.includes(model.id));
    if (!selected.length) {
      showModelToast('请先勾选需要检测的模型');
      return;
    }
    healthChecking.value = true;
    modelsError.value = '';
    updateModels((model) =>
      selectedModels.value.includes(model.id)
        ? { ...model, healthStatus: 'testing', healthMessage: '', latency: '', advice: '正在请求模型' }
        : model,
    );

    const results: Array<{ id: string; gateway_id?: string; status: 'ok' | 'fail' | 'timeout'; latency_ms?: number | null; message?: string }> = [];

    try {
      await Promise.all(selected.map(async (model) => {
        const gatewayId = model.gatewayId || 'env-default';
        try {
          results.push(...await api.checkModelsHealth([model.id], gatewayId));
        } catch (error) {
          const message = error instanceof Error ? error.message : '模型检测失败';
          const status = message.includes('超时') ? 'timeout' : 'fail';
          results.push({ id: model.id, gateway_id: gatewayId, status, latency_ms: null, message });
        }
      }));
      const resultMap = new Map(results.map((result) => [`${result.gateway_id || 'env-default'}:${result.id}`, result]));
      updateModels((model) => {
        const gatewayId = model.gatewayId || 'env-default';
        const result = resultMap.get(`${gatewayId}:${model.id}`);
        if (!result) return model;
        const ok = result.status === 'ok';
        const timeout = result.status === 'timeout';
        return {
          ...model,
          available: ok,
          healthStatus: ok ? 'ok' : timeout ? 'timeout' : 'fail',
          healthMessage: result.message || (ok ? '请求成功' : '请求失败'),
          latency: result.latency_ms != null ? `${result.latency_ms}ms` : '--',
          advice: ok ? '可用于本次推演' : timeout ? '请求超时，请检查服务地址或模型名' : (result.message || '检测失败'),
        };
      });
      const ok = results.filter((result) => result.status === 'ok').length;
      const timeout = results.filter((result) => result.status === 'timeout').length;
      const failed = results.length - ok - timeout;
      healthSummary.value = { total: results.length, ok, failed, timeout };
      showModelToast(`共检测 ${results.length} 个模型，${ok} 可用，${failed} 失败，${timeout} 超时`);
    } finally {
      healthChecking.value = false;
    }
  }

  async function saveConfig() {
    await api.saveConfig({
      parallel_worlds: config.value.parallelWorlds,
      ticks: config.value.ticks,
      batch_name: config.value.batchName,
      focuses: config.value.focuses,
    });
  }

  async function startRun(seedInput: { seedText: string; seedPath?: string; source?: string }) {
    runState.value = 'loading';
    runError.value = '';
    try {
      await saveConfig();
      const selected = selectedModels.value.length ? selectedModels.value : models.value.filter((model) => model.available).slice(0, config.value.parallelWorlds).map((model) => model.id);
      const result = await api.startRun({
        seed_text: seedInput.seedText,
        seed_path: seedInput.source === 'file' ? seedInput.seedPath ?? '' : '',
        models: selected,
        tag: config.value.batchName,
        config: {
          parallel_worlds: config.value.parallelWorlds,
          ticks: config.value.ticks,
          batch_name: config.value.batchName,
          focuses: config.value.focuses,
        },
      });
      applyRunStatus(result);
      await loadObservability();
      saveActiveBatch();
      startPolling();
    } catch (error) {
      runError.value = error instanceof Error ? error.message : '启动推演失败';
      runState.value = 'error';
    }
  }

  async function refreshStatus(options: { silent?: boolean } = {}) {
    if (!activeBatch.value.batchId) return;
    if (!options.silent) runState.value = 'loading';
    runError.value = '';
    try {
      const result = await api.getRunStatus(activeBatch.value.batchId);
      applyRunStatus(result);
      await loadObservability();
      saveActiveBatch();
      // Start auto-poll when batch is running
      if (activeBatch.value.status === 'running') startPolling();
    } catch (error) {
      runError.value = error instanceof Error ? error.message : '运行状态读取失败';
      runState.value = 'error';
    }
  }

  async function _doPoll() {
    if (!activeBatch.value.batchId || activeBatch.value.status !== 'running') return;
    if (pollInFlight) return;
    pollInFlight = true;
    try {
      const result = await api.getRunStatus(activeBatch.value.batchId);
      applyRunStatus(result);
      await loadObservability();
      saveActiveBatch();
      // Stop polling when batch finishes
      if (result.status !== 'running') stopPolling();
    } catch (error) {
      // Poll errors are silent — network hiccups shouldn't stop polling
      runError.value = error instanceof Error ? error.message : '运行状态轮询失败';
    } finally {
      pollInFlight = false;
    }
  }

  function startPolling() {
    stopPolling();
    if (activeBatch.value.status === 'running') {
      pollTimer = setInterval(_doPoll, 5000);
      void _doPoll();
    }
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = undefined;
    }
  }

  async function loadReview() {
    if (!activeBatch.value.batchId) {
      await restoreActiveBatch();
      if (!activeBatch.value.batchId) {
        reviewRows.value = [];
        reviewState.value = 'empty';
        return;
      }
    }
    reviewState.value = 'loading';
    reviewError.value = '';
    try {
      const result = await api.getReview(activeBatch.value.batchId);
      reviewRows.value = result.rows;
      reviewState.value = result.rows.length ? 'populated' : 'empty';
    } catch (error) {
      reviewError.value = error instanceof Error ? error.message : '审查结果读取失败';
      reviewState.value = 'error';
    }
  }

  async function loadObservability() {
    if (!activeBatch.value.batchId) {
      batchEvents.value = [];
      worldEvents.value = {};
      runMetrics.value = null;
      runErrors.value = [];
      return;
    }
    observabilityError.value = '';
    try {
      const batchId = activeBatch.value.batchId;
      const [events, metrics, errors] = await Promise.all([
        api.getBatchEvents(batchId),
        api.getRunMetrics(batchId),
        api.getRunErrors(batchId),
      ]);
      batchEvents.value = events.events;
      runMetrics.value = metrics;
      runErrors.value = errors.errors;
      const pairs = await Promise.all(activeBatch.value.worlds.map(async (_world, index) => {
        try {
          const response = await api.getWorldEvents(batchId, index);
          return [index, response.events] as const;
        } catch {
          return [index, []] as const;
        }
      }));
      worldEvents.value = Object.fromEntries(pairs);
    } catch (error) {
      observabilityError.value = error instanceof Error ? error.message : '运行事件读取失败';
    }
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
    modelsError,
    modelToast,
    reviewError,
    observabilityError,
    healthChecking,
    healthSummary,
    reviewRows,
    batchEvents,
    worldEvents,
    runMetrics,
    runErrors,
    activeBatch,
    completedCount,
    runningCount,
    failedCount,
    loadedModelCount,
    availableModelCount,
    selectedModelCount,
    allModelsSelected,
    hydrate,
    toggleModel,
    toggleGateway,
    addGateway,
    loadCatalogModels,
    discoverModels,
    checkSelectedModels,
    selectAvailableModels,
    toggleAllModels,
    saveConfig,
    restoreActiveBatch,
    startRun,
    refreshStatus,
    startPolling,
    stopPolling,
    loadReview,
    loadObservability,
  };
});
