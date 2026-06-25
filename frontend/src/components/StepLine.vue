<template>
  <div class="step-line" :class="stateClass">
    <div class="dot">{{ markerText }}</div>
    <div>
      <strong>{{ title }}</strong>
      <small>{{ note }}</small>
    </div>
    <Chip v-if="chip" :label="chip.label" :variant="chip.variant" />
    <span v-else />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import Chip from './Chip.vue';

const props = defineProps<{
  title: string;
  note: string;
  marker?: string | number;
  status?: 'done' | 'current' | 'pending';
  chip?: { label: string; variant?: 'ok' | 'warn' | 'bad' };
}>();

const markerText = computed(() => String(props.marker ?? (props.status === 'done' ? '✓' : props.status === 'current' ? '!' : '○')));
const stateClass = computed(() => ({
  done: props.status === 'done',
  current: props.status === 'current',
}));
</script>
