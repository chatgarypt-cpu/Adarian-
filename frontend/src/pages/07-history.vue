<template>
  <section class="workspace">
    <PageState :state="history.pageState" message="历史任务加载失败">
      <Panel title="历史任务" note="最近批次">
        <div class="status-note">历史任务来自 SQLite batches 表，可打开批次查看真实 world 结果。</div>
        <table class="table">
          <thead><tr><th>任务名称</th><th>Batch ID</th><th>创建时间</th><th>状态</th><th>结果摘要</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="batch in history.batches" :key="batch.batchId">
              <td>{{ batch.name }}</td>
              <td><code>{{ batch.batchId }}</code></td>
              <td>{{ batch.createdAt }}</td>
              <td><Chip :label="statusFor(batch.status).label" :variant="statusFor(batch.status).variant" /></td>
              <td>{{ batch.risk || '待补充' }}</td>
              <td><button class="ghost compact" type="button" @click="openBatch(batch.batchId)">打开</button></td>
            </tr>
          </tbody>
        </table>
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import Chip from '../components/Chip.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import { useHistoryStore } from '../stores/history';
import type { BatchSummary, ChipVariant } from '../api/types';

const history = useHistoryStore();
const router = useRouter();
onMounted(() => history.fetchHistory());

function statusFor(status: BatchSummary['status']): { label: string; variant?: ChipVariant } {
  if (status === 'completed') return { label: '已完成', variant: 'ok' };
  if (status === 'running') return { label: '运行中', variant: 'warn' };
  if (status === 'failed') return { label: '失败', variant: 'bad' };
  return { label: '待处理' };
}

function openBatch(batchId: string) {
  router.push({ path: '/review', query: { batch_id: batchId } });
}
</script>
