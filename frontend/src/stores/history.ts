import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '../api/client';
import type { BatchSummary, PageState } from '../api/types';

export const useHistoryStore = defineStore('history', () => {
  const batches = ref<BatchSummary[]>([]);
  const loading = ref(false);
  const pageState = ref<PageState>('populated');

  async function fetchHistory() {
    loading.value = true;
    pageState.value = 'loading';
    batches.value = await api.getHistory();
    pageState.value = batches.value.length ? 'populated' : 'empty';
    loading.value = false;
  }

  return { batches, loading, pageState, fetchHistory };
});
