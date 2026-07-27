<template>
  <section class="workspace">
    <PageState :state="settings.pageState" :message="settings.error || '系统设置保存失败'">
      <div class="hero-grid">
        <Panel title="报告模型" note="report slot">
          <div class="status-note">报告生成使用这里保存的默认模型和生成参数。</div>
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

      <Panel title="保存报告配置" note="SQLite">
        <div class="status-note">设置通过 /api/settings 持久化，API key 不会从后端回显。</div>
        <div class="actions">
          <button class="primary" type="button" :disabled="settings.saving" @click="settings.saveSettings">
            {{ settings.saving ? '保存中...' : '保存设置' }}
          </button>
        </div>
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StepLine from '../components/StepLine.vue';
import { useSettingsStore } from '../stores/settings';

const settings = useSettingsStore();
onMounted(() => settings.loadSettings());
</script>
