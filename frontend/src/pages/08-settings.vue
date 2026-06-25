<template>
  <section class="workspace">
    <StateTools v-model="settings.pageState" />
    <PageState :state="settings.pageState" message="系统设置保存失败">
      <div class="grid-3">
        <Panel title="模型管理" note="可用模型">
          <div class="steps">
            <StepLine title="通义 80B" note="已启用" status="done" :chip="{ label: '正常', variant: 'ok' }" />
            <StepLine title="MiniMax" note="已启用" status="done" :chip="{ label: '正常', variant: 'ok' }" />
            <StepLine title="DeepSeek" note="暂不可用" status="current" :chip="{ label: '异常', variant: 'bad' }" />
          </div>
        </Panel>
        <Panel title="输出位置" note="任务产物">
          <div class="mock-note">当前设置只保存在前端状态；真实保存将在 v1.5.0b 写入后端 settings。</div>
          <div class="form-row"><label>默认保存目录</label><input v-model="settings.outputDir" /></div>
          <div class="form-row">
            <label>历史任务保留</label>
            <select v-model.number="settings.retentionDays">
              <option :value="30">保留 30 天</option>
              <option :value="7">保留 7 天</option>
              <option :value="3650">长期保留</option>
            </select>
          </div>
        </Panel>
        <Panel title="显示设置" note="界面偏好">
          <div class="steps">
            <StepLine title="业务语言优先" note="默认隐藏底层字段" status="done" :chip="{ label: '开启', variant: 'ok' }" />
            <StepLine title="技术详情" note="需要时展开查看" status="pending" :chip="{ label: settings.technicalMode ? '展开' : '折叠' }" />
          </div>
        </Panel>
      </div>
      <Panel title="系统检查" note="运行前自检">
        <div class="grid-4">
          <Card title="正常" label="模型接口" metric />
          <Card title="可写" label="任务目录" metric />
          <Card title="待接入" label="报告入口" metric />
          <Card title="正常" label="日志服务" metric />
        </div>
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import Card from '../components/Card.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StateTools from '../components/StateTools.vue';
import StepLine from '../components/StepLine.vue';
import { useSettingsStore } from '../stores/settings';

const settings = useSettingsStore();
</script>
