<template>
  <section class="workspace">
    <PageState :state="effectiveState" :message="seed.error">
      <div class="hero-grid">
        <Panel title="事件材料" note="必填">
          <div class="status-note">支持手动录入文本和读取本地 seed 文件。</div>
          <div class="form-row">
            <label>舆情事件描述</label>
            <textarea v-model="seed.seedText" :disabled="seed.source === 'file'" placeholder="请输入舆情事件描述" />
          </div>
          <div class="grid-2">
            <div class="form-row">
              <label>任务名称</label>
              <input v-model="seed.taskName" />
            </div>
            <div class="form-row">
              <label>材料来源</label>
              <select v-model="seed.source">
                <option value="manual">手动录入</option>
                <option value="file">本地 seed 路径</option>
              </select>
            </div>
          </div>
          <div v-if="seed.source === 'file'" class="form-row">
            <label>本地 seed 文件路径</label>
            <div class="form-row-inline">
              <input v-model="seed.seedPath" placeholder="seeds/test8.txt" />
              <button class="ghost" type="button" :disabled="!seed.seedPath.trim() || seed.pageState === 'loading'" @click="seed.loadFile">
                <span v-if="seed.pageState === 'loading'" class="btn-icon"></span>
                读取内容
              </button>
            </div>
          </div>
          <div class="chips">
            <button v-for="item in examples" :key="item.label" class="chip" type="button" @click="seed.useExample(item.text)">
              {{ item.label }}
            </button>
            <button class="chip" type="button" @click="seed.useLocalTest8">本地 test8</button>
          </div>
          <div class="actions">
            <button class="primary" type="button" :disabled="seed.isEmpty || seed.pageState === 'loading'" @click="seed.saveSeed">
              <span v-if="seed.pageState === 'loading'" class="btn-icon"></span>
              保存事件材料
            </button>
            <button class="ghost" type="button" @click="seed.useExample(examples[0].text)">使用预设事件</button>
          </div>
        </Panel>

        <Panel title="录入检查" note="内容完整性">
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
          <Card title="确认材料来源" description="可直接录入文本，也可读取项目内的 seed 文件。" />
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
import StepLine from '../components/StepLine.vue';
import { useSeedStore } from '../stores/seed';

const seed = useSeedStore();
const examples = [
  { label: '校园食品安全', text: '校园食堂食品安全争议在短视频平台发酵，学生、家长、商家和监管部门形成多方讨论。' },
  { label: '车企降价争议', text: '车企突然降价引发老车主不满，售后门店、媒体和品牌方进入持续争议。' },
  { label: '文旅接待争议', text: '热门文旅城市因接待体验争议被集中讨论，游客、商家和管理部门回应不一。' },
  { label: '平台投诉扩散', text: '平台投诉事件跨社区扩散，用户维权、企业回应和监管关注形成多方互动。' },
];

const effectiveState = computed(() => seed.pageState);
const checks = computed(() => {
  if (seed.isCurrentSaved) return seed.checks;
  return [{
    label: '事件材料待保存',
    note: seed.isEmpty ? '请先填写事件材料' : '保存后完成录入检查',
    status: 'pending' as const,
  }];
});
const chipFor = (status: 'passed' | 'suggested' | 'pending') => {
  if (status === 'passed') return { label: '通过', variant: 'ok' as const };
  if (status === 'suggested') return { label: '建议', variant: 'warn' as const };
  return { label: '待补充' };
};
</script>
