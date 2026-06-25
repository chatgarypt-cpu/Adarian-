<template>
  <section class="workspace">
    <StateTools v-model="settings.pageState" />
    <PageState :state="settings.pageState" message="系统设置保存失败">
      <div class="grid-3">
        <Panel title="模型管理" note="可用模型">
          <div class="steps">
            <StepLine title="模型接口" note="请在模型调度页执行网关健康检测" status="pending" :chip="{ label: '待检测' }" />
            <StepLine title="内置 catalog" note="由 /api/models 返回" status="done" :chip="{ label: '真实', variant: 'ok' }" />
            <StepLine title="用户网关" note="保存于 SQLite，密钥不回显" status="done" :chip="{ label: '持久化', variant: 'ok' }" />
          </div>
        </Panel>
        <Panel title="输出位置" note="任务产物">
          <div class="mock-note">设置通过 /api/settings 持久化；历史清理执行仍为后续能力。</div>
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
          <Card v-for="check in settings.systemChecks" :key="check.label" :title="check.status" :label="check.label" metric />
        </div>
        <div class="actions"><button class="primary" type="button" @click="settings.saveSettings">保存设置</button></div>
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import Card from '../components/Card.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StateTools from '../components/StateTools.vue';
import StepLine from '../components/StepLine.vue';
import { useSettingsStore } from '../stores/settings';

const settings = useSettingsStore();
onMounted(() => settings.loadSettings());
</script>
