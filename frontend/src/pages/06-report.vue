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
            <button class="primary" type="button" :disabled="!canGenerate" @click="startReport">生成报告</button>
            <button class="ghost" type="button" :disabled="!job || job.status === 'running'" @click="restoreActiveJob">恢复最近报告</button>
          </div>
          <div v-if="disableReason" class="status-note">{{ disableReason }}</div>
        </Panel>

        <Panel title="报告选项" note="v1.5.2">
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
              <option value="default_government">政府研判</option>
              <option value="enterprise_brief">企业简报</option>
            </select>
          </div>
          <div class="status-note">模型使用 03-models 已选模型；未选择时后端回退 report/env 默认模型。</div>
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
        <div v-if="reportFiles.length" class="file-list">
          <a v-for="file in reportFiles" :key="file.id" class="file-link" :href="file.url" download>
            <strong>{{ file.name }}</strong>
            <span>{{ file.version || 'data' }} · {{ file.appendix || 'none' }}</span>
          </a>
        </div>
        <div v-else class="empty-inline">暂无正式报告文件。</div>
      </Panel>

      <Panel title="appendix_b.json" note="结构化审计产物">
        <div v-if="appendixFile" class="file-list compact">
          <a class="file-link" :href="appendixFile.url" download>
            <strong>{{ appendixFile.name }}</strong>
            <span>{{ job?.appendix_b.worlds_count || 0 }} worlds · {{ job?.appendix_b.confirmed_risks || 0 }} risks</span>
          </a>
        </div>
        <pre class="json-preview">{{ appendixPreview }}</pre>
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { api } from '../api/client';
import type { AppendixMode, BatchSummary, PageState as UiPageState, ReportFile, ReportJobResponse, ReportVersion, WorldStatus } from '../api/types';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StateTools from '../components/StateTools.vue';
import StepLine from '../components/StepLine.vue';
import { useRunStore } from '../stores/run';

const run = useRunStore();
const state = ref<UiPageState>('populated');
const errorMessage = ref('');
const selectedBatchId = ref('');
const history = ref<BatchSummary[]>([]);
const worlds = ref<WorldStatus[]>([]);
const versionOptions: ReportVersion[] = ['A', 'B', 'C'];
const selectedVersions = ref<ReportVersion[]>(['B']);
const appendixMode = ref<AppendixMode>('none');
const allowPartial = ref(false);
const skillId = ref('default_government');
const job = ref<ReportJobResponse | null>(null);
let pollTimer: ReturnType<typeof setInterval> | undefined;

const completedCount = computed(() => worlds.value.filter((world) => world.status === 'completed').length);
const failedCount = computed(() => worlds.value.filter((world) => world.status === 'failed').length);
const datasetCount = computed(() => worlds.value.filter((world) => world.rows.some((row) => row.label === '数据集' && row.value)).length);
const reportFiles = computed(() => (job.value?.files || []).filter((file) => file.appendix !== 'data'));
const appendixFile = computed<ReportFile | undefined>(() => (job.value?.files || []).find((file) => file.id === 'appendix_b'));
const appendixPreview = computed(() => JSON.stringify(job.value?.appendix_b?.preview || {}, null, 2));
const selectedModel = computed(() => run.models.find((model) => run.selectedModels.includes(model.id)));
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
  await Promise.all([loadHistory(), loadWorlds(), restoreActiveJob()]);
});

onBeforeUnmount(stopPolling);
watch(selectedBatchId, () => {
  void loadWorlds();
});

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
  job.value = await api.createReportJob({
    batch_id: selectedBatchId.value,
    versions: selectedVersions.value,
    appendix_mode: appendixMode.value,
    allow_partial: allowPartial.value,
    skill_id: skillId.value,
    gateway_id: selectedModel.value?.gatewayId,
    model_id: selectedModel.value?.id,
  });
  startPolling();
}

async function restoreActiveJob() {
  try {
    const active = await api.getActiveReportJob();
    if (active.active && active.job) {
      job.value = active.job;
      if (active.job.status === 'running') startPolling();
    }
  } catch {
    // non-blocking
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
    if (job.value.status !== 'running') stopPolling();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '报告状态轮询失败';
    stopPolling();
  }
}
</script>
