import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '../api/client';
import type { ModelGateway, PageState, ReportSkill, SystemCheck } from '../api/types';

export const useSettingsStore = defineStore('settings', () => {
  const maxConcurrent = ref(3);
  const outputDir = ref('outputs/runs/');
  const retentionDays = ref(30);
  const technicalMode = ref(false);
  const reportGatewayId = ref('');
  const reportModelId = ref('');
  const reportTemperature = ref(0.3);
  const reportMaxTokens = ref(8192);
  const reportSkillId = ref('default_government');
  const reportSkills = ref<ReportSkill[]>([]);
  const modelGateways = ref<ModelGateway[]>([]);
  const systemChecks = ref<SystemCheck[]>([]);
  const pageState = ref<PageState>('populated');
  const error = ref('');
  const saving = ref(false);

  async function loadSettings() {
    pageState.value = 'loading';
    error.value = '';
    try {
      const [data, skills, gateways] = await Promise.all([
        api.getSettings(),
        api.getReportSkills(),
        api.getModelGateways(),
      ]);
      maxConcurrent.value = data.maxConcurrent;
      outputDir.value = data.outputDir;
      retentionDays.value = data.retentionDays;
      technicalMode.value = data.technicalMode;
      reportGatewayId.value = data.report_gateway_id || '';
      reportModelId.value = data.report_model_id || '';
      reportTemperature.value = data.report_temperature ?? 0.3;
      reportMaxTokens.value = data.report_max_tokens ?? 8192;
      reportSkillId.value = data.report_skill_id || 'default_government';
      reportSkills.value = skills;
      modelGateways.value = gateways;
      systemChecks.value = data.systemChecks ?? [];
      pageState.value = 'populated';
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : '系统设置加载失败';
      pageState.value = 'error';
    }
  }

  async function saveSettings() {
    saving.value = true;
    error.value = '';
    try {
      const data = await api.saveSettings({
        maxConcurrent: maxConcurrent.value,
        outputDir: outputDir.value,
        retentionDays: retentionDays.value,
        technicalMode: technicalMode.value,
        report_gateway_id: reportGatewayId.value,
        report_model_id: reportModelId.value.trim(),
        report_temperature: Number(reportTemperature.value),
        report_max_tokens: Number(reportMaxTokens.value),
        report_skill_id: reportSkillId.value,
        systemChecks: systemChecks.value,
      });
      maxConcurrent.value = data.maxConcurrent;
      outputDir.value = data.outputDir;
      retentionDays.value = data.retentionDays;
      technicalMode.value = data.technicalMode;
      reportGatewayId.value = data.report_gateway_id || '';
      reportModelId.value = data.report_model_id || '';
      reportTemperature.value = data.report_temperature ?? 0.3;
      reportMaxTokens.value = data.report_max_tokens ?? 8192;
      reportSkillId.value = data.report_skill_id || 'default_government';
      systemChecks.value = data.systemChecks ?? [];
      pageState.value = 'populated';
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : '系统设置保存失败';
      pageState.value = 'error';
    } finally {
      saving.value = false;
    }
  }

  return {
    maxConcurrent,
    outputDir,
    retentionDays,
    technicalMode,
    reportGatewayId,
    reportModelId,
    reportTemperature,
    reportMaxTokens,
    reportSkillId,
    reportSkills,
    modelGateways,
    systemChecks,
    pageState,
    error,
    saving,
    loadSettings,
    saveSettings,
  };
});
