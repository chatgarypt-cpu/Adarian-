<template>
  <section class="workspace">
    <StateTools v-model="run.modelsState" />
    <PageState :state="effectiveState" message="模型检测失败">
      <Panel title="API 服务管理" note="v1.5.0a mock 入口">
        <div class="mock-note">当前只做前端临时添加；真实保存、密钥保护、模型识别和健康检查在 v1.5.0b 后端实现。</div>
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
          <button class="ghost" type="button">识别模型（后端接入后启用）</button>
        </div>
      </Panel>
      <Panel title="模型中转站" note="按 API 地址识别模型">
        <div class="mock-note">当前模型网关和模型列表来自 mock 数据，不代表真实 API 服务已完成识别。</div>
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
            <StepLine title="主模型已选择" note="通义 80B" status="done" :chip="{ label: '通过', variant: 'ok' }" />
            <StepLine title="对照模型已选择" note="MiniMax" status="done" :chip="{ label: '通过', variant: 'ok' }" />
            <StepLine title="异常模型已排除" note="避免任务启动失败" status="current" :chip="{ label: '注意', variant: 'warn' }" />
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
