<template>
  <section class="workspace">
    <PageState :state="effectiveState" :message="run.reviewError || '审查结果读取失败'">
      <div class="review-layout">
        <Panel title="主要风险对比" note="多轮结果汇总">
          <div class="status-note">审查结果来自当前 batch 的真实 world 状态与结构化产物。</div>
          <div class="actions">
            <button class="primary" type="button" :disabled="!run.activeBatch.batchId" @click="run.loadReview()">读取审查结果</button>
          </div>
          <div v-if="rows.length === 0" class="empty-inline">暂无可审查结果。完成一次真实推演后，可在这里读取多轮结果对比。</div>
          <div class="review-table-scroll">
            <table class="table review-table">
              <colgroup>
                <col class="review-col-round" />
                <col class="review-col-risks" />
                <col class="review-col-level" />
                <col class="review-col-status" />
                <col class="review-col-action" />
              </colgroup>
              <thead><tr><th>推演轮次</th><th>主要风险</th><th>风险等级</th><th>结果状态</th><th>详情</th></tr></thead>
              <tbody>
                <tr v-for="item in rows" :key="item.world">
                  <td class="review-nowrap">{{ item.world }}</td>
                  <td class="review-risk-text">{{ item.risks }}</td>
                  <td class="review-nowrap"><Chip :label="item.level" :variant="item.levelVariant" /></td>
                  <td class="review-nowrap"><Chip :label="item.status" :variant="item.statusVariant" /></td>
                  <td class="review-nowrap"><button class="ghost compact" type="button" @click="openWorld(item)">查看</button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </Panel>
        <Panel title="审查结论" note="供报告生成使用">
          <div class="steps">
            <StepLine title="真实数据优先" note="只展示后端返回的推演证据。" status="done" :chip="{ label: '真实', variant: 'ok' }" />
            <StepLine title="未完成批次" note="运行中的样本会标记为等待。" status="current" :chip="{ label: '等待', variant: 'warn' }" />
            <StepLine title="报告准备" note="至少需要一个已完成且数据可用的样本。" status="pending" :chip="{ label: '条件' }" />
          </div>
        </Panel>
      </div>
      <Panel title="结果证据" note="默认展示业务结论">
        <div v-if="rows.length === 0" class="empty-inline">暂无结果证据。</div>
        <div v-else class="grid-3">
          <Card v-for="item in rows" :key="item.world" :title="item.world" :description="item.evidence || item.risks" />
        </div>
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useRoute, useRouter } from 'vue-router';
import type { RiskComparison } from '../api/types';
import Card from '../components/Card.vue';
import Chip from '../components/Chip.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StepLine from '../components/StepLine.vue';
import { useRunStore } from '../stores/run';

const run = useRunStore();
const router = useRouter();
const route = useRoute();
const { reviewState: state, reviewRows } = storeToRefs(run);
const rows = computed(() => reviewRows.value);
const effectiveState = computed(() => (state.value === 'empty' ? 'populated' : state.value));

onMounted(async () => {
  const batchId = typeof route.query.batch_id === 'string' ? route.query.batch_id : '';
  await run.loadReview(batchId);
});

function openWorld(item: RiskComparison) {
  const batchId = item.batchId || run.activeBatch.batchId;
  if (!batchId) return;
  router.push({ path: '/world', query: { batch_id: batchId, world_index: String(item.worldIndex ?? 0) } });
}
</script>

<style scoped>
.review-layout {
  display: grid;
  gap: 16px;
}

.review-table-scroll {
  width: 100%;
  overflow-x: auto;
}

.review-table {
  min-width: 780px;
  table-layout: fixed;
}

.review-col-round {
  width: 112px;
}

.review-col-risks {
  width: auto;
}

.review-col-level,
.review-col-status {
  width: 116px;
}

.review-col-action {
  width: 86px;
}

.review-nowrap {
  white-space: nowrap;
}

.review-risk-text {
  overflow-wrap: anywhere;
  line-height: 1.65;
}
</style>
