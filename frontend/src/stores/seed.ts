import { defineStore } from 'pinia';
import { computed, ref, watch } from 'vue';
import { api } from '../api/client';
import type { PageState, StepCheck } from '../api/types';

export const useSeedStore = defineStore('seed', () => {
  const seedText = ref('');
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
      if (result.content) seedText.value = result.content;  // 回填文件内容
      saved.value = true;
      pageState.value = 'populated';
      window.setTimeout(() => {
        saved.value = false;
      }, 4000);
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : '保存失败';
      pageState.value = 'error';
    }
  }

  async function loadFile() {
    if (!seedPath.value.trim()) return;
    pageState.value = 'loading';
    error.value = '';
    try {
      const result = await api.saveSeed({
        seed_text: '',
        seed_path: seedPath.value,
        task_name: taskName.value,
        source: 'file',
      });
      checks.value = result.checks;
      if (result.seed_path) seedPath.value = result.seed_path;
      if (result.content) seedText.value = result.content;
      pageState.value = 'populated';
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : '读取失败';
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
    seedText.value = '';  // 清空文本域，避免 stale 显示
    pageState.value = 'populated';
  }

  // 切换 source 时清空 seedText，防止 file→manual 时显示旧文本
  watch(source, (newVal, oldVal) => {
    if (newVal === 'file' && oldVal !== 'file') {
      seedText.value = '';
    }
  });

  return { seedText, seedPath, taskName, source, checks, pageState, error, saved, isEmpty, canStart, saveSeed, loadFile, useExample, useLocalTest8 };
});
