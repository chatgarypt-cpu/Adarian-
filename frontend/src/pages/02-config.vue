<template>
  <section class="workspace">
    <StateTools v-model="state" />
    <PageState :state="state" message="配置校验失败">
      <div class="grid-3">
        <Panel title="推演规模" note="任务参数">
          <div class="mock-note">当前配置只影响前端预览，不会传入真实推演。v1.5.0b 需接入 /api/config 与 /api/run。</div>
          <div class="form-row"><label>平行推演轮数</label><input v-model.number="run.config.parallelWorlds" type="number" min="1" /></div>
          <div class="form-row"><label>每轮模拟步数</label><input v-model.number="run.config.ticks" type="number" min="1" /></div>
          <div class="form-row"><label>输出批次名称</label><input v-model="run.config.batchName" /></div>
        </Panel>
        <Panel title="推演重点" note="业务目标">
          <div class="mock-note">推演重点 chips 仍为产品占位，尚未影响 Phase 或报告逻辑。</div>
          <div class="chips">
            <button
              v-for="focus in focuses"
              :key="focus"
              class="chip"
              :class="{ ok: run.config.focuses.includes(focus) }"
              type="button"
              @click="toggleFocus(focus)"
            >
              {{ focus }}
            </button>
          </div>
          <div class="actions"><button class="ghost" type="button">添加重点</button></div>
        </Panel>
        <Panel title="输出内容" note="生成范围">
          <div class="steps">
            <StepLine title="推演结果数据" note="用于结果审查" status="done" :chip="{ label: '开启', variant: 'ok' }" />
            <StepLine title="运行日志" note="用于复盘排错" status="done" :chip="{ label: '开启', variant: 'ok' }" />
            <StepLine title="报告草稿" note="运行完成后生成" status="pending" :chip="{ label: '后续' }" />
          </div>
        </Panel>
      </div>
      <Panel title="配置预览" note="启动前确认">
        <div class="grid-4">
          <Card :title="String(run.config.parallelWorlds)" label="平行轮数" metric />
          <Card :title="String(run.config.ticks)" label="模拟步数" metric />
          <Card :title="String(run.config.focuses.length)" label="推演重点" metric />
          <Card title="3 类" label="预计产物" metric />
        </div>
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import type { PageState as UiPageState } from '../api/types';
import Card from '../components/Card.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StateTools from '../components/StateTools.vue';
import StepLine from '../components/StepLine.vue';
import { useRunStore } from '../stores/run';

const run = useRunStore();
const state = ref<UiPageState>('populated');
const focuses = ['风险扩散', '群体分化', '官方回应', '平台外溢'];

function toggleFocus(focus: string) {
  run.config.focuses = run.config.focuses.includes(focus)
    ? run.config.focuses.filter((item) => item !== focus)
    : [...run.config.focuses, focus];
}
</script>
