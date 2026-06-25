<template>
  <section class="workspace">
    <StateTools v-model="state" />
    <PageState :state="state" message="报告生成失败">
      <div class="hero-grid">
        <Panel title="报告生成" note="选择推演结果">
          <div class="mock-note">报告生成调用 Phase 4 API；没有 completed world 的 simulation_dataset 会返回明确错误。</div>
          <div class="form-row"><label>报告类型</label><select v-model="reportType"><option>舆情风险研判报告</option><option>领导摘要</option><option>内部复盘材料</option></select></div>
          <div class="form-row"><label>面向对象</label><select v-model="audience"><option>属地管理部门</option><option>监管部门</option><option>公安/执法协同</option><option>学校管理方</option></select></div>
          <div class="form-row"><label>使用结果</label><select v-model="source"><option>使用全部已完成推演</option><option>仅使用第 1 轮</option><option>仅使用第 2 轮</option></select></div>
          <div class="actions"><button class="primary" type="button" :disabled="!run.activeBatch.batchId" @click="generate">生成报告草稿</button><button class="ghost" type="button">预览报告结构</button></div>
        </Panel>
        <Panel title="报告结构" note="五章式">
          <div class="steps">
            <StepLine v-for="(item, index) in structure" :key="item.title" :marker="index + 1" status="done" :title="item.title" :note="item.note" />
          </div>
        </Panel>
      </div>
      <Panel title="报告状态" :note="files.length ? '已生成' : '待生成'">
        <div v-if="files.length" class="grid-2">
          <Card v-for="file in files" :key="file.id" :title="file.name" description="报告草稿已生成，可在真实 API 接入后下载。" />
        </div>
        <div v-else class="empty">选择报告类型和使用结果后，可以生成报告草稿。</div>
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { api } from '../api/client';
import type { PageState as UiPageState, ReportFile } from '../api/types';
import Card from '../components/Card.vue';
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
const structure = [
  { title: '舆情概要', note: '事件背景和当前态势' },
  { title: '演化分析', note: '多轮推演过程和趋势' },
  { title: '风险研判', note: '主要风险类型和等级' },
  { title: '对策建议', note: '舆情风险防范建议' },
  { title: '附录', note: '推演依据和结果摘要' },
];

async function generate() {
  if (!run.activeBatch.batchId) return;
  state.value = 'loading';
  try {
    const result = await api.generateReport(run.activeBatch.batchId, reportType.value, audience.value);
    files.value = result.files;
    state.value = 'populated';
  } catch {
    files.value = [];
    state.value = 'error';
  }
}
</script>
