<template>
  <article class="world">
    <div class="world-top">
      <span>{{ round }}</span>
      <Badge :label="status.label" :variant="status.variant" />
    </div>
    <h3>{{ model }}</h3>
    <div v-for="row in rows" :key="row.label" class="ev">
      <span>{{ row.label }}</span>
      <strong :class="row.tone ? `${row.tone}-text` : ''">{{ row.value }}</strong>
    </div>
  </article>
</template>

<script setup lang="ts">
import Badge from './Badge.vue';

defineProps<{
  round: string;
  model: string;
  status: { label: string; variant?: 'ok' | 'run' | 'warn' | 'bad' };
  rows: Array<{ label: string; value: string; tone?: 'ok' | 'warn' | 'bad' }>;
}>();
</script>
