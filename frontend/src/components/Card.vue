<template>
  <article class="card" :class="{ metric }">
    <span v-if="metric">{{ label }}</span>
    <strong>{{ title }}</strong>
    <p v-if="description">{{ description }}</p>
    <slot />
  </article>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
  label?: string;
  metric?: boolean;
}>();
</script>
