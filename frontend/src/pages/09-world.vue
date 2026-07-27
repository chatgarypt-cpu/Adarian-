<template>
  <section class="workspace">
    <PageState :state="world.state" :message="world.error || 'World 详情读取失败'">
      <div class="grid-4">
        <Card :title="world.summary?.model || '--'" label="模型" metric />
        <Card :title="statusLabel" label="状态" metric />
        <Card :title="String(world.summary?.dataset.event_entities_count ?? 0)" label="事件主体" metric />
        <Card :title="String(world.summary?.dataset.opinions_count ?? 0)" label="立场矩阵" metric />
      </div>

      <Panel title="World 摘要" note="真实产物">
        <div v-if="!world.summary" class="empty-inline">暂无摘要。</div>
        <div v-else class="grid-2">
          <Card title="风险等级" :description="riskLevel" />
          <Card title="风险类型" :description="riskTypes" />
          <Card title="运行目录" :description="world.summary.run_dir || '未记录'" />
          <Card title="耗时" :description="world.summary.elapsed_seconds != null ? `${world.summary.elapsed_seconds}s` : '未记录'" />
        </div>
      </Panel>

      <Panel title="事件流" note="phase / tick / error">
        <div v-if="world.events.length === 0" class="empty-inline">暂无结构化事件。可检查 run.log 是否已生成。</div>
        <div v-else class="event-list">
          <div v-for="event in world.events" :key="event.id" :class="['event-row', event.tone]">
            <strong>{{ event.title }}</strong>
            <span>{{ event.timestamp || event.phase || event.kind }}</span>
            <p>{{ event.message }}</p>
          </div>
        </div>
      </Panel>

      <Panel title="Ticks" note="智能体发言">
        <div v-if="!world.ticks || world.ticks.ticks.length === 0" class="empty-inline">暂无 tick_logs.json。</div>
        <div v-else class="tick-list">
          <details v-for="(tick, index) in world.ticks.ticks" :key="index" :open="index === 0">
            <summary>Tick {{ tick.tick ?? index }} · {{ Array.isArray(tick.entries) ? tick.entries.length : 0 }} 条发言</summary>
            <pre class="json-preview">{{ JSON.stringify(tick.entries ?? tick, null, 2) }}</pre>
          </details>
        </div>
      </Panel>

      <Panel title="运行日志" note="run.log tail">
        <LogBox :text="logText" />
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import Card from '../components/Card.vue';
import LogBox from '../components/LogBox.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import { useRunStore } from '../stores/run';
import { useWorldStore } from '../stores/world';

const route = useRoute();
const run = useRunStore();
const world = useWorldStore();

const batchId = computed(() => String(route.query.batch_id || run.activeBatch.batchId || ''));
const worldIndex = computed(() => Number(route.query.world_index || 0));
const statusLabel = computed(() => world.summary?.status || '--');
const riskLevel = computed(() => {
  const verdict = world.summary?.dataset.risk_verdict || {};
  return String(verdict.label || verdict.level || '待定');
});
const riskTypes = computed(() => {
  const riskType = world.summary?.dataset.risk_type_classification || {};
  const labels = riskType.type_labels;
  return Array.isArray(labels) && labels.length ? labels.join('、') : '暂无风险标签';
});
const logText = computed(() => world.log?.lines.join('\n') || '暂无 run.log。');

async function load() {
  await world.load(batchId.value, worldIndex.value);
}

watch([batchId, worldIndex], load);
onMounted(load);
</script>
