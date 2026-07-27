import { defineStore } from 'pinia';
import { computed, ref, watch } from 'vue';
import { api } from '../api/client';
import type { PageState, StepCheck } from '../api/types';

export const useSeedStore = defineStore('seed', () => {
  const seedText = ref('');
  const seedPath = ref('seeds/test8.txt');
  const taskName = ref('校园食品安全争议推演');
  const source = ref<'manual' | 'file'>('manual');
  const pageState = ref<PageState>('populated');
  const error = ref('');
  const saved = ref(false);
  const savedSignature = ref('');
  const checks = ref<StepCheck[]>([
    { label: '事件材料待保存', note: '填写后保存以完成检查', status: 'pending' },
  ]);

  const isEmpty = computed(() => (source.value === 'file' ? !seedPath.value.trim() : !seedText.value.trim()));
  const canStart = computed(() => source.value === 'file' ? Boolean(seedPath.value.trim()) : Boolean(seedText.value.trim()));
  const currentSignature = computed(() => JSON.stringify([
    source.value,
    source.value === 'file' ? seedPath.value.trim() : seedText.value.trim(),
    taskName.value.trim(),
  ]));
  const isCurrentSaved = computed(() => !isEmpty.value && savedSignature.value === currentSignature.value);

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
      savedSignature.value = currentSignature.value;
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
      savedSignature.value = currentSignature.value;
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

  return { seedText, seedPath, taskName, source, checks, pageState, error, saved, isEmpty, canStart, isCurrentSaved, saveSeed, loadFile, useExample, useLocalTest8 };
});
