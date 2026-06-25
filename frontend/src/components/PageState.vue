<template>
  <div v-if="state === 'loading'" class="panel">
    <div class="panel-body" style="display:flex;align-items:center;gap:12px;">
      <div class="spinner" />
      <span class="panel-note">加载中</span>
    </div>
  </div>
  <div v-else-if="state === 'empty'" class="empty">暂无数据</div>
  <div v-else-if="state === 'error'" class="error-box">
    <Chip label="错误" variant="bad" />
    <p>{{ message || '页面数据加载失败' }}</p>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import Chip from './Chip.vue';

defineProps<{
  state: 'loading' | 'empty' | 'error' | 'populated';
  message?: string;
}>();
</script>
