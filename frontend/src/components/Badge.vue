<template>
  <span class="badge" :class="variant">{{ label }}</span>
</template>

<script setup lang="ts">
defineProps<{
  label: string;
  variant?: 'ok' | 'run' | 'warn' | 'bad';
}>();
</script>
