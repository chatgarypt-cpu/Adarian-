<template>
  <section class="panel">
    <div class="panel-head">
      <div class="panel-title">{{ title }}</div>
      <div v-if="note" class="panel-note">{{ note }}</div>
    </div>
    <div class="panel-body">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  note?: string;
}>();
</script>
