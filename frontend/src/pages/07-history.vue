<template>
  <section class="workspace">
    <StateTools v-model="history.pageState" />
    <PageState :state="history.pageState" message="历史任务加载失败">
      <Panel title="历史任务" note="最近批次">
        <div class="mock-note">历史任务来自 SQLite batches 表；复用能力仍为后续版本。</div>
        <table class="table">
          <thead><tr><th>任务名称</th><th>创建时间</th><th>状态</th><th>主要风险</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="batch in history.batches" :key="batch.batchId">
              <td>{{ batch.name }}</td>
              <td>{{ batch.createdAt }}</td>
              <td><Chip :label="statusFor(batch.status).label" :variant="statusFor(batch.status).variant" /></td>
              <td>{{ batch.risk }}</td>
              <td><button class="ghost" type="button" disabled>打开（待接入）</button></td>
            </tr>
          </tbody>
        </table>
      </Panel>
      <Panel title="可复用内容" note="快速启动">
        <div class="grid-3">
          <Card title="复用事件材料" description="待后续 reuse API 接入。" />
          <Card title="复用推演配置" description="待后续 reuse API 接入。" />
          <Card title="打开报告草稿" description="待报告详情 API 接入。" />
        </div>
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import Card from '../components/Card.vue';
import Chip from '../components/Chip.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StateTools from '../components/StateTools.vue';
import { useHistoryStore } from '../stores/history';
import type { BatchSummary, ChipVariant } from '../api/types';

const history = useHistoryStore();
onMounted(() => history.fetchHistory());

function statusFor(status: BatchSummary['status']): { label: string; variant?: ChipVariant } {
  if (status === 'completed') return { label: '已完成', variant: 'ok' };
  if (status === 'running') return { label: '运行中', variant: 'warn' };
  if (status === 'failed') return { label: '失败', variant: 'bad' };
  return { label: '待处理' };
}
</script>
