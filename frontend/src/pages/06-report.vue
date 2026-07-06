<template>
  <section class="report-workbench" :class="`theme-${theme}`">
    <header class="report-topbar">
      <div>
        <span class="mini-label">REPORT WORKBENCH · REPORT_VIEW</span>
        <h3>报告生成与阅读</h3>
        <p>按现有报告顺序展示，正文读取后端原生 report_view.json；Markdown / HTML 只作为导出格式。</p>
      </div>
      <div class="topbar-actions">
        <div class="job-pill">
          <span :class="['pulse-dot', viewState]" />
          <strong>{{ statusLabel }}</strong>
          <small>{{ statusNote }}</small>
        </div>
        <button v-if="viewState !== 'setup'" class="quiet-action" type="button" @click="resetToSetup">重新设置</button>
        <div class="theme-switch" aria-label="主题切换">
          <button type="button" :class="{ active: theme === 'dark' }" @click="theme = 'dark'">深色</button>
          <button type="button" :class="{ active: theme === 'light' }" @click="theme = 'light'">浅色</button>
        </div>
      </div>
    </header>

    <section v-if="viewState === 'setup'" class="setup-shell" aria-label="报告生成前设置">
      <div class="setup-copy">
        <span class="mini-label">PRE-GENERATION</span>
        <h4>生成前确认</h4>
        <p>这里读取真实 batch / worlds 状态。完成后，阅读界面只保留报告正文、版本切换、附录开关和一个文件出口。</p>
      </div>

      <div class="setup-grid">
        <section class="setup-card primary-card">
          <span>报告来源</span>
          <strong>{{ selectedBatchId || '暂无 batch' }}</strong>
          <select v-model="selectedBatchId" @change="loadWorlds">
            <option v-if="activeBatchId" :value="activeBatchId">当前任务：{{ activeBatchId }}</option>
            <option v-for="batch in history" :key="batch.batchId" :value="batch.batchId">{{ batch.name }} · {{ batch.batchId }}</option>
          </select>
          <dl>
            <div>
              <dt>completed worlds</dt>
              <dd>{{ completedCount }}</dd>
            </div>
            <div>
              <dt>failed worlds</dt>
              <dd>{{ failedCount }}</dd>
            </div>
            <div>
              <dt>dataset</dt>
              <dd>{{ datasetReady ? 'ready' : 'missing' }}</dd>
            </div>
          </dl>
          <label v-if="failedCount" class="check-row">
            <input v-model="allowPartial" type="checkbox" />
            <span>仅基于 completed worlds 生成</span>
          </label>
        </section>

        <section class="setup-card">
          <span>生成版本</span>
          <div class="setup-options">
            <button
              v-for="version in versionOptions"
              :key="version.id"
              type="button"
              :class="{ active: selectedVersion === version.id }"
              @click="selectedVersion = version.id"
            >
              {{ version.id }} 版
              <small>{{ version.intent }}</small>
            </button>
          </div>
        </section>

        <section class="setup-card">
          <span>报告选项</span>
          <div class="setup-options compact-options">
            <button type="button" :class="{ active: appendixMode === 'hidden' }" @click="appendixMode = 'hidden'">不含附录</button>
            <button type="button" :class="{ active: appendixMode === 'summary' }" @click="appendixMode = 'summary'">附录摘要</button>
            <button type="button" :class="{ active: appendixMode === 'references' }" @click="appendixMode = 'references'">引用明细</button>
          </div>
          <p>模型：{{ modelLabel }} · 风格：{{ skillLabel }}</p>
        </section>
      </div>

      <div class="generate-actions">
        <button class="generate-button" type="button" :disabled="!canGenerate" @click="startReport">生成报告</button>
        <small>{{ disableReason || '将创建真实 report job；若模型未配置，会进入阻断态。' }}</small>
      </div>
    </section>

    <section v-else-if="viewState === 'generating'" class="generating-shell" aria-label="报告生成中">
      <div class="generating-head">
        <div>
          <span class="mini-label">GENERATING</span>
          <h4>正在生成报告预览</h4>
          <p>正在轮询真实 report job 状态：读取 dataset、构建附录、生成正文、质检、准备文件出口。</p>
        </div>
        <strong>{{ reportJob?.progress || 0 }}%</strong>
      </div>
      <div class="loading-bar">
        <span :style="{ width: `${reportJob?.progress || 0}%` }" />
      </div>
      <div ref="generationLogRef" class="generation-stream" aria-label="生成过程信息流">
        <article v-for="(event, index) in generationEvents" :key="`${event.label}-${index}`" :class="['generation-event', event.status]">
          <span>{{ String(index + 1).padStart(2, '0') }}</span>
          <div>
            <strong>{{ event.label }}</strong>
            <p>{{ event.detail }}</p>
          </div>
        </article>
      </div>
    </section>

    <section v-else-if="viewState === 'failed' || viewState === 'blocked'" class="failure-shell" aria-label="报告生成失败">
      <span class="mini-label">{{ viewState === 'blocked' ? 'BLOCKED' : 'FAILED' }}</span>
      <h4>{{ viewState === 'blocked' ? '报告生成被阻断' : '报告生成失败' }}</h4>
      <p>{{ reportJob?.error_message || '后端未返回错误原因。' }}</p>
      <button class="generate-button" type="button" @click="resetToSetup">返回生成前设置</button>
    </section>

    <section v-else class="report-toolbar" aria-label="报告控制">
      <div class="toolbar-group version-tabs">
        <span>版本</span>
        <button
          v-for="version in generatedVersions"
          :key="version"
          type="button"
          :class="{ active: selectedVersion === version }"
          @click="selectGeneratedVersion(version)"
        >
          {{ version }} 版
        </button>
      </div>
      <div class="toolbar-group">
        <span>附录</span>
        <button type="button" :class="{ active: appendixMode === 'hidden' }" @click="appendixMode = 'hidden'">隐藏</button>
        <button type="button" :class="{ active: appendixMode === 'summary' }" @click="appendixMode = 'summary'">摘要</button>
        <button type="button" :class="{ active: appendixMode === 'references' }" @click="appendixMode = 'references'">引用</button>
      </div>
      <details class="export-menu">
        <summary>导出</summary>
        <div class="export-list">
          <a v-for="artifact in exportArtifacts" :key="artifact.id" :class="{ disabled: !artifact.downloadable }" :href="artifact.downloadable ? artifact.url : undefined" download>
            <strong>{{ artifact.label }}</strong>
            <span>{{ artifact.state === 'ready' ? '可下载' : '计划中' }}</span>
            <small>{{ artifact.note }}</small>
          </a>
        </div>
      </details>
    </section>

    <div v-if="viewState === 'report'" class="workbench-grid">
      <main class="report-canvas">
        <article class="document-shell">
          <header class="document-head">
            <div>
              <span>{{ reportView?.version || selectedVersion }} 版 · {{ versionIntent }}</span>
              <h1>{{ reportView?.title }}</h1>
              <p>{{ reportView?.subtitle }}</p>
            </div>
            <div class="fake-stamp">REPORT_VIEW</div>
          </header>

          <section class="kpi-strip" aria-label="关键指标">
            <div v-for="kpi in reportView?.kpis || []" :key="kpi.label" :class="['kpi-item', kpi.tone || 'info']">
              <span>{{ kpi.label }}</span>
              <strong>{{ kpi.value }}</strong>
              <small>{{ kpi.note }}</small>
            </div>
          </section>

          <nav class="section-index" aria-label="报告目录">
            <a v-for="section in visibleSections" :key="section.id" :href="`#report-${section.id}`">{{ section.heading }}</a>
          </nav>

          <section v-for="section in visibleSections" :id="`report-${section.id}`" :key="section.id" class="report-section">
            <div class="section-kicker">{{ section.eyebrow }}</div>
            <h2>{{ section.heading }}</h2>
            <template v-for="(block, index) in section.blocks" :key="`${section.id}-${index}`">
              <p v-if="block.type === 'paragraph'" class="report-paragraph">{{ block.text }}</p>
              <ul v-else-if="block.type === 'list'" class="report-list">
                <li v-for="item in block.items" :key="item">{{ item }}</li>
              </ul>
              <div v-else :class="['report-callout', block.tone || 'info']">
                <strong>{{ block.title }}</strong>
                <p>{{ block.text }}</p>
              </div>
            </template>
          </section>

          <section v-if="appendixMode !== 'hidden'" id="report-appendix" class="report-section appendix-section">
            <div class="section-kicker">Appendix</div>
            <h2>五、附录引用</h2>
            <p class="report-paragraph">
              附录当前以结构化摘要方式展示；完整 appendix_b 属于内部数据，不直接暴露为用户下载入口。
            </p>
            <div class="appendix-grid">
              <div>
                <span>事件</span>
                <strong>{{ reportView?.appendix.event_name }}</strong>
              </div>
              <div>
                <span>worlds</span>
                <strong>{{ reportView?.appendix.worlds_count }}</strong>
              </div>
              <div>
                <span>confirmed risks</span>
                <strong>{{ reportView?.appendix.confirmed_risks }}</strong>
              </div>
              <div>
                <span>等级分布</span>
                <strong>{{ reportView?.appendix.risk_distribution || '暂无' }}</strong>
              </div>
            </div>
            <ul v-if="appendixMode === 'references'" class="report-list appendix-list">
              <li v-for="reference in reportView?.appendix.references || []" :key="reference">{{ reference }}</li>
            </ul>
          </section>
        </article>
      </main>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import { api } from '../api/client';
import type { AppendixMode, BatchSummary, NativeReportView, ReportArtifact, ReportEvent, ReportJobResponse, ReportUiState, ReportVersion, WorldStatus } from '../api/types';

type AppendixDisplayMode = 'hidden' | 'summary' | 'references';

const theme = ref<'dark' | 'light'>('dark');
const viewState = ref<ReportUiState>('setup');
const selectedVersion = ref<ReportVersion>('B');
const appendixMode = ref<AppendixDisplayMode>('summary');
const selectedBatchId = ref('');
const activeBatchId = ref('');
const history = ref<BatchSummary[]>([]);
const worlds = ref<WorldStatus[]>([]);
const allowPartial = ref(false);
const reportJob = ref<ReportJobResponse | null>(null);
const reportView = ref<NativeReportView | null>(null);
const errorMessage = ref('');
const generationLogRef = ref<HTMLElement | null>(null);
let pollTimer: ReturnType<typeof setInterval> | undefined;

const versionOptions: Array<{ id: ReportVersion; intent: string }> = [
  { id: 'A', intent: '短版决策摘要' },
  { id: 'B', intent: '标准研判报告' },
  { id: 'C', intent: '详细归档版' },
];

const completedCount = computed(() => worlds.value.filter((world) => world.status === 'completed').length);
const failedCount = computed(() => worlds.value.filter((world) => world.status === 'failed').length);
const datasetReady = computed(() => worlds.value.some((world) => world.rows.some((row) => row.label === '数据集' && row.value)));
const modelLabel = computed(() => reportView.value?.source.model || reportJob.value?.model.resolved_from || 'report slot');
const skillLabel = computed(() => reportView.value?.source.skill_id || reportJob.value?.skill_id || 'default');
const generatedVersions = computed(() => reportJob.value?.selected_versions?.length ? reportJob.value.selected_versions : [selectedVersion.value]);
const exportArtifacts = computed<ReportArtifact[]>(() => reportJob.value?.artifacts || []);
const generationEvents = computed<ReportEvent[]>(() => reportJob.value?.events?.length ? reportJob.value.events : [{ label: reportJob.value?.current_step || '等待后端状态', detail: '', status: 'current' }]);
const versionIntent = computed(() => versionOptions.find((item) => item.id === (reportView.value?.version || selectedVersion.value))?.intent || '研判报告');
const canGenerate = computed(() => !disableReason.value && viewState.value !== 'generating');
const disableReason = computed(() => {
  if (!selectedBatchId.value) return '请选择一个 batch。';
  if (!completedCount.value) return '没有 completed world，不能生成报告。';
  if (failedCount.value > 0 && !allowPartial.value) return '存在 failed world，请确认仅基于 completed worlds 生成。';
  return '';
});
const statusLabel = computed(() => {
  if (viewState.value === 'setup') return '未生成';
  if (viewState.value === 'generating') return '生成中';
  if (viewState.value === 'blocked') return '已阻断';
  if (viewState.value === 'failed') return '失败';
  return '已生成';
});
const statusNote = computed(() => {
  if (viewState.value === 'setup') return '等待生成前确认';
  if (viewState.value === 'generating') return `${reportJob.value?.progress || 0}% · ${reportJob.value?.current_step || '等待后端状态'}`;
  if (viewState.value === 'blocked' || viewState.value === 'failed') return reportJob.value?.error_code || reportJob.value?.current_step || '需要处理';
  return reportJob.value?.current_step || '报告生成完成';
});
const visibleSections = computed(() => reportView.value?.sections.filter((section) => section.kind !== 'appendix') || []);

onMounted(async () => {
  await Promise.all([loadSources(), restoreActiveReport()]);
});

onBeforeUnmount(stopPolling);

async function loadSources() {
  try {
    const [active, batches] = await Promise.all([api.getActiveRun(), api.getHistory()]);
    activeBatchId.value = active.batch?.batch_id || '';
    history.value = batches;
    selectedBatchId.value = activeBatchId.value || batches[0]?.batchId || '';
    await loadWorlds();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '报告来源读取失败';
  }
}

async function loadWorlds() {
  if (!selectedBatchId.value) {
    worlds.value = [];
    return;
  }
  try {
    const response = await api.getWorlds(selectedBatchId.value);
    worlds.value = response.worlds.map((world, index) => ({
      id: world.id,
      round: `第 ${index + 1} 轮`,
      model: world.model,
      status: world.status,
      rows: [
        { label: '模型', value: world.model },
        { label: '状态', value: world.status },
        { label: '数据集', value: world.dataset_path },
      ],
      errorSummary: world.error,
    }));
  } catch (error) {
    worlds.value = [];
    errorMessage.value = error instanceof Error ? error.message : 'world 列表读取失败';
  }
}

async function restoreActiveReport() {
  try {
    const active = await api.getActiveReportJob();
    if (active.active && active.job) await applyJob(active.job);
  } catch {
    // Restore is best-effort; setup state remains usable.
  }
}

async function startReport() {
  if (!canGenerate.value) return;
  errorMessage.value = '';
  reportView.value = null;
  viewState.value = 'generating';
  const job = await api.createReportJob({
    batch_id: selectedBatchId.value,
    versions: [selectedVersion.value],
    appendix_mode: appendixMode.value === 'references' ? 'included' : 'none',
    allow_partial: allowPartial.value,
  });
  await applyJob(job);
  startPolling();
}

async function pollJob() {
  if (!reportJob.value?.job_id) return;
  try {
    await applyJob(await api.getReportJobStatus(reportJob.value.job_id));
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '报告状态轮询失败';
    stopPolling();
  }
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(pollJob, 1500);
}

function stopPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = undefined;
}

async function applyJob(job: ReportJobResponse) {
  reportJob.value = job;
  selectedVersion.value = job.version || job.selected_versions?.[0] || selectedVersion.value;
  if (job.report_view) reportView.value = job.report_view;
  if (job.ui_state === 'blocked') {
    viewState.value = 'blocked';
    stopPolling();
    return;
  }
  if (job.ui_state === 'failed') {
    viewState.value = 'failed';
    stopPolling();
    return;
  }
  if (job.ui_state === 'report' || (job.status === 'completed' && job.report_view)) {
    viewState.value = 'report';
    stopPolling();
    return;
  }
  if (job.status === 'completed' && !job.report_view) {
    try {
      reportView.value = await api.getNativeReportView(job.job_id, selectedVersion.value);
      viewState.value = 'report';
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : 'report_view 读取失败';
      viewState.value = 'failed';
    }
    stopPolling();
    return;
  }
  if (job.status === 'blocked') {
    viewState.value = 'blocked';
    stopPolling();
    return;
  }
  if (job.status === 'failed') {
    viewState.value = 'failed';
    stopPolling();
    return;
  }
  viewState.value = 'generating';
  await nextTick();
  generationLogRef.value?.scrollTo({ top: generationLogRef.value.scrollHeight, behavior: 'smooth' });
}

async function selectGeneratedVersion(version: ReportVersion) {
  selectedVersion.value = version;
  if (!reportJob.value?.job_id) return;
  try {
    reportView.value = await api.getNativeReportView(reportJob.value.job_id, version);
  } catch {
    // The backend may only have generated one selected version in R1.
  }
}

function resetToSetup() {
  stopPolling();
  reportJob.value = null;
  reportView.value = null;
  errorMessage.value = '';
  viewState.value = 'setup';
}
</script>

<style scoped>
.report-workbench {
  --rw-bg: #07121f;
  --rw-surface: rgba(8, 22, 39, .88);
  --rw-surface-2: rgba(10, 29, 49, .92);
  --rw-paper: rgba(242, 248, 252, .96);
  --rw-paper-line: rgba(24, 60, 82, .12);
  --rw-text: #ecf8ff;
  --rw-paper-text: #102333;
  --rw-muted: #92adbf;
  --rw-paper-muted: #5d6f7c;
  --rw-line: rgba(81, 220, 255, .24);
  --rw-strong-line: rgba(81, 220, 255, .46);
  --rw-accent: #51dcff;
  --rw-blue: #1f8cff;
  --rw-green: #35f0a0;
  --rw-amber: #f2c94c;
  --rw-red: #ff6b7d;
  --rw-shadow: 0 22px 70px rgba(0, 0, 0, .34);
  display: grid;
  gap: 14px;
  color: var(--rw-text);
}

.report-workbench.theme-light {
  --rw-bg: #eef4f7;
  --rw-surface: rgba(255, 255, 255, .9);
  --rw-surface-2: rgba(247, 251, 253, .96);
  --rw-paper: #ffffff;
  --rw-paper-line: rgba(18, 56, 82, .14);
  --rw-text: #132b3a;
  --rw-paper-text: #132b3a;
  --rw-muted: #647987;
  --rw-paper-muted: #647987;
  --rw-line: rgba(28, 106, 145, .18);
  --rw-strong-line: rgba(28, 106, 145, .34);
  --rw-accent: #087fa8;
  --rw-blue: #136fd1;
  --rw-green: #16895d;
  --rw-amber: #a46b00;
  --rw-red: #c43f51;
  --rw-shadow: 0 18px 56px rgba(31, 56, 74, .14);
}

.report-topbar,
.report-toolbar,
.document-shell {
  border: 1px solid var(--rw-line);
  background: var(--rw-surface);
  border-radius: 8px;
  box-shadow: var(--rw-shadow);
}

.report-topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 18px;
}

.mini-label,
.section-kicker,
.job-pill small,
.kpi-item small {
  color: var(--rw-muted);
  font-size: 12px;
}

.mini-label {
  display: block;
  margin-bottom: 6px;
}

.report-topbar h3 {
  margin: 0 0 6px;
  font-size: 26px;
  line-height: 1.18;
}

.report-topbar p {
  max-width: 760px;
  margin: 0;
  color: var(--rw-muted);
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.job-pill {
  min-width: 190px;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2px 8px;
  align-items: center;
  padding: 9px 11px;
  border: 1px solid var(--rw-line);
  border-radius: 8px;
  background: var(--rw-surface-2);
}

.job-pill small {
  grid-column: 2;
}

.pulse-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: var(--rw-muted);
}

.pulse-dot.completed {
  background: var(--rw-green);
}

.pulse-dot.report {
  background: var(--rw-green);
}

.pulse-dot.blocked {
  background: var(--rw-amber);
}

.pulse-dot.failed {
  background: var(--rw-red);
}

.pulse-dot.setup {
  background: var(--rw-amber);
}

.pulse-dot.generating {
  background: var(--rw-accent);
  animation: reportPulse 1s ease-in-out infinite;
}

@keyframes reportPulse {
  0%, 100% {
    opacity: .45;
    transform: scale(.9);
  }
  50% {
    opacity: 1;
    transform: scale(1.16);
  }
}

.quiet-action {
  border: 1px solid var(--rw-line);
  background: var(--rw-surface-2);
  color: var(--rw-text);
  border-radius: 8px;
  padding: 9px 11px;
  cursor: pointer;
}

.theme-switch,
.report-toolbar,
.toolbar-group {
  display: flex;
  border: 1px solid var(--rw-line);
  border-radius: 8px;
  background: var(--rw-surface-2);
}

.theme-switch {
  padding: 3px;
}

.theme-switch button,
.toolbar-group button {
  border: 0;
  background: transparent;
  color: var(--rw-muted);
  border-radius: 6px;
  padding: 7px 10px;
  cursor: pointer;
}

.theme-switch button.active,
.toolbar-group button.active {
  color: var(--rw-paper-text);
  background: var(--rw-accent);
}

.workbench-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.report-toolbar {
  align-items: center;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 10px;
  padding: 10px;
}

.toolbar-group {
  align-items: center;
  gap: 3px;
  padding: 3px;
}

.toolbar-group span {
  padding: 0 8px;
  color: var(--rw-muted);
  font-size: 12px;
}

.toolbar-group button {
  cursor: pointer;
}

.setup-shell {
  display: grid;
  gap: 18px;
  border: 1px solid var(--rw-line);
  background: var(--rw-surface);
  border-radius: 8px;
  padding: 22px;
  box-shadow: var(--rw-shadow);
}

.setup-copy {
  max-width: 760px;
}

.setup-copy h4 {
  margin: 0 0 8px;
  font-size: 30px;
  line-height: 1.16;
}

.setup-copy p {
  margin: 0;
  color: var(--rw-muted);
}

.setup-grid {
  display: grid;
  grid-template-columns: 1.1fr 1fr 1fr;
  gap: 12px;
}

.setup-card {
  display: grid;
  align-content: start;
  gap: 12px;
  min-height: 210px;
  border: 1px solid var(--rw-line);
  background: var(--rw-surface-2);
  border-radius: 8px;
  padding: 16px;
}

.setup-card > span {
  color: var(--rw-muted);
  font-size: 12px;
}

.setup-card > strong {
  overflow-wrap: anywhere;
  font-size: 20px;
  line-height: 1.25;
}

.setup-card p {
  margin: 0;
  color: var(--rw-muted);
  font-size: 12px;
}

.setup-card dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
}

.setup-card dl div {
  border: 1px solid var(--rw-line);
  border-radius: 8px;
  padding: 10px;
}

.setup-card dt {
  color: var(--rw-muted);
  font-size: 12px;
}

.setup-card dd {
  margin: 4px 0 0;
  font-weight: 760;
}

.setup-options {
  display: grid;
  gap: 8px;
}

.setup-options button {
  border: 1px solid var(--rw-line);
  background: transparent;
  color: var(--rw-text);
  border-radius: 8px;
  padding: 10px;
  text-align: left;
  cursor: pointer;
}

.setup-options button.active {
  color: var(--rw-paper-text);
  border-color: transparent;
  background: var(--rw-accent);
}

.setup-options small {
  display: block;
  margin-top: 2px;
  opacity: .78;
}

.compact-options {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.compact-options button {
  text-align: center;
}

.generate-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.generate-button {
  border: 1px solid rgba(81, 220, 255, .7);
  background: linear-gradient(135deg, rgba(31, 140, 255, .95), rgba(28, 211, 255, .72));
  color: #02101c;
  font-weight: 780;
  border-radius: 8px;
  padding: 12px 18px;
  cursor: pointer;
}

.generate-actions small {
  color: var(--rw-muted);
}

.generating-shell {
  display: grid;
  gap: 14px;
  border: 1px solid var(--rw-line);
  background: var(--rw-surface);
  border-radius: 8px;
  padding: 22px;
  box-shadow: var(--rw-shadow);
}

.failure-shell {
  display: grid;
  gap: 12px;
  max-width: 760px;
  border: 1px solid var(--rw-line);
  background: var(--rw-surface);
  border-radius: 8px;
  padding: 22px;
  box-shadow: var(--rw-shadow);
}

.failure-shell h4 {
  margin: 0;
  font-size: 28px;
  line-height: 1.16;
}

.failure-shell p {
  margin: 0;
  color: var(--rw-muted);
}

.generating-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.generating-head h4 {
  margin: 0 0 8px;
  font-size: 30px;
  line-height: 1.16;
}

.generating-head p {
  max-width: 720px;
  margin: 0;
  color: var(--rw-muted);
}

.generating-head > strong {
  font-size: 34px;
  color: var(--rw-accent);
}

.loading-bar {
  height: 10px;
  border: 1px solid var(--rw-line);
  border-radius: 999px;
  background: var(--rw-surface-2);
  overflow: hidden;
}

.loading-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--rw-blue), var(--rw-accent), var(--rw-green));
  transition: width .22s ease;
}

.generation-stream {
  display: grid;
  gap: 10px;
  max-height: 310px;
  overflow-y: auto;
  padding-right: 4px;
  scroll-behavior: smooth;
}

.generation-event {
  display: grid;
  grid-template-columns: 42px 1fr;
  gap: 12px;
  align-items: start;
  border: 1px solid var(--rw-line);
  border-radius: 8px;
  padding: 13px;
  background: var(--rw-surface-2);
  animation: eventIn .22s ease both;
}

@keyframes eventIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.generation-event > span {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: var(--rw-accent);
  border: 1px solid var(--rw-line);
  background: rgba(81, 220, 255, .06);
  font-weight: 760;
}

.generation-event strong {
  display: block;
  margin-bottom: 3px;
}

.generation-event p {
  margin: 0;
  color: var(--rw-muted);
}

.export-menu {
  position: relative;
  margin-left: auto;
  color: var(--rw-muted);
  font-size: 12px;
}

.export-menu summary {
  cursor: pointer;
  list-style: none;
  border: 1px solid var(--rw-line);
  border-radius: 8px;
  padding: 7px 10px;
  background: var(--rw-surface-2);
}

.export-menu summary::-webkit-details-marker {
  display: none;
}

.export-list {
  position: absolute;
  right: 0;
  z-index: 3;
  display: grid;
  gap: 6px;
  min-width: 220px;
  max-height: 190px;
  overflow-y: auto;
  margin-top: 8px;
  padding: 10px;
  border: 1px solid var(--rw-line);
  border-radius: 8px;
  background: var(--rw-surface-2);
  box-shadow: var(--rw-shadow);
}

.export-list a,
.export-list button {
  display: block;
  border: 1px solid var(--rw-line);
  background: transparent;
  color: var(--rw-text);
  border-radius: 8px;
  padding: 9px;
  text-align: left;
  text-decoration: none;
}

.export-list a.disabled {
  cursor: not-allowed;
  opacity: .58;
}

.export-list strong,
.export-list span,
.export-list small {
  display: block;
}

.export-list span {
  color: var(--rw-accent);
}

.export-list small {
  color: var(--rw-muted);
}

.report-canvas {
  min-width: 0;
}

.document-shell {
  background: var(--rw-paper);
  color: var(--rw-paper-text);
  padding: 34px clamp(26px, 4vw, 54px);
}

.document-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--rw-paper-line);
}

.document-head span {
  color: var(--rw-paper-muted);
  font-weight: 700;
}

.document-head h1 {
  margin: 8px 0 10px;
  font-size: clamp(30px, 4vw, 48px);
  line-height: 1.12;
}

.document-head p {
  max-width: 780px;
  margin: 0;
  color: var(--rw-paper-muted);
  font-size: 16px;
}

.fake-stamp {
  align-self: flex-start;
  flex: 0 0 auto;
  border: 1px solid rgba(31, 140, 255, .32);
  border-radius: 8px;
  padding: 7px 9px;
  color: var(--rw-blue);
  font-weight: 760;
  font-size: 12px;
}

.kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 22px 0;
}

.kpi-item {
  border: 1px solid var(--rw-paper-line);
  border-radius: 8px;
  padding: 12px;
  background: rgba(14, 52, 78, .035);
}

.theme-dark .kpi-item {
  background: rgba(8, 22, 39, .05);
}

.kpi-item span,
.kpi-item small {
  display: block;
  color: var(--rw-paper-muted);
}

.kpi-item strong {
  display: block;
  margin: 4px 0;
  font-size: 24px;
}

.kpi-item.good strong {
  color: var(--rw-green);
}

.kpi-item.warn strong {
  color: var(--rw-amber);
}

.kpi-item.bad strong {
  color: var(--rw-red);
}

.kpi-item.info strong {
  color: var(--rw-blue);
}

.section-index {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 22px;
}

.section-index a {
  text-decoration: none;
  border: 1px solid var(--rw-paper-line);
  border-radius: 999px;
  padding: 5px 10px;
  color: var(--rw-paper-muted);
  font-size: 12px;
}

.report-section {
  padding: 22px 0;
  border-top: 1px solid var(--rw-paper-line);
  scroll-margin-top: 18px;
}

.section-kicker {
  color: var(--rw-blue);
  font-weight: 760;
}

.report-section h2 {
  margin: 5px 0 14px;
  font-size: 24px;
  line-height: 1.25;
}

.report-paragraph {
  margin: 0 0 12px;
  color: var(--rw-paper-text);
  font-size: 16px;
}

.report-list {
  display: grid;
  gap: 9px;
  margin: 0 0 14px;
  padding-left: 20px;
  color: var(--rw-paper-text);
  font-size: 15px;
}

.report-callout {
  margin: 14px 0;
  border: 1px solid var(--rw-paper-line);
  border-left: 4px solid var(--rw-blue);
  border-radius: 8px;
  padding: 13px 14px;
  background: rgba(31, 140, 255, .06);
}

.report-callout.warn {
  border-left-color: var(--rw-amber);
  background: rgba(242, 201, 76, .08);
}

.report-callout.good {
  border-left-color: var(--rw-green);
  background: rgba(53, 240, 160, .07);
}

.report-callout p {
  margin: 4px 0 0;
  color: var(--rw-paper-muted);
}

.appendix-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 12px 0;
}

.appendix-grid div {
  border: 1px solid var(--rw-paper-line);
  border-radius: 8px;
  padding: 11px;
}

.appendix-grid span,
.appendix-grid strong {
  display: block;
}

.appendix-grid span {
  color: var(--rw-paper-muted);
  font-size: 12px;
}

.appendix-list {
  margin-top: 14px;
}

@media (max-width: 1280px) {
  .workbench-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 900px) {
  .report-topbar,
  .document-head,
  .generating-head {
    display: grid;
  }

  .workbench-grid,
  .kpi-strip,
  .appendix-grid,
  .setup-grid,
  .setup-card dl,
  .compact-options {
    grid-template-columns: 1fr;
  }

  .document-shell {
    padding: 24px 18px;
  }
}
</style>
