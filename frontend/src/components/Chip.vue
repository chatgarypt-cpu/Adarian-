<template>
  <span class="chip" :class="variant">{{ label }}</span>
</template>

<script setup lang="ts">
defineProps<{
  label: string;
  variant?: 'ok' | 'warn' | 'bad';
}>();
</script>
