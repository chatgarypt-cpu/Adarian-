import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '../api/client';
import type { PageState, SystemCheck } from '../api/types';

export const useSettingsStore = defineStore('settings', () => {
  const maxConcurrent = ref(3);
  const outputDir = ref('outputs/runs/');
  const retentionDays = ref(30);
  const technicalMode = ref(false);
  const systemChecks = ref<SystemCheck[]>([]);
  const pageState = ref<PageState>('populated');
  const error = ref('');

  async function loadSettings() {
    pageState.value = 'loading';
    error.value = '';
    try {
      const data = await api.getSettings();
      maxConcurrent.value = data.maxConcurrent;
      outputDir.value = data.outputDir;
      retentionDays.value = data.retentionDays;
      technicalMode.value = data.technicalMode;
      systemChecks.value = data.systemChecks ?? [];
      pageState.value = 'populated';
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : '系统设置加载失败';
      pageState.value = 'error';
    }
  }

  async function saveSettings() {
    pageState.value = 'loading';
    error.value = '';
    try {
      const data = await api.saveSettings({
        maxConcurrent: maxConcurrent.value,
        outputDir: outputDir.value,
        retentionDays: retentionDays.value,
        technicalMode: technicalMode.value,
        systemChecks: systemChecks.value,
      });
      maxConcurrent.value = data.maxConcurrent;
      outputDir.value = data.outputDir;
      retentionDays.value = data.retentionDays;
      technicalMode.value = data.technicalMode;
      systemChecks.value = data.systemChecks ?? [];
      pageState.value = 'populated';
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : '系统设置保存失败';
      pageState.value = 'error';
    }
  }

  return { maxConcurrent, outputDir, retentionDays, technicalMode, systemChecks, pageState, error, loadSettings, saveSettings };
});
