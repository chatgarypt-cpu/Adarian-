<template>
  <section class="report-workbench" :class="`theme-${theme}`">
    <header class="report-topbar">
      <div>
        <span class="mini-label">REPORT WORKBENCH</span>
        <h3>报告生成与阅读</h3>
        <p>在浏览器中阅读交互报告，并从同一份正文导出 DOCX、PDF、HTML 或 Markdown。</p>
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
        <p>选择真实推演任务、报告版本和写作风格；生成后可直接阅读正文或下载正式文件。</p>
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
              <dt>有效样本</dt>
              <dd>{{ completedCount }}</dd>
            </div>
            <div>
              <dt>失败样本</dt>
              <dd>{{ failedCount }}</dd>
            </div>
            <div>
              <dt>数据状态</dt>
              <dd>{{ datasetReady ? '可用' : '缺失' }}</dd>
            </div>
          </dl>
          <label v-if="failedCount" class="check-row">
            <input v-model="allowPartial" type="checkbox" />
            <span>仅基于已完成样本生成</span>
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
          <span>写作与附录</span>
          <div class="form-row setup-field">
            <label>本次写作 Skill</label>
            <select v-model="selectedSkillId">
              <optgroup label="系统内置">
                <option v-for="skill in builtinSkills" :key="skill.id" :value="skill.id">{{ skill.label }}</option>
              </optgroup>
              <optgroup v-if="userSkills.length" label="用户导入">
                <option v-for="skill in userSkills" :key="skill.id" :value="skill.id">{{ skill.label }}</option>
              </optgroup>
            </select>
          </div>
          <div v-if="selectedSkill" class="selected-skill-note">
            <strong>{{ selectedSkill.label }} · v{{ selectedSkill.version }}</strong>
            <small>{{ selectedSkill.source === 'builtin' ? '系统内置' : '用户导入' }} · {{ selectedSkill.directory }}</small>
          </div>
          <div class="setup-options compact-options">
            <button type="button" :class="{ active: appendixMode === 'hidden' }" @click="appendixMode = 'hidden'">不含附录</button>
            <button type="button" :class="{ active: appendixMode === 'references' }" @click="appendixMode = 'references'">包含附录</button>
          </div>
          <RouterLink class="manage-skill-link" to="/settings">管理写作 Skill</RouterLink>
        </section>
      </div>

      <details class="generation-parameters">
        <summary>生成参数</summary>
        <div class="parameter-grid">
          <div class="form-row">
            <label>模型网关</label>
            <select v-model="selectedGatewayId">
              <option value="">使用环境默认</option>
              <option v-for="gateway in settings.modelGateways" :key="gateway.id" :value="gateway.id">{{ gateway.name }}</option>
            </select>
          </div>
          <div class="form-row">
            <label>模型</label>
            <input v-model="selectedModelId" placeholder="使用网关默认模型" />
          </div>
          <div class="form-row">
            <label>温度</label>
            <input v-model.number="selectedTemperature" type="number" min="0" max="2" step="0.1" />
          </div>
          <div class="form-row">
            <label>最大 Token</label>
            <input v-model.number="selectedMaxTokens" type="number" min="512" max="65536" step="512" />
          </div>
        </div>
      </details>

      <div class="generate-actions">
        <button class="generate-button" type="button" :disabled="!canGenerate" @click="startReport">生成报告</button>
        <small>{{ disableReason || `将使用 ${skillLabel} · ${modelLabel}` }}</small>
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
      <p>{{ reportJob?.error_message || errorMessage || '后端未返回错误原因。' }}</p>
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
        <button type="button" :class="{ active: appendixMode === 'references' }" @click="appendixMode = 'references'">显示</button>
      </div>
      <details class="export-menu">
        <summary>导出</summary>
        <div class="export-list">
          <a v-for="artifact in exportArtifacts" :key="artifact.id" :href="artifact.url" download>
            <strong>{{ artifact.label }}</strong>
            <span>可下载</span>
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
              <p>{{ productText(reportView?.subtitle) }}</p>
            </div>
            <div class="report-stamp">INTERACTIVE</div>
          </header>

          <section class="kpi-strip" aria-label="关键指标">
            <div v-for="kpi in reportView?.kpis || []" :key="kpi.label" :class="['kpi-item', kpi.tone || 'info']">
              <span>{{ productText(kpi.label) }}</span>
              <strong>{{ kpi.value }}</strong>
              <small>{{ productText(kpi.note) }}</small>
            </div>
          </section>

          <nav class="section-index" aria-label="报告目录">
            <a v-for="section in visibleSections" :key="section.id" :href="`#report-${section.id}`">{{ section.heading }}</a>
          </nav>

          <section v-for="section in visibleSections" :id="`report-${section.id}`" :key="section.id" class="report-section">
            <div class="section-kicker">{{ section.eyebrow }}</div>
            <h2>{{ section.heading }}</h2>
            <template v-for="(block, index) in section.blocks" :key="`${section.id}-${index}`">
              <h3 v-if="block.type === 'subheading' || isLegacySubheading(block.text)" class="report-subheading">
                {{ cleanReportText(block.text) }}
              </h3>
              <p v-else-if="block.type === 'paragraph'" class="report-paragraph">{{ cleanReportText(block.text) }}</p>
              <ul v-else-if="block.type === 'list'" class="report-list">
                <li v-for="item in block.items" :key="item">{{ cleanReportText(item) }}</li>
              </ul>
              <pre v-else-if="block.type === 'preformatted'" class="report-preformatted">{{ block.text }}</pre>
              <div v-else-if="block.type === 'table'" class="report-table-scroll">
                <table class="report-table">
                  <thead>
                    <tr><th v-for="header in block.headers" :key="header">{{ cleanReportText(header) }}</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, rowIndex) in block.rows" :key="rowIndex">
                      <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cleanReportText(cell) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else :class="['report-callout', block.tone || 'info']">
                <strong>{{ cleanReportText(block.title) }}</strong>
                <p>{{ cleanReportText(block.text) }}</p>
              </div>
            </template>
          </section>

          <section v-if="appendixMode !== 'hidden' && reportView?.appendix.sections?.length" id="report-appendix" class="report-section appendix-section">
            <div class="section-kicker">Appendix</div>
            <h2>{{ reportView.appendix.title || '附录' }}</h2>
            <template v-for="section in reportView.appendix.sections" :key="section.heading">
              <h3 class="report-subheading">{{ section.heading }}</h3>
              <template v-for="(block, index) in section.blocks" :key="`${section.heading}-${index}`">
                <h4 v-if="block.type === 'subheading'" class="report-subheading">{{ cleanReportText(block.text) }}</h4>
                <p v-else-if="block.type === 'paragraph'" class="report-paragraph">{{ cleanReportText(block.text) }}</p>
                <ul v-else-if="block.type === 'list'" class="report-list">
                  <li v-for="item in block.items" :key="item">{{ cleanReportText(item) }}</li>
                </ul>
                <pre v-else-if="block.type === 'preformatted'" class="report-preformatted">{{ block.text }}</pre>
                <div v-else-if="block.type === 'table'" class="report-table-scroll">
                  <table class="report-table">
                    <thead>
                      <tr><th v-for="header in block.headers" :key="header">{{ cleanReportText(header) }}</th></tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, rowIndex) in block.rows" :key="rowIndex">
                        <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cleanReportText(cell) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>
            </template>
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
import { useSettingsStore } from '../stores/settings';

type AppendixDisplayMode = 'hidden' | 'references';

const theme = ref<'dark' | 'light'>('dark');
const settings = useSettingsStore();
const viewState = ref<ReportUiState>('setup');
const selectedVersion = ref<ReportVersion>('B');
const appendixMode = ref<AppendixDisplayMode>('hidden');
const selectedBatchId = ref('');
const activeBatchId = ref('');
const history = ref<BatchSummary[]>([]);
const worlds = ref<WorldStatus[]>([]);
const allowPartial = ref(false);
const selectedSkillId = ref('default_government');
const selectedGatewayId = ref('');
const selectedModelId = ref('');
const selectedTemperature = ref(0.3);
const selectedMaxTokens = ref(8192);
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
const builtinSkills = computed(() => settings.reportSkills.filter((skill) => skill.source === 'builtin'));
const userSkills = computed(() => settings.reportSkills.filter((skill) => skill.source === 'user'));
const selectedSkill = computed(() => settings.reportSkills.find((skill) => skill.id === selectedSkillId.value));
const modelLabel = computed(() => reportJob.value?.model.model_id || selectedModelId.value || reportView.value?.source.model || '环境默认模型');
const skillLabel = computed(() => reportJob.value?.skill?.label || selectedSkill.value?.label || reportView.value?.source.skill_label || selectedSkillId.value);
const generatedVersions = computed(() => reportJob.value?.selected_versions?.length ? reportJob.value.selected_versions : [selectedVersion.value]);
const exportArtifacts = computed<ReportArtifact[]>(() => {
  const sourceViewId = `report_view_${selectedVersion.value}`;
  return (reportJob.value?.artifacts || []).filter(
    (artifact) => artifact.state === 'ready'
      && artifact.downloadable
      && (!artifact.source_view_id || artifact.source_view_id === sourceViewId),
  );
});
const generationEvents = computed<ReportEvent[]>(() => reportJob.value?.events?.length ? reportJob.value.events : [{ label: reportJob.value?.current_step || '等待后端状态', detail: '', status: 'current' }]);
const versionIntent = computed(() => versionOptions.find((item) => item.id === (reportView.value?.version || selectedVersion.value))?.intent || '研判报告');
const canGenerate = computed(() => !disableReason.value && viewState.value !== 'generating');
const disableReason = computed(() => {
  if (!selectedBatchId.value) return '请选择一个 batch。';
  if (!completedCount.value) return '没有已完成样本，不能生成报告。';
  if (failedCount.value > 0 && !allowPartial.value) return '存在失败样本，请确认仅基于已完成样本生成。';
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

onMounted(initialize);

onBeforeUnmount(stopPolling);

async function initialize() {
  await settings.loadSettings();
  selectedSkillId.value = settings.reportSkillId;
  selectedGatewayId.value = settings.reportGatewayId;
  selectedModelId.value = settings.reportModelId;
  selectedTemperature.value = settings.reportTemperature;
  selectedMaxTokens.value = settings.reportMaxTokens;
  await Promise.all([loadSources(), restoreActiveReport()]);
}

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
  try {
    const job = await api.createReportJob({
      batch_id: selectedBatchId.value,
      versions: [selectedVersion.value],
      appendix_mode: appendixMode.value === 'references' ? 'included' : 'none',
      allow_partial: allowPartial.value,
      skill_id: selectedSkillId.value,
      gateway_id: selectedGatewayId.value,
      model_id: selectedModelId.value.trim(),
      temperature: Number(selectedTemperature.value),
      max_tokens: Number(selectedMaxTokens.value),
    });
    await applyJob(job);
    startPolling();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '报告任务创建失败';
    viewState.value = 'failed';
  }
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
  selectedSkillId.value = job.skill?.id || job.skill_id || selectedSkillId.value;
  selectedGatewayId.value = job.model.gateway_id || selectedGatewayId.value;
  selectedModelId.value = job.model.model_id || selectedModelId.value;
  selectedTemperature.value = job.model.temperature ?? selectedTemperature.value;
  selectedMaxTokens.value = job.model.max_tokens ?? selectedMaxTokens.value;
  selectedVersion.value = job.version || job.selected_versions?.[0] || selectedVersion.value;
  if (job.report_view) {
    reportView.value = job.report_view;
    appendixMode.value = job.report_view.appendix.mode === 'hidden' ? 'hidden' : 'references';
  }
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
      errorMessage.value = error instanceof Error ? error.message : '交互报告读取失败';
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
    appendixMode.value = reportView.value.appendix.mode === 'hidden' ? 'hidden' : 'references';
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

function isLegacySubheading(value?: string) {
  return /^\s*#{2,6}\s+/.test(value || '');
}

function cleanReportText(value?: string) {
  return (value || '')
    .trim()
    .replace(/^#{1,6}\s+/, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/`([^`]+)`/g, '$1');
}

function productText(value?: string) {
  return (value || '')
    .replace(/completed worlds?/gi, '已完成样本')
    .replace(/simulation_dataset(?:\.json)?/gi, '结构化数据')
    .replace(/appendix_b/gi, '风险依据')
    .replace(/world 覆盖/gi, '有效样本');
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.compact-options button {
  text-align: center;
}

.setup-field {
  margin: 0;
}

.selected-skill-note {
  min-width: 0;
  display: grid;
  gap: 3px;
  padding: 10px;
  border: 1px solid var(--rw-line);
  border-radius: 8px;
}

.selected-skill-note small {
  overflow: hidden;
  color: var(--rw-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.manage-skill-link {
  color: var(--rw-accent);
  font-size: 12px;
  text-decoration: none;
}

.generation-parameters {
  border-top: 1px solid var(--rw-line);
  border-bottom: 1px solid var(--rw-line);
  padding: 12px 0;
}

.generation-parameters summary {
  color: var(--rw-muted);
  cursor: pointer;
  font-weight: 700;
}

.parameter-grid {
  display: grid;
  grid-template-columns: 1fr 1.2fr .65fr .75fr;
  gap: 12px;
  margin-top: 12px;
}

.parameter-grid .form-row {
  margin: 0;
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

.report-stamp {
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

.report-subheading {
  margin: 24px 0 10px;
  color: var(--rw-paper-text);
  font-size: 18px;
  line-height: 1.4;
}

.report-list {
  display: grid;
  gap: 9px;
  margin: 0 0 14px;
  padding-left: 20px;
  color: var(--rw-paper-text);
  font-size: 15px;
}

.report-preformatted {
  max-width: 100%;
  overflow-x: auto;
  margin: 0 0 14px;
  border: 1px solid var(--rw-paper-line);
  border-radius: 6px;
  padding: 12px 14px;
  color: var(--rw-paper-text);
  background: rgba(127, 151, 170, .08);
  font: 13px/1.6 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.report-table-scroll {
  max-width: 100%;
  overflow-x: auto;
  margin: 0 0 16px;
}

.report-table {
  width: 100%;
  min-width: 560px;
  border-collapse: collapse;
  color: var(--rw-paper-text);
  font-size: 14px;
}

.report-table th,
.report-table td {
  border: 1px solid var(--rw-paper-line);
  padding: 9px 10px;
  text-align: left;
  vertical-align: top;
}

.report-table th {
  color: var(--rw-blue);
  background: rgba(31, 140, 255, .06);
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
  .setup-grid,
  .setup-card dl,
  .compact-options,
  .parameter-grid {
    grid-template-columns: 1fr;
  }

  .document-shell {
    padding: 24px 18px;
  }
}
</style>
