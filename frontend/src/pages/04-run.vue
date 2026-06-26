<template>
  <section class="workspace">
    <StateTools v-model="run.runState" />
    <PageState :state="run.runState" :message="run.runError || '运行状态读取失败'">
      <div class="grid-4">
        <Card :title="String(run.activeBatch.worlds.length)" label="推演轮数" metric />
        <Card :title="String(run.completedCount)" label="已完成" metric />
        <Card :title="String(run.runningCount)" label="运行中" metric />
        <Card :title="String(run.failedCount)" label="失败" metric />
      </div>
      <Panel title="运行监控" note="每轮推演状态">
        <div class="status-note">运行状态来自 /api/run；cancel/retry 属后续版本，当前不提供假操作。</div>
        <div class="actions">
          <button
            class="primary"
            type="button"
            :disabled="!seed.canStart || run.selectedModels.length === 0"
            @click="run.startRun({ seedText: seed.seedText, seedPath: seed.seedPath, source: seed.source })"
          >
            启动真实推演
          </button>
          <button class="ghost" type="button" :disabled="!run.activeBatch.batchId" @click="run.refreshStatus()">刷新状态</button>
        </div>
        <div v-if="run.activeBatch.worlds.length === 0" class="empty-inline">尚未启动推演。请先在模型调度页选择模型，再启动真实推演。</div>
        <div v-if="hasRealBatch" class="run-console">
          <div class="console-head">
            <div>
              <strong>多模型运行台</strong>
              <span v-if="hasRealBatch">来自真实 batch events / world events / raw log。</span>
            </div>
            <Chip v-if="hasRealBatch" :label="selectedConsole.status === 'failed' ? '失败流' : selectedConsole.status === 'completed' ? '结果可用' : selectedConsole.status === 'pending' ? '等待中' : '运行中'" :variant="toneFor(selectedConsole.status)" />
          </div>

          <div class="world-rail" aria-label="选择模型信息流">
            <button
              v-for="world in consoleWorlds"
              :key="world.id"
              :class="['rail-item', world.status, { active: world.id === selectedConsoleId }]"
              type="button"
              @click="selectedConsoleId = world.id"
            >
              <span class="rail-dot" />
              <strong>{{ world.model }}</strong>
              <small>{{ world.phase }}</small>
            </button>
          </div>

          <div v-if="hasRealBatch" class="console-window">
            <div class="window-summary">
              <div>
                <span>当前视图</span>
                <strong>{{ selectedConsole.label }} · {{ selectedConsole.model }}</strong>
              </div>
              <div>
                <span>阶段</span>
                <strong>{{ selectedConsole.phase }}</strong>
              </div>
              <div>
                <span>耗时</span>
                <strong>{{ selectedConsole.elapsed }}</strong>
              </div>
              <div>
                <span>研判</span>
                <strong>{{ selectedConsole.risk }}</strong>
              </div>
            </div>

            <p class="window-copy">{{ selectedConsole.summary }}</p>

            <div class="metric-strip">
              <span v-for="item in selectedMetricItems" :key="item.label">
                <strong>{{ item.value }}</strong>
                {{ item.label }}
              </span>
            </div>

            <div v-if="selectedErrors.length" class="error-reason-list">
              <div v-for="item in selectedErrors" :key="`${item.world_index}-${item.reason}`">
                <strong>{{ item.model }} · {{ item.reason }}</strong>
                <p>{{ item.message }}</p>
                <small>{{ item.suggestion }}</small>
              </div>
            </div>

            <div class="chat-console">
              <div class="chat-status">
                <span>{{ selectedConsole.agents.length }} 个{{ selectedConsole.id === 'overview' ? '平行世界' : '智能体' }}</span>
                <span>{{ selectedConsole.phases.length }} 个{{ selectedConsole.id === 'overview' ? '总控节点' : '阶段动作' }}</span>
                <span>{{ selectedConsole.id === 'overview' ? `${selectedConsole.events.length} 条调度记录` : `${selectedConsole.waterfall.length} 条发言` }}</span>
              </div>

              <div class="chat-controls">
                <div class="stage-tabs" aria-label="预览阶段">
                  <button
                    v-for="stage in stageTabs"
                    :key="stage.id"
                    :class="{ active: activeStage === stage.id }"
                    type="button"
                    @click="setStage(stage.id)"
                  >
                    {{ stage.label }}
                  </button>
                </div>
              </div>

              <div ref="chatFeedEl" class="chat-feed">
                <div
                  v-for="item in visibleChatItems"
                  :key="item.id"
                  :class="['chat-row', item.kind, item.tone]"
                >
                  <div class="chat-avatar">{{ item.avatar }}</div>
                  <div class="chat-bubble">
                    <div class="chat-name">
                      <strong>{{ item.title }}</strong>
                      <span>{{ item.meta }}</span>
                    </div>
                    <p>{{ item.text }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Panel>
      <Panel title="运行日志" :note="run.logs ? '真实执行流' : hasRealBatch ? '等待 raw log' : ''">
        <LogBox :text="displayRunLogs" />
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import Card from '../components/Card.vue';
import Chip from '../components/Chip.vue';
import LogBox from '../components/LogBox.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StateTools from '../components/StateTools.vue';
import { useRunStore } from '../stores/run';
import { useSeedStore } from '../stores/seed';
import type { RunEvent } from '../api/types';

const run = useRunStore();
const seed = useSeedStore();
type StageId = 'all' | 'phase1' | 'phase2' | 'phase3' | 'analysis' | 'phase4' | 'log';
type ChatKind = 'monitor' | 'agent' | 'system';
type ChatTone = 'ok' | 'warn' | 'bad' | 'run';
type ConsoleStatus = 'completed' | 'running' | 'failed' | 'pending';
type ConsoleWorld = {
  id: string;
  model: string;
  label: string;
  status: ConsoleStatus;
  phase: string;
  elapsed: string;
  risk: string;
  summary: string;
  agents: string[];
  phases: Array<{ label: string; action: string; result: string; tone?: ChatTone }>;
  waterfall: Array<{ tick: number; agent: string; role: string; stance: string; comment: string; tone?: ChatTone }>;
  events: Array<{ time: string; title: string; detail: string; tone?: ChatTone }>;
};

const selectedConsoleId = ref('overview');
const activeStage = ref<StageId>('all');
const chatFeedEl = ref<HTMLElement | null>(null);

const hasRealBatch = computed(() => run.activeBatch.worlds.length > 0);
const displayRunLogs = computed(() => run.logs || (hasRealBatch.value ? '暂无 scheduler_batch.log。刷新状态后如果仍为空，可检查 batch_dir。' : ''));
const shortName = (name: string) => name.slice(0, 2);
const toneFor = (status: ConsoleStatus) => {
  if (status === 'completed') return 'ok' as const;
  if (status === 'failed') return 'bad' as const;
  return 'warn' as const;
};

const realConsoleWorlds = computed<ConsoleWorld[]>(() => {
  const counts = run.runMetrics?.counts;
  const overviewEvents = run.batchEvents.map((event) => ({
    time: event.timestamp || '',
    title: event.title,
    detail: event.message,
    tone: event.tone,
  }));
  const overview: ConsoleWorld = {
    id: 'overview',
    model: '总览',
    label: run.activeBatch.batchId || 'Batch',
    status: run.activeBatch.status === 'idle' ? 'pending' : run.activeBatch.status,
    phase: run.activeBatch.status === 'completed' ? '已完成' : run.activeBatch.status === 'failed' ? '存在失败' : run.activeBatch.worlds.some(w => w.phase) ? run.activeBatch.worlds.map(w => `${w.model}:${w.phase}`).join(' / ') : '运行中',
    elapsed: maxElapsedText(),
    risk: counts ? `${counts.completed} 完成 / ${counts.running} 运行 / ${counts.failed} 失败` : `${run.completedCount} 完成 / ${run.runningCount} 运行 / ${run.failedCount} 失败`,
    summary: '总览只显示批次级运行状态、耗时、成功/失败数量和调度日志；具体 world 内容请切换到对应模型。',
    agents: run.activeBatch.worlds.map((world) => world.model),
    phases: run.batchEvents.map((event) => ({
      label: '调度',
      action: event.title,
      result: event.message,
      tone: event.tone,
    })),
    waterfall: [],
    events: overviewEvents,
  };
  return [
    overview,
    ...run.activeBatch.worlds.map((world, index) => {
      const events = run.worldEvents[index] || [];
      const metric = run.runMetrics?.worlds.find((item) => item.world_index === index);
      return {
        id: `world-${index}`,
        model: world.model,
        label: world.round,
        status: world.status === 'cancelled' ? 'pending' : world.status,
        phase: world.phase || phaseFromEvents(events, world.status),
        elapsed: world.elapsed_seconds != null ? `${world.elapsed_seconds}s` : metric?.elapsed_seconds != null ? `${metric.elapsed_seconds}s` : '--',
        risk: world.errorSummary || world.status,
        summary: `真实 world 事件流。模型 ${world.model}，状态 ${world.status}。`,
        agents: uniqueAgents(events),
        phases: events.filter((event) => event.kind !== 'agent').map((event) => ({
          label: phaseLabel(event),
          action: event.title,
          result: event.message,
          tone: event.tone,
        })),
        waterfall: events.filter((event) => event.kind === 'agent').map((event, eventIndex) => ({
          tick: Number(event.meta?.tick ?? 0),
          agent: event.title,
          role: String(event.meta?.role ?? 'agent'),
          stance: String(event.meta?.stance ?? ''),
          comment: event.message,
          tone: event.tone,
        })),
        events: events.map((event) => ({
          time: event.timestamp || '',
          title: event.title || `event_${index}`,
          detail: event.message,
          tone: event.tone,
        })),
      } satisfies ConsoleWorld;
    }),
  ];
});

const consoleWorlds = computed<ConsoleWorld[]>(() => (hasRealBatch.value ? realConsoleWorlds.value : []));
const selectedConsole = computed(() => consoleWorlds.value.find((world) => world.id === selectedConsoleId.value) ?? consoleWorlds.value[0]);
const isOverview = computed(() => selectedConsole.value?.id === 'overview');
const selectedWorldIndex = computed(() => (selectedConsoleId.value.startsWith('world-') ? Number(selectedConsoleId.value.replace('world-', '')) : null));
const selectedMetricItems = computed(() => {
  if (isOverview.value) {
    return [
      { label: '总 Tokens', value: String(run.runMetrics?.tokens.total_tokens ?? 0) },
      { label: '模型数', value: String(run.runMetrics?.counts.total ?? run.activeBatch.worlds.length) },
      { label: '报告文件', value: String(run.runMetrics?.report_count ?? 0) },
      { label: '错误原因', value: String(run.runErrors.length) },
    ];
  }
  const metric = run.runMetrics?.worlds.find((item) => item.world_index === selectedWorldIndex.value);
  const tokenSummary = metric?.token_summary || {};
  return [
    { label: '总 Tokens', value: String(tokenSummary.total_tokens ?? 0) },
    { label: 'LLM 调用', value: String(tokenSummary.total_calls ?? 0) },
    { label: 'Prompt', value: String(tokenSummary.prompt_tokens ?? 0) },
    { label: 'Completion', value: String(tokenSummary.completion_tokens ?? 0) },
  ];
});
const selectedErrors = computed(() => {
  if (isOverview.value) return run.runErrors;
  return run.runErrors.filter((item) => item.world_index === selectedWorldIndex.value);
});

const allStageTabs: Array<{ id: StageId; label: string }> = [
  { id: 'all', label: '全流程' },
  { id: 'phase1', label: 'Phase 1' },
  { id: 'phase2', label: 'Phase 2' },
  { id: 'phase3', label: 'Phase 3' },
  { id: 'analysis', label: '分析层' },
  { id: 'phase4', label: 'Phase 4' },
  { id: 'log', label: '调度' },
];
const overviewStageTabs: Array<{ id: StageId; label: string }> = [
  { id: 'all', label: '全流程' },
  { id: 'log', label: '调度' },
];
const stageTabs = computed(() => (isOverview.value ? overviewStageTabs : allStageTabs));

const stageForPhase = (label: string): StageId => {
  if (label.includes('Phase 1')) return 'phase1';
  if (label.includes('Phase 2')) return 'phase2';
  if (label.includes('Phase 3')) return 'phase3';
  if (label.includes('Phase 4')) return 'phase4';
  if (label.includes('调度')) return 'log';
  return 'analysis';
};

const chatItems = computed(() => {
  const world = selectedConsole.value;
  if (!world) return [];
  const items: Array<{ id: string; stage: StageId; kind: ChatKind; tone: ChatTone; avatar: string; title: string; meta: string; text: string }> = [
    {
      id: `${world.id}-intro`,
      stage: 'all',
      kind: 'monitor',
      tone: 'run',
      avatar: '总控',
      title: '总控 Agent',
      meta: `${world.label} · ${world.model}`,
      text: world.id === 'overview'
        ? `${world.label} 已接入。当前展示跨模型批次态势，只汇总调度、阶段、产出和异常。`
        : `${world.label} 已接入。当前平行世界为 ${world.model}，状态：${world.phase}。`,
    },
  ];

  world.phases.forEach((phase, index) => {
    const stage = stageForPhase(phase.label);
    items.push({
      id: `${world.id}-phase-${index}`,
      stage,
      kind: 'monitor',
      tone: phase.tone || 'run',
      avatar: '总控',
      title: `${phase.label} · ${phase.action}`,
      meta: '阶段播报',
      text: phase.result,
    });
  });

  world.waterfall.forEach((post, index) => {
    items.push({
      id: `${world.id}-post-${index}`,
      stage: 'phase3',
      kind: 'agent',
      tone: post.tone || 'run',
      avatar: shortName(post.agent),
      title: post.agent,
      meta: `Tick ${post.tick} · ${post.role} · ${post.stance}`,
      text: post.comment,
    });
  });

  world.events.forEach((event, index) => {
    items.push({
      id: `${world.id}-event-${index}`,
      stage: 'log',
      kind: 'system',
      tone: event.tone || 'run',
      avatar: event.time.slice(3),
      title: event.title,
      meta: event.time,
      text: event.detail,
    });
  });

  return items;
});

const filteredChatItems = computed(() => (
  activeStage.value === 'all'
    ? chatItems.value
    : chatItems.value.filter((item) => item.stage === activeStage.value || item.stage === 'all')
));
const visibleChatItems = filteredChatItems;

async function scrollChatToLatest() {
  await nextTick();
  if (!chatFeedEl.value) return;
  chatFeedEl.value.scrollTop = chatFeedEl.value.scrollHeight;
}

function setStage(stage: StageId) {
  activeStage.value = stage;
}

watch([selectedConsoleId, activeStage, hasRealBatch], () => {
  if (isOverview.value && activeStage.value !== 'all' && activeStage.value !== 'log') {
    activeStage.value = 'all';
  }
}, { immediate: true });

watch(consoleWorlds, () => {
  if (!consoleWorlds.value.some((world) => world.id === selectedConsoleId.value)) {
    selectedConsoleId.value = consoleWorlds.value[0]?.id || 'overview';
  }
});

function maxElapsedText() {
  const liveValues = run.activeBatch.worlds.map((world) => world.elapsed_seconds).filter((value): value is number => typeof value === 'number');
  const metricValues = run.runMetrics?.worlds.map((world) => world.elapsed_seconds).filter((value): value is number => typeof value === 'number') || [];
  const values = liveValues.length ? liveValues : metricValues;
  return values.length ? `${Math.max(...values)}s` : '--';
}

function phaseFromEvents(events: RunEvent[], status: string) {
  const latestPhase = [...events].reverse().find((event) => event.phase || event.kind.includes('phase'));
  if (latestPhase?.phase) return latestPhase.phase;
  return status;
}

function phaseLabel(event: RunEvent): string {
  if (event.phase) return event.phase;
  if (event.kind.includes('llm')) return 'LLM';
  if (event.kind.includes('error')) return '错误';
  if (event.kind.includes('tick')) return 'Phase 3';
  return '调度';
}

function uniqueAgents(events: RunEvent[]) {
  const agents = events.filter((event) => event.kind === 'agent').map((event) => event.title);
  return [...new Set(agents)];
}

watch(visibleChatItems, scrollChatToLatest, { flush: 'post' });

onBeforeUnmount(() => run.stopPolling());
</script>
