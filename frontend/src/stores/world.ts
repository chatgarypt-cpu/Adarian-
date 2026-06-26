import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '../api/client';
import type { PageState, RunEvent, WorldLogResponse, WorldSummaryResponse, WorldTicksResponse } from '../api/types';

export const useWorldStore = defineStore('world', () => {
  const state = ref<PageState>('empty');
  const error = ref('');
  const summary = ref<WorldSummaryResponse | null>(null);
  const ticks = ref<WorldTicksResponse | null>(null);
  const log = ref<WorldLogResponse | null>(null);
  const events = ref<RunEvent[]>([]);

  async function load(batchId: string, worldIndex: number) {
    if (!batchId) {
      state.value = 'empty';
      return;
    }
    state.value = 'loading';
    error.value = '';
    try {
      const [summaryResult, ticksResult, logResult, eventsResult] = await Promise.all([
        api.getWorldSummary(batchId, worldIndex),
        api.getWorldTicks(batchId, worldIndex),
        api.getWorldLog(batchId, worldIndex),
        api.getWorldEvents(batchId, worldIndex),
      ]);
      summary.value = summaryResult;
      ticks.value = ticksResult;
      log.value = logResult;
      events.value = eventsResult.events;
      state.value = 'populated';
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'World 详情读取失败';
      state.value = 'error';
    }
  }

  return {
    state,
    error,
    summary,
    ticks,
    log,
    events,
    load,
  };
});
