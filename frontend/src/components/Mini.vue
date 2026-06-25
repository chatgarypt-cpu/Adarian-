<template>
  <div class="mini">
    <span>{{ label }}</span>
    <strong :class="toneClass">{{ value }}</strong>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  label: string;
  value: string | number;
  tone?: 'ok' | 'warn' | 'bad';
}>();

const toneClass = computed(() => {
  if (props.tone === 'ok') return 'ok-text';
  if (props.tone === 'warn') return 'warn-text';
  if (props.tone === 'bad') return 'bad-text';
  return '';
});
</script>
