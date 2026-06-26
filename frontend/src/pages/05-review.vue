<template>
  <section class="workspace">
    <StateTools v-model="state" />
    <PageState :state="effectiveState" :message="run.reviewError || '审查结果读取失败'">
      <div class="hero-grid">
        <Panel title="主要风险对比" note="多轮结果汇总">
          <div class="status-note">审查结果来自当前 batch 的真实 world 状态与产物路径；不会生成 mock 风险。</div>
          <div class="actions">
            <button class="primary" type="button" :disabled="!run.activeBatch.batchId" @click="run.loadReview">读取审查结果</button>
          </div>
          <div v-if="rows.length === 0" class="empty-inline">暂无可审查结果。完成一次真实推演后，可在这里读取多轮结果对比。</div>
          <table class="table">
            <thead><tr><th>推演轮次</th><th>主要风险</th><th>风险等级</th><th>结果状态</th><th>详情</th></tr></thead>
            <tbody>
              <tr v-for="item in rows" :key="item.world">
                <td>{{ item.world }}</td>
                <td>{{ item.risks }}</td>
                <td><Chip :label="item.level" :variant="item.levelVariant" /></td>
                <td><Chip :label="item.status" :variant="item.statusVariant" /></td>
                <td><button class="ghost compact" type="button" @click="openWorld(item)">查看</button></td>
              </tr>
            </tbody>
          </table>
        </Panel>
        <Panel title="审查结论" note="供报告生成使用">
          <div class="steps">
            <StepLine title="真实数据优先" note="只展示 API 返回的 world 证据。" status="done" :chip="{ label: '真实', variant: 'ok' }" />
            <StepLine title="未完成批次" note="运行中 world 会标记等待。" status="current" :chip="{ label: '等待', variant: 'warn' }" />
            <StepLine title="报告准备" note="需存在 completed world 的 simulation_dataset。" status="pending" :chip="{ label: '条件' }" />
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
import { useRouter } from 'vue-router';
import type { RiskComparison } from '../api/types';
import Card from '../components/Card.vue';
import Chip from '../components/Chip.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StateTools from '../components/StateTools.vue';
import StepLine from '../components/StepLine.vue';
import { useRunStore } from '../stores/run';

const run = useRunStore();
const router = useRouter();
const { reviewState: state, reviewRows } = storeToRefs(run);
const rows = computed(() => reviewRows.value);
const effectiveState = computed(() => (state.value === 'empty' ? 'populated' : state.value));

onMounted(async () => {
  await run.loadReview();
});

function openWorld(item: RiskComparison) {
  const batchId = item.batchId || run.activeBatch.batchId;
  if (!batchId) return;
  router.push({ path: '/world', query: { batch_id: batchId, world_index: String(item.worldIndex ?? 0) } });
}
</script>
