<template>
  <div v-if="showStateTools" class="state-tools">
    <button
      v-for="item in states"
      :key="item"
      :class="{ active: modelValue === item }"
      type="button"
      @click="$emit('update:modelValue', item)"
    >
      {{ labels[item] }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { PageState } from '../api/types';

defineProps<{
  modelValue: PageState;
}>();

defineEmits<{
  'update:modelValue': [value: PageState];
}>();

const states: PageState[] = ['loading', 'empty', 'error', 'populated'];
const labels: Record<PageState, string> = {
  loading: 'loading',
  empty: 'empty',
  error: 'error',
  populated: 'populated',
};

const showStateTools = computed(() => {
  if (typeof window === 'undefined') return false;
  const params = new URLSearchParams(window.location.search);
  return params.get('debugStates') === '1' || window.localStorage.getItem('adarian:debug-states') === '1';
});
</script>
