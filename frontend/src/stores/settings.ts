import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '../api/client';
import type { PageState } from '../api/types';

export const useSettingsStore = defineStore('settings', () => {
  const maxConcurrent = ref(3);
  const outputDir = ref('outputs/runs/');
  const retentionDays = ref(30);
  const technicalMode = ref(false);
  const pageState = ref<PageState>('populated');

  async function loadSettings() {
    pageState.value = 'loading';
    const data = await api.getSettings();
    maxConcurrent.value = data.maxConcurrent;
    outputDir.value = data.outputDir;
    retentionDays.value = data.retentionDays;
    technicalMode.value = data.technicalMode;
    pageState.value = 'populated';
  }

  async function saveSettings() {
    pageState.value = 'loading';
    await api.getSettings();
    pageState.value = 'populated';
  }

  return { maxConcurrent, outputDir, retentionDays, technicalMode, pageState, loadSettings, saveSettings };
});
