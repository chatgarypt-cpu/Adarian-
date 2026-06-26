<template>
  <section class="workspace">
    <StateTools v-model="state" />
    <PageState :state="state" :message="errorMessage || '报告生成失败'">
      <div class="hero-grid">
        <Panel title="报告占位" note="v1.5.2 重构">
          <div class="status-note">报告生成将在 v1.5.2 重构；当前仅检查并下载 batch 中已有的报告文件。</div>
          <div class="form-row"><label>报告类型</label><select v-model="reportType"><option>舆情风险研判报告</option><option>领导摘要</option><option>内部复盘材料</option></select></div>
          <div class="form-row"><label>面向对象</label><select v-model="audience"><option>属地管理部门</option><option>监管部门</option><option>公安/执法协同</option><option>学校管理方</option></select></div>
          <div class="form-row"><label>使用结果</label><select v-model="source"><option>使用全部已完成推演</option><option>仅使用第 1 轮</option><option>仅使用第 2 轮</option></select></div>
          <div class="actions"><button class="primary" type="button" :disabled="!run.activeBatch.batchId" @click="generate">检查已有报告</button><button class="ghost" type="button">预览报告结构</button></div>
        </Panel>
        <Panel title="报告结构" note="五章式">
          <div class="steps">
            <StepLine v-for="(item, index) in structure" :key="item.title" :marker="index + 1" status="done" :title="item.title" :note="item.note" />
          </div>
        </Panel>
      </div>
      <Panel title="报告状态" :note="files.length ? '已生成' : '待生成'">
        <div v-if="errorMessage" class="error-box">{{ errorMessage }}</div>
        <div v-if="files.length" class="file-list">
          <a v-for="file in files" :key="file.id" class="file-link" :href="file.url" download>
            <strong>{{ file.name }}</strong>
            <span>下载报告文件</span>
          </a>
        </div>
        <div v-else class="empty">v1.5.1 仅保留报告入口；生成能力将在 v1.5.2 重构。</div>
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '../api/client';
import type { PageState as UiPageState, ReportFile } from '../api/types';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StateTools from '../components/StateTools.vue';
import StepLine from '../components/StepLine.vue';
import { useRunStore } from '../stores/run';

const run = useRunStore();
const state = ref<UiPageState>('populated');
const reportType = ref('舆情风险研判报告');
const audience = ref('属地管理部门');
const source = ref('使用全部已完成推演');
const files = ref<ReportFile[]>([]);
const errorMessage = ref('');
const structure = [
  { title: '舆情概要', note: '事件背景和当前态势' },
  { title: '演化分析', note: '多轮推演过程和趋势' },
  { title: '风险研判', note: '主要风险类型和等级' },
  { title: '对策建议', note: '舆情风险防范建议' },
  { title: '附录', note: '推演依据和结果摘要' },
];

onMounted(async () => {
  if (!run.activeBatch.batchId) {
    await run.restoreActiveBatch();
  }
});

async function generate() {
  if (!run.activeBatch.batchId) return;
  state.value = 'loading';
  errorMessage.value = '';
  try {
    const result = await api.generateReport(run.activeBatch.batchId, reportType.value, audience.value);
    files.value = result.files;
    state.value = 'populated';
  } catch (error) {
    files.value = [];
    errorMessage.value = error instanceof Error ? error.message : '报告生成失败';
    state.value = 'error';
  }
}
</script>
