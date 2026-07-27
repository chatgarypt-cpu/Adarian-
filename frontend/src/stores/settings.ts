import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '../api/client';
import type { ModelGateway, PageState, ReportSkill, ReportSkillLocations, SystemCheck } from '../api/types';

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
  const reportSkillLocations = ref<ReportSkillLocations>({ builtin: '', user: '' });
  const modelGateways = ref<ModelGateway[]>([]);
  const systemChecks = ref<SystemCheck[]>([]);
  const pageState = ref<PageState>('populated');
  const error = ref('');
  const saving = ref(false);
  const skillBusy = ref(false);
  const skillError = ref('');

  async function loadSettings() {
    pageState.value = 'loading';
    error.value = '';
    try {
      const [data, skills, locations, gateways] = await Promise.all([
        api.getSettings(),
        api.getReportSkills(),
        api.getReportSkillLocations(),
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
      reportSkillLocations.value = locations;
      modelGateways.value = gateways;
      systemChecks.value = data.systemChecks ?? [];
      pageState.value = 'populated';
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : '系统设置加载失败';
      pageState.value = 'error';
    }
  }

  async function refreshReportSkills() {
    const [skills, locations] = await Promise.all([api.getReportSkills(), api.getReportSkillLocations()]);
    reportSkills.value = skills;
    reportSkillLocations.value = locations;
  }

  async function importReportSkill(file: File, replace = false) {
    skillBusy.value = true;
    skillError.value = '';
    try {
      const skill = await api.importReportSkill(file, replace);
      await refreshReportSkills();
      reportSkillId.value = skill.id;
      return skill;
    } catch (exc) {
      skillError.value = exc instanceof Error ? exc.message : 'Skill 导入失败';
      throw exc;
    } finally {
      skillBusy.value = false;
    }
  }

  async function deleteReportSkill(skillId: string) {
    skillBusy.value = true;
    skillError.value = '';
    try {
      await api.deleteReportSkill(skillId);
      if (reportSkillId.value === skillId) reportSkillId.value = 'default_government';
      await refreshReportSkills();
    } catch (exc) {
      skillError.value = exc instanceof Error ? exc.message : 'Skill 删除失败';
      throw exc;
    } finally {
      skillBusy.value = false;
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
    reportSkillLocations,
    modelGateways,
    systemChecks,
    pageState,
    error,
    saving,
    skillBusy,
    skillError,
    loadSettings,
    saveSettings,
    refreshReportSkills,
    importReportSkill,
    deleteReportSkill,
  };
});
