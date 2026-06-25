<template>
  <section class="workspace">
    <StateTools v-model="run.modelsState" />
    <PageState :state="effectiveState" message="模型检测失败">
      <Panel title="API 服务管理" note="后端持久化">
        <div class="mock-note">用户新增服务保存到 SQLite；API key write-only，不会回显明文。</div>
        <div class="grid-4">
          <div class="form-row">
            <label>服务名称</label>
            <input v-model="run.gatewayDraft.name" placeholder="例如：自建 OpenAI 中转站" />
          </div>
          <div class="form-row">
            <label>Base URL</label>
            <input v-model="run.gatewayDraft.baseUrl" placeholder="https://example.com/v1" />
          </div>
          <div class="form-row">
            <label>服务类型</label>
            <select v-model="run.gatewayDraft.provider">
              <option value="openai-compatible">OpenAI-compatible</option>
              <option value="minimax">MiniMax</option>
              <option value="deepseek">DeepSeek</option>
              <option value="custom">自定义</option>
            </select>
          </div>
          <div class="form-row">
            <label>API Key</label>
            <input v-model="run.gatewayDraft.apiKey" type="password" placeholder="v1.5.0b 后端 write-only 保存" />
          </div>
        </div>
        <div class="actions">
          <button class="primary" type="button" @click="run.addGateway">添加 API 服务</button>
          <button class="ghost" type="button" @click="run.hydrate">刷新网关</button>
        </div>
      </Panel>
      <Panel title="模型中转站" note="按 API 地址识别模型">
        <div class="mock-note">内置 catalog 与用户网关动态发现分开展示；失败会返回明确错误。</div>
        <div class="gateway-list">
          <section v-for="gateway in run.modelGateways" :key="gateway.id" class="gateway">
            <button class="gateway-head" type="button" @click="run.toggleGateway(gateway.id)">
              <span class="num">{{ run.expandedGatewayIds.includes(gateway.id) ? '−' : '+' }}</span>
              <span>
                <strong>{{ gateway.name }}</strong>
                <small>{{ gateway.baseUrl }} · {{ providerLabel(gateway.provider) }} · {{ gateway.hasApiKey ? '密钥已配置' : '未配置密钥' }}</small>
              </span>
              <Chip :label="gatewayStatus(gateway.status).label" :variant="gatewayStatus(gateway.status).variant" />
            </button>
            <div v-if="run.expandedGatewayIds.includes(gateway.id)" class="gateway-body">
              <p>{{ gateway.note }}</p>
              <div class="actions">
                <button class="ghost" type="button" @click="run.discoverModels(gateway.id)">识别模型</button>
              </div>
              <div class="model-column">
                <button
                  v-for="model in gateway.models"
                  :key="model.id"
                  class="model-row"
                  :class="{ selected: model.selected }"
                  type="button"
                  :disabled="!model.available"
                  @click="run.toggleModel(model.id)"
                >
                  <span class="model-main">
                    <strong>{{ model.name }}</strong>
                    <small>{{ model.description }}</small>
                  </span>
                  <span class="model-meta">
                    <Chip :label="model.selected ? '已选择' : '未选择'" :variant="model.selected ? 'ok' : undefined" />
                    <Chip :label="model.available ? '可用' : '不可用'" :variant="model.available ? 'ok' : 'bad'" />
                    <span>{{ model.latency ?? '--' }}</span>
                  </span>
                </button>
              </div>
            </div>
          </section>
        </div>
      </Panel>
      <div class="hero-grid">
        <Panel title="可用性检测" note="运行前检查">
          <table class="table">
            <thead><tr><th>模型</th><th>状态</th><th>响应时间</th><th>建议</th></tr></thead>
            <tbody>
              <tr v-for="model in run.models" :key="model.id">
                <td>{{ model.name }}</td>
                <td><Chip :label="model.available ? '可用' : '失败'" :variant="model.available ? 'ok' : 'bad'" /></td>
                <td>{{ model.latency ?? '--' }}</td>
                <td>{{ model.advice }}</td>
              </tr>
            </tbody>
          </table>
          <div class="actions">
            <button class="primary" type="button" @click="run.hydrate">重新检测</button>
            <button class="ghost" type="button" @click="run.selectAvailableModels">只选择可用模型</button>
          </div>
        </Panel>
        <Panel title="调度建议" note="自动推荐">
          <div class="steps">
            <StepLine title="模型来自后端" note="内置 catalog 或网关 discover" status="done" :chip="{ label: '真实', variant: 'ok' }" />
            <StepLine title="密钥不回显" note="仅显示 hasApiKey" status="done" :chip="{ label: '通过', variant: 'ok' }" />
            <StepLine title="运行前选择模型" note="可直接选可用模型启动 batch" status="current" :chip="{ label: '注意', variant: 'warn' }" />
          </div>
        </Panel>
      </div>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ChipVariant, ModelGateway } from '../api/types';
import Chip from '../components/Chip.vue';
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StateTools from '../components/StateTools.vue';
import StepLine from '../components/StepLine.vue';
import { useRunStore } from '../stores/run';

const run = useRunStore();
const effectiveState = computed(() => (run.modelsState === 'populated' && run.modelGateways.length === 0 ? 'empty' : run.modelsState));
const gatewayStatus = (status: string): { label: string; variant?: ChipVariant } => {
  if (status === 'connected') return { label: '已连接', variant: 'ok' };
  if (status === 'partial') return { label: '部分可用', variant: 'warn' };
  return { label: '离线', variant: 'bad' };
};
const providerLabel = (provider: ModelGateway['provider']) => {
  if (provider === 'openai-compatible') return 'OpenAI-compatible';
  if (provider === 'minimax') return 'MiniMax';
  if (provider === 'deepseek') return 'DeepSeek';
  return '自定义';
};
</script>
