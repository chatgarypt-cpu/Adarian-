<template>
  <section class="workspace">
    <StateTools v-model="settings.pageState" />
    <PageState :state="settings.pageState" :message="settings.error || '系统设置保存失败'">
      <div class="hero-grid">
        <Panel title="报告模型" note="report slot">
          <div class="status-note">报告生成优先使用这里的默认配置；单次生成时仍可由报告页覆盖。</div>
          <div class="form-row">
            <label>模型网关</label>
            <select v-model="settings.reportGatewayId">
              <option value="">使用环境默认</option>
              <option v-for="gateway in settings.modelGateways" :key="gateway.id" :value="gateway.id">
                {{ gateway.name }} · {{ gateway.id }}
              </option>
            </select>
          </div>
          <div class="form-row">
            <label>报告模型</label>
            <input v-model="settings.reportModelId" placeholder="例如 qwen36-35b" />
          </div>
          <div class="grid-2">
            <div class="form-row">
              <label>温度</label>
              <input v-model.number="settings.reportTemperature" type="number" min="0" max="2" step="0.1" />
            </div>
            <div class="form-row">
              <label>最大 Token</label>
              <input v-model.number="settings.reportMaxTokens" type="number" min="512" max="65536" step="512" />
            </div>
          </div>
        </Panel>

        <Panel title="报告风格" note="skill">
          <div class="form-row">
            <label>默认写作风格</label>
            <select v-model="settings.reportSkillId">
              <option v-for="skill in settings.reportSkills" :key="skill.id" :value="skill.id">{{ skill.label }}</option>
            </select>
          </div>
          <div class="steps">
            <StepLine
              v-for="skill in settings.reportSkills"
              :key="skill.id"
              :title="skill.label"
              :note="skill.description || skill.id"
              :status="settings.reportSkillId === skill.id ? 'current' : 'pending'"
              :chip="{ label: settings.reportSkillId === skill.id ? '默认' : '可选', variant: settings.reportSkillId === skill.id ? 'ok' : undefined }"
            />
          </div>
        </Panel>
      </div>

      <div class="grid-3">
        <Panel title="输出位置" note="任务产物">
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
        <Panel title="保存" note="SQLite">
          <div class="status-note">设置通过 /api/settings 持久化，API key 不会从后端回显。</div>
          <div class="actions">
            <button class="primary" type="button" :disabled="settings.saving" @click="settings.saveSettings">
              {{ settings.saving ? '保存中...' : '保存设置' }}
            </button>
          </div>
        </Panel>
      </div>

      <Panel title="系统检查" note="运行前自检">
        <div class="grid-4">
          <Card v-for="check in settings.systemChecks" :key="check.label" :title="check.status" :label="check.label" metric />
        </div>
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
