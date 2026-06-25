<template>
  <section class="workspace">
    <StateTools v-model="state" />
    <PageState :state="effectiveState" message="审查结果读取失败">
      <div class="hero-grid">
        <Panel title="主要风险对比" note="多轮结果汇总">
          <div class="mock-note">当前风险对比来自 mock 数据；v1.5.0b 需要从真实 batch 产物聚合。</div>
          <table class="table">
            <thead><tr><th>推演轮次</th><th>主要风险</th><th>风险等级</th><th>结果状态</th></tr></thead>
            <tbody>
              <tr v-for="item in rows" :key="item.world">
                <td>{{ item.world }}</td>
                <td>{{ item.risks }}</td>
                <td><Chip :label="item.level" :variant="item.levelVariant" /></td>
                <td><Chip :label="item.status" :variant="item.statusVariant" /></td>
              </tr>
            </tbody>
          </table>
        </Panel>
        <Panel title="审查结论" note="供报告生成使用">
          <div class="steps">
            <StepLine title="风险类型基本一致" note="多轮结果均识别出叙事聚集与群体分化。" status="done" :chip="{ label: '稳定', variant: 'ok' }" />
            <StepLine title="第三轮仍在运行" note="报告生成前建议等待全部完成。" status="current" :chip="{ label: '等待', variant: 'warn' }" />
            <StepLine title="可进入报告准备" note="已有两轮可用结果。" status="pending" :chip="{ label: '可选' }" />
          </div>
        </Panel>
      </div>
      <Panel title="结果证据" note="默认展示业务结论">
        <div class="grid-3">
          <Card title="负面叙事聚集" description="多轮推演中均出现集中质疑食品安全、监管责任和学校回应的讨论。" />
          <Card title="群体分化" description="学生、家长、商家与管理部门之间的判断差异逐渐扩大。" />
          <Card title="平台外溢" description="短视频平台讨论可能带动媒体转载和跨平台扩散。" />
        </div>
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { api } from '../api/client';
import type { PageState as UiPageState, RiskComparison } from '../api/types';
import Card from '../components/Card.vue';
import Chip from '../components/Chip.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StateTools from '../components/StateTools.vue';
import StepLine from '../components/StepLine.vue';

const state = ref<UiPageState>('populated');
const rows = ref<RiskComparison[]>([]);
const effectiveState = computed(() => (state.value === 'populated' && rows.value.length === 0 ? 'empty' : state.value));

onMounted(async () => {
  rows.value = await api.getReview();
});
</script>
