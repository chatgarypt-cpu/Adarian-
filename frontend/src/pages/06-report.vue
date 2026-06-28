<template>
  <section class="workspace">
    <StateTools v-model="state" />
    <PageState :state="state" :message="errorMessage || '报告生成失败'">
      <div class="hero-grid">
        <Panel title="报告生成" note="dataset-only">
          <div class="status-note">仅消费 completed worlds 的 simulation_dataset.json；不会上传原始材料，也不会联网补事实。</div>
          <div class="form-row">
            <label>报告来源</label>
            <select v-model="selectedBatchId" @change="loadWorlds">
              <option v-if="run.activeBatch.batchId" :value="run.activeBatch.batchId">当前任务：{{ run.activeBatch.batchId }}</option>
              <option v-for="batch in history" :key="batch.batchId" :value="batch.batchId">{{ batch.name }} · {{ batch.batchId }}</option>
            </select>
          </div>
          <div class="report-metrics">
            <div><span>completed</span><strong>{{ completedCount }}</strong></div>
            <div><span>failed</span><strong>{{ failedCount }}</strong></div>
            <div><span>dataset</span><strong>{{ datasetCount }}</strong></div>
          </div>
          <label v-if="failedCount > 0" class="check-row">
            <input v-model="allowPartial" type="checkbox" />
            <span>仅基于 completed worlds 生成，接受数据不完整提示</span>
          </label>
          <div class="actions">
            <button class="primary" type="button" :disabled="!canGenerate" @click="startReport">{{ job?.status === 'running' ? '生成中...' : '生成报告' }}</button>
            <button class="ghost" type="button" :disabled="job?.status === 'running'" @click="restoreActiveJob">恢复最近报告</button>
          </div>
          <div v-if="disableReason" class="status-note">{{ disableReason }}</div>
        </Panel>

        <Panel title="报告选项" note="v1.5.2.1">
          <div class="form-row">
            <label>版本</label>
            <div class="choice-row">
              <label v-for="version in versionOptions" :key="version" class="choice-pill">
                <input v-model="selectedVersions" type="checkbox" :value="version" />
                <span>{{ version }} 版</span>
              </label>
            </div>
          </div>
          <div class="form-row">
            <label>附录</label>
            <div class="choice-row">
              <label class="choice-pill"><input v-model="appendixMode" type="radio" value="none" /><span>不附录</span></label>
              <label class="choice-pill"><input v-model="appendixMode" type="radio" value="included" /><span>含附录</span></label>
              <label class="choice-pill"><input v-model="appendixMode" type="radio" value="both" /><span>两份都要</span></label>
            </div>
          </div>
          <div class="form-row">
            <label>写作风格</label>
            <select v-model="skillId">
              <option value="">使用系统默认</option>
              <option v-for="skill in reportSkills" :key="skill.id" :value="skill.id">{{ skill.label }}</option>
            </select>
          </div>
          <div class="status-note">模型优先使用 03-models 当前选择；未选择时回退 08-settings 或 .env。</div>
        </Panel>
      </div>

      <Panel title="报告状态" :note="job?.status || 'idle'">
        <div class="report-progress">
          <div class="progress-bar"><span :style="{ width: `${job?.progress || 0}%` }" /></div>
          <strong>{{ job?.current_step || '等待生成' }}</strong>
        </div>
        <div v-if="job?.partial" class="status-note warn">数据不完整，基于 {{ job.completed_worlds_count }} 个 completed worlds 生成。</div>
        <div v-if="job?.status === 'blocked' || job?.status === 'failed'" class="error-box">
          <strong>{{ job.error_code }}</strong>
          <p>{{ job.error_message }}</p>
        </div>
        <div v-if="job?.audit_summary?.blocked_reasons?.length" class="steps">
          <StepLine v-for="reason in job.audit_summary.blocked_reasons" :key="reason" title="审核阻断" :note="reason" status="current" :chip="{ label: 'blocked', variant: 'bad' }" />
        </div>
        <div v-if="reportFiles.length" class="artifact-list">
          <button
            v-for="file in reportFiles"
            :key="file.id"
            class="artifact-item"
            :class="{ active: selectedReportFileId === file.id }"
            type="button"
            @click="selectedReportFileId = file.id"
          >
            <strong>{{ file.version || 'report' }} · {{ appendixLabel(file.appendix) }}</strong>
            <span>{{ file.format || fileFormat(file.name) }} · {{ file.previewable === false ? '仅下载' : '可预览' }}</span>
          </button>
        </div>
        <div v-else class="empty-inline">暂无正式报告文件。</div>
      </Panel>

      <Panel title="报告阅读器" :note="selectedReportFile?.name || 'view-model'">
        <div v-if="viewError" class="error-box">{{ viewError }}</div>
        <div v-else-if="reportViewLoading" class="empty-inline">正在加载报告正文...</div>
        <div v-else-if="reportView && !reportView.preview_supported" class="empty-inline">{{ reportView.message || '该格式仅下载，不支持预览。' }}</div>
        <article v-else-if="reportView" class="report-reader">
          <header class="report-reader-head">
            <span>{{ reportView.version || selectedReportFile?.version || 'report' }} · {{ reportView.format }}</span>
            <h3>{{ reportView.title }}</h3>
          </header>
          <section v-for="section in reportView.sections" :key="section.heading" class="report-section">
            <h4>{{ section.heading }}</h4>
            <template v-for="(block, index) in section.blocks" :key="`${section.heading}-${index}`">
              <p v-if="block.type === 'paragraph'">{{ block.text }}</p>
              <ul v-else-if="block.type === 'list'">
                <li v-for="item in block.items" :key="item">{{ item }}</li>
              </ul>
              <pre v-else>{{ block.text }}</pre>
            </template>
            <div v-for="child in section.children || []" :key="child.heading" class="report-subsection">
              <h5>{{ child.heading }}</h5>
              <template v-for="(block, index) in child.blocks" :key="`${child.heading}-${index}`">
                <p v-if="block.type === 'paragraph'">{{ block.text }}</p>
                <ul v-else-if="block.type === 'list'">
                  <li v-for="item in block.items" :key="item">{{ item }}</li>
                </ul>
                <pre v-else>{{ block.text }}</pre>
              </template>
            </div>
          </section>
        </article>
        <div v-else class="empty-inline">生成完成后会在这里显示报告正文。</div>
      </Panel>

      <div class="grid-2">
        <Panel title="下载 artifacts" note="多格式出口">
          <div v-if="reportFiles.length" class="file-list">
            <a v-for="file in reportFiles" :key="file.id" class="file-link" :href="file.url" download>
              <strong>{{ file.name }}</strong>
              <span>{{ file.version || 'report' }} · {{ appendixLabel(file.appendix) }} · {{ file.format || fileFormat(file.name) }}</span>
            </a>
          </div>
          <div v-else class="empty-inline">暂无可下载报告。</div>
        </Panel>

        <Panel title="结构化摘要" note="appendix_b">
          <div class="appendix-summary">
            <div><span>事件</span><strong>{{ appendixEventName }}</strong></div>
            <div><span>worlds</span><strong>{{ job?.appendix_b.worlds_count || 0 }}</strong></div>
            <div><span>risks</span><strong>{{ job?.appendix_b.confirmed_risks || 0 }}</strong></div>
            <div><span>等级分布</span><strong>{{ riskDistribution }}</strong></div>
          </div>
        </Panel>
      </div>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { api } from '../api/client';
import type { AppendixMode, BatchSummary, PageState as UiPageState, ReportFile, ReportJobResponse, ReportSkill, ReportVersion, ReportViewResponse, WorldStatus } from '../api/types';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StateTools from '../components/StateTools.vue';
import StepLine from '../components/StepLine.vue';
import { useRunStore } from '../stores/run';

const run = useRunStore();
const state = ref<UiPageState>('populated');
const errorMessage = ref('');
const viewError = ref('');
const selectedBatchId = ref('');
const history = ref<BatchSummary[]>([]);
const worlds = ref<WorldStatus[]>([]);
const versionOptions: ReportVersion[] = ['A', 'B', 'C'];
const selectedVersions = ref<ReportVersion[]>(['B']);
const appendixMode = ref<AppendixMode>('none');
const allowPartial = ref(false);
const skillId = ref('');
const reportSkills = ref<ReportSkill[]>([]);
const job = ref<ReportJobResponse | null>(null);
const selectedReportFileId = ref('');
const reportView = ref<ReportViewResponse | null>(null);
const reportViewLoading = ref(false);
let pollTimer: ReturnType<typeof setInterval> | undefined;

const completedCount = computed(() => worlds.value.filter((world) => world.status === 'completed').length);
const failedCount = computed(() => worlds.value.filter((world) => world.status === 'failed').length);
const datasetCount = computed(() => worlds.value.filter((world) => world.rows.some((row) => row.label === '数据集' && row.value)).length);
const reportFiles = computed(() => (job.value?.files || []).filter((file) => file.appendix !== 'data'));
const selectedReportFile = computed<ReportFile | undefined>(() => reportFiles.value.find((file) => file.id === selectedReportFileId.value));
const selectedModel = computed(() => run.models.find((model) => run.selectedModels.includes(model.id)));
const appendixPreview = computed(() => job.value?.appendix_b?.preview || {});
const appendixEventName = computed(() => String(appendixPreview.value.event_name || '暂无'));
const riskDistribution = computed(() => {
  const value = appendixPreview.value.risk_level_distribution;
  if (!value || typeof value !== 'object') return '暂无';
  return Object.entries(value as Record<string, unknown>).map(([key, count]) => `${key}:${count}`).join(' / ');
});
const disableReason = computed(() => {
  if (!selectedBatchId.value) return '请选择一个 batch。';
  if (!completedCount.value) return '没有 completed world，不能生成报告。';
  if (failedCount.value > 0 && !allowPartial.value) return '存在 failed world，请确认仅基于 completed worlds 生成。';
  if (!selectedVersions.value.length) return '至少选择一个报告版本。';
  return '';
});
const canGenerate = computed(() => !disableReason.value && job.value?.status !== 'running');

onMounted(async () => {
  await run.restoreActiveBatch();
  selectedBatchId.value = run.activeBatch.batchId || '';
  await Promise.all([loadReportSkills(), loadHistory(), loadWorlds(), restoreActiveJob()]);
});

onBeforeUnmount(stopPolling);
watch(selectedBatchId, () => {
  void loadWorlds();
});
watch(reportFiles, syncSelectedReportFile);
watch(selectedReportFileId, () => {
  void loadReportView();
});

async function loadReportSkills() {
  try {
    reportSkills.value = await api.getReportSkills();
  } catch {
    reportSkills.value = [];
  }
}

async function loadHistory() {
  try {
    history.value = await api.getHistory();
    if (!selectedBatchId.value && history.value.length) selectedBatchId.value = history.value[0].batchId;
  } catch {
    history.value = [];
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
    errorMessage.value = error instanceof Error ? error.message : 'world 列表读取失败';
  }
}

async function startReport() {
  if (!canGenerate.value) return;
  errorMessage.value = '';
  reportView.value = null;
  selectedReportFileId.value = '';
  job.value = await api.createReportJob({
    batch_id: selectedBatchId.value,
    versions: selectedVersions.value,
    appendix_mode: appendixMode.value,
    allow_partial: allowPartial.value,
    skill_id: skillId.value,
    gateway_id: selectedModel.value?.gatewayId,
    model_id: selectedModel.value?.id,
  });
  syncSelectedReportFile();
  startPolling();
}

async function restoreActiveJob() {
  try {
    const active = await api.getActiveReportJob();
    if (active.active && active.job) {
      job.value = active.job;
      syncSelectedReportFile();
      if (active.job.status === 'running') startPolling();
    }
  } catch {
    // non-blocking
  }
}

function syncSelectedReportFile() {
  if (!reportFiles.value.length) {
    selectedReportFileId.value = '';
    reportView.value = null;
    return;
  }
  if (!reportFiles.value.some((file) => file.id === selectedReportFileId.value)) {
    selectedReportFileId.value = reportFiles.value[0].id;
  } else {
    void loadReportView();
  }
}

async function loadReportView() {
  if (!job.value?.job_id || !selectedReportFileId.value) return;
  reportViewLoading.value = true;
  viewError.value = '';
  try {
    reportView.value = await api.getReportView(job.value.job_id, selectedReportFileId.value);
  } catch (error) {
    viewError.value = error instanceof Error ? error.message : '报告正文读取失败';
    reportView.value = null;
  } finally {
    reportViewLoading.value = false;
  }
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(pollJob, 2000);
  void pollJob();
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = undefined;
  }
}

async function pollJob() {
  if (!job.value?.job_id) return;
  try {
    job.value = await api.getReportJobStatus(job.value.job_id);
    syncSelectedReportFile();
    if (job.value.status !== 'running') stopPolling();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '报告状态轮询失败';
    stopPolling();
  }
}

function appendixLabel(value?: ReportFile['appendix']) {
  if (value === 'included') return '含附录';
  if (value === 'data') return '数据';
  return '无附录';
}

function fileFormat(name: string) {
  const suffix = name.split('.').pop()?.toLowerCase();
  return suffix || 'unknown';
}
</script>
