<template>
  <section class="workspace">
    <StateTools v-model="seed.pageState" />
    <PageState :state="effectiveState" :message="seed.error">
      <div class="hero-grid">
        <Panel title="事件材料" note="必填">
          <div class="mock-note">当前真实可用：手动录入文本。 本地材料文件、历史事件复用为后续接入能力。</div>
          <div class="form-row">
            <label>舆情事件描述</label>
            <textarea v-model="seed.seedText" placeholder="请输入舆情事件描述" />
          </div>
          <div class="grid-2">
            <div class="form-row">
              <label>任务名称</label>
              <input v-model="seed.taskName" />
            </div>
            <div class="form-row">
              <label>材料来源</label>
              <select v-model="seed.source">
                <option>手动录入</option>
                <option>本地材料文件</option>
                <option>历史事件复用</option>
              </select>
            </div>
          </div>
          <div class="chips">
            <button v-for="item in examples" :key="item.label" class="chip" type="button" @click="seed.useExample(item.text)">
              {{ item.label }}
            </button>
          </div>
          <div class="actions">
            <button class="primary" type="button" :disabled="seed.isEmpty" @click="seed.saveSeed">保存事件材料</button>
            <button class="ghost" type="button" @click="seed.useExample(examples[0].text)">使用示例事件</button>
          </div>
        </Panel>

        <Panel title="录入检查" note="自动判断">
          <div class="mock-note">当前仅“事件背景已填写”可由前端真实判断；主体识别和时间线建议仍为 mock-only。</div>
          <div class="steps">
            <StepLine
              v-for="check in checks"
              :key="check.label"
              :title="check.label"
              :note="check.note"
              :status="check.status === 'passed' ? 'done' : check.status === 'suggested' ? 'current' : 'pending'"
              :chip="chipFor(check.status)"
            />
          </div>
        </Panel>
      </div>

      <Panel title="本阶段要完成什么" note="进入推演前">
        <div class="grid-3">
          <Card title="说清楚事件" description="让系统知道本次围绕什么争议展开推演。" />
          <Card title="明确关键主体" description="识别参与讨论的群体、机构和潜在利益方。" />
          <Card title="保留材料入口" description="后续可从本地文件或历史任务复用事件材料。" />
        </div>
      </Panel>
    </PageState>
    <div v-if="seed.saved" class="toast">事件材料已保存</div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import Card from '../components/Card.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StateTools from '../components/StateTools.vue';
import StepLine from '../components/StepLine.vue';
import { useSeedStore } from '../stores/seed';

const seed = useSeedStore();
const examples = [
  { label: '校园食品安全', text: '校园食堂食品安全争议在短视频平台发酵，学生、家长、商家和监管部门形成多方讨论。' },
  { label: '车企降价争议', text: '车企突然降价引发老车主不满，售后门店、媒体和品牌方进入持续争议。' },
  { label: '文旅接待争议', text: '热门文旅城市因接待体验争议被集中讨论，游客、商家和管理部门回应不一。' },
  { label: '平台投诉扩散', text: '平台投诉事件跨社区扩散，用户维权、企业回应和监管关注形成多方互动。' },
];

const effectiveState = computed(() => (seed.isEmpty && seed.pageState === 'populated' ? 'empty' : seed.pageState));
const checks = computed(() => (seed.isEmpty ? seed.checks.map((check) => ({ ...check, status: 'pending' as const })) : seed.checks));
const chipFor = (status: 'passed' | 'suggested' | 'pending') => {
  if (status === 'passed') return { label: '通过', variant: 'ok' as const };
  if (status === 'suggested') return { label: '建议', variant: 'warn' as const };
  return { label: '待补充' };
};
</script>
