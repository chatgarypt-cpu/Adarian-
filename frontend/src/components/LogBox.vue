<template>
  <pre class="logbox">{{ text }}</pre>
</template>

<script setup lang="ts">
defineProps<{
  text: string;
}>();
</script>
