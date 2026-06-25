<template>
  <section class="workspace">
    <StateTools v-model="history.pageState" />
    <PageState :state="history.pageState" message="历史任务加载失败">
      <Panel title="历史任务" note="最近批次">
        <div class="mock-note">当前历史任务来自 mock 数据；v1.5.0b 需接 SQLite/outputs/runs 真实索引。</div>
        <table class="table">
          <thead><tr><th>任务名称</th><th>创建时间</th><th>状态</th><th>主要风险</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="batch in history.batches" :key="batch.batchId">
              <td>{{ batch.name }}</td>
              <td>{{ batch.createdAt }}</td>
              <td><Chip :label="batch.status === 'running' ? '运行中' : '已完成'" :variant="batch.status === 'running' ? 'warn' : 'ok'" /></td>
              <td>{{ batch.risk }}</td>
              <td><button class="ghost" type="button">打开</button></td>
            </tr>
          </tbody>
        </table>
      </Panel>
      <Panel title="可复用内容" note="快速启动">
        <div class="grid-3">
          <Card title="复用事件材料" description="从历史任务复制事件描述和主体信息。" />
          <Card title="复用推演配置" description="沿用历史任务的轮数、模型和重点设置。" />
          <Card title="打开报告草稿" description="继续查看或导出已经生成的报告。" />
        </div>
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import Card from '../components/Card.vue';
import Chip from '../components/Chip.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StateTools from '../components/StateTools.vue';
import { useHistoryStore } from '../stores/history';

const history = useHistoryStore();
</script>
