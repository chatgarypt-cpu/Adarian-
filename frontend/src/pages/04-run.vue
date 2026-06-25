<template>
  <section class="workspace">
    <StateTools v-model="run.runState" />
    <PageState :state="effectiveState" message="运行状态读取失败">
      <div class="grid-4">
        <Card :title="String(run.activeBatch.worlds.length)" label="推演轮数" metric />
        <Card :title="String(run.completedCount)" label="已完成" metric />
        <Card :title="String(run.runningCount)" label="运行中" metric />
        <Card :title="String(run.failedCount)" label="失败" metric />
      </div>
      <Panel title="运行监控" note="每轮推演状态">
        <div class="mock-note">运行状态来自 /api/run；cancel/retry 属后续版本，当前不提供假操作。</div>
        <div class="actions">
          <button class="primary" type="button" :disabled="seed.isEmpty || run.selectedModels.length === 0" @click="run.startRun(seed.seedText)">启动真实推演</button>
          <button class="ghost" type="button" :disabled="!run.activeBatch.batchId" @click="run.refreshStatus">刷新状态</button>
        </div>
        <div class="grid-3">
          <WorldCard
            v-for="world in run.activeBatch.worlds"
            :key="world.id"
            :round="world.round"
            :model="world.model"
            :status="badgeFor(world.status)"
            :rows="world.rows"
          />
        </div>
      </Panel>
      <Panel title="运行日志" note="最新动态">
        <LogBox :text="run.logs" />
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import Card from '../components/Card.vue';
import LogBox from '../components/LogBox.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StateTools from '../components/StateTools.vue';
import WorldCard from '../components/WorldCard.vue';
import { useRunStore } from '../stores/run';
import { useSeedStore } from '../stores/seed';

const run = useRunStore();
const seed = useSeedStore();
const effectiveState = computed(() => (run.runState === 'populated' && run.activeBatch.worlds.length === 0 ? 'empty' : run.runState));
const badgeFor = (status: string) => {
  if (status === 'completed') return { label: '已完成', variant: 'ok' as const };
  if (status === 'running') return { label: '运行中', variant: 'run' as const };
  if (status === 'failed') return { label: '失败', variant: 'bad' as const };
  if (status === 'cancelled') return { label: '已取消', variant: 'warn' as const };
  return { label: '排队中', variant: 'warn' as const };
};
</script>
