<template>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <div class="eyebrow">ADARIAN CONSOLE</div>
        <h1>舆情推演工作台</h1>
        <p>按流程完成事件录入、推演运行、结果审查与报告生成。</p>
      </div>
      <nav class="nav">
        <button
          v-for="page in pages"
          :key="page.path"
          :class="{ active: route.path === page.path }"
          type="button"
          @click="router.push(page.path)"
        >
          <span class="num">{{ page.n }}</span>
          <span>
            <span class="nav-title">{{ page.title }}</span>
            <span class="nav-sub">{{ page.sub }}</span>
          </span>
          <span class="nav-state">{{ route.path === page.path ? '●' : '○' }}</span>
        </button>
      </nav>
    </aside>

    <main class="main">
      <section class="topbar">
        <div class="title-wrap">
          <div class="eyebrow">第 {{ activePage.n }} 步</div>
          <h2>{{ activePage.title }}</h2>
          <p>{{ activePage.desc }}</p>
        </div>
        <div class="status-strip">
          <Mini label="系统状态" value="就绪" />
          <Mini label="当前任务" value="未启动" />
          <Mini label="今日批次" value="3" />
        </div>
      </section>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Mini from './components/Mini.vue';
import { useRunStore } from './stores/run';
import { useHistoryStore } from './stores/history';

const pages = [
  { path: '/seed', n: '01', title: '事件录入', sub: '输入材料', desc: '录入本次需要推演的舆情事件，明确事件背景、核心争议和材料来源。' },
  { path: '/config', n: '02', title: '推演配置', sub: '设置任务', desc: '设置推演规模、推演重点和输出内容，确认任务准备情况。' },
  { path: '/models', n: '03', title: '模型调度', sub: '选择模型', desc: '选择参与推演的模型，检测可用性，并给出调度建议。' },
  { path: '/run', n: '04', title: '运行监控', sub: '查看进度', desc: '查看每一轮平行推演的运行状态、结果产物和最新日志。' },
  { path: '/review', n: '05', title: '结果审查', sub: '比较结论', desc: '对比多轮推演结果，识别稳定风险、差异风险和可用证据。' },
  { path: '/report', n: '06', title: '报告生成', sub: '形成材料', desc: '选择推演结果和面向对象，生成舆情风险研判报告草稿。' },
  { path: '/history', n: '07', title: '历史任务', sub: '复用结果', desc: '查看历史推演任务，复用事件材料、推演配置和报告草稿。' },
  { path: '/settings', n: '08', title: '系统设置', sub: '管理能力', desc: '管理模型、输出位置、显示方式和系统检查项。' },
];

const detailPages = [
  { path: '/world', n: '详情', title: 'World 详情', sub: '单轮证据', desc: '查看单个平行世界的摘要、事件流、智能体发言和运行日志。' },
];

const route = useRoute();
const router = useRouter();
const runStore = useRunStore();
const historyStore = useHistoryStore();
const activePage = computed(() => pages.find((page) => page.path === route.path) ?? detailPages.find((page) => page.path === route.path) ?? pages[0]);

onMounted(async () => {
  try {
    await Promise.all([runStore.hydrate(), historyStore.fetchHistory()]);
  } catch {
    runStore.modelsState = 'error';
    historyStore.pageState = 'error';
  }
});
</script>
