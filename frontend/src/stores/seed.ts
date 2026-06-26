import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { api } from '../api/client';
import type { PageState, StepCheck } from '../api/types';

export const useSeedStore = defineStore('seed', () => {
  const seedText = ref('校园食堂食品安全争议在短视频平台发酵，学生、家长、商家和监管部门形成多方讨论。');
  const seedPath = ref('seeds/test8.txt');
  const taskName = ref('校园食品安全争议推演');
  const source = ref<'manual' | 'file' | 'history'>('manual');
  const pageState = ref<PageState>('populated');
  const error = ref('');
  const saved = ref(false);
  const checks = ref<StepCheck[]>([
    { label: '事件背景已填写', note: '可以进入下一步', status: 'passed' },
    { label: '核心主体识别', note: 'v1.5.0b 暂未接入主体抽取，后续版本启用', status: 'pending' },
    { label: '时间线可补充', note: '建议补充首发时间和官方回应时间', status: 'suggested' },
  ]);

  const isEmpty = computed(() => (source.value === 'file' ? !seedPath.value.trim() : !seedText.value.trim()));
  const canStart = computed(() => source.value === 'file' ? Boolean(seedPath.value.trim()) : Boolean(seedText.value.trim()));

  async function saveSeed() {
    if (isEmpty.value) return;
    pageState.value = 'loading';
    error.value = '';
    try {
      const result = await api.saveSeed({
        seed_text: source.value === 'file' ? '' : seedText.value,
        seed_path: source.value === 'file' ? seedPath.value : '',
        task_name: taskName.value,
        source: source.value,
      });
      checks.value = result.checks;
      if (result.seed_path) seedPath.value = result.seed_path;
      saved.value = true;
      pageState.value = 'populated';
      window.setTimeout(() => {
        saved.value = false;
      }, 3000);
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : '保存失败';
      pageState.value = 'error';
    }
  }

  function useExample(text: string) {
    seedText.value = text;
    source.value = 'manual';
    pageState.value = 'populated';
  }

  function useLocalTest8() {
    source.value = 'file';
    seedPath.value = 'seeds/test8.txt';
    pageState.value = 'populated';
  }

  return { seedText, seedPath, taskName, source, checks, pageState, error, saved, isEmpty, canStart, saveSeed, useExample, useLocalTest8 };
});
