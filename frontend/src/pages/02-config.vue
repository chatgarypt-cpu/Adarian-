<template>
  <section class="workspace">
    <PageState state="populated" message="配置校验失败">
      <div class="hero-grid">
        <Panel title="任务配置" note="真实生效">
          <div class="form-row"><label>输出批次名称</label><input v-model="run.config.batchName" /></div>
          <div class="status-note">每个已选择模型会创建一个独立 world；模拟参数由当前 WorkflowBase 运行配置管理。</div>
          <div class="actions">
            <button class="primary" type="button" :disabled="run.configSaving" @click="run.saveConfig">
              {{ run.configSaving ? '保存中...' : '保存配置' }}
            </button>
          </div>
        </Panel>

        <Panel title="启动条件" note="运行前确认">
          <div class="steps">
            <StepLine
              title="参与模型"
              :note="run.selectedModelCount ? `${run.selectedModelCount} 个模型已选择` : '请先在模型调度页选择模型'"
              :status="run.selectedModelCount ? 'done' : 'current'"
              :chip="{ label: run.selectedModelCount ? '已就绪' : '待选择', variant: run.selectedModelCount ? 'ok' : 'warn' }"
            />
            <StepLine title="运行方式" note="一个模型对应一个平行 world" status="done" :chip="{ label: '固定', variant: 'ok' }" />
          </div>
        </Panel>
      </div>

      <Panel title="真实产物" note="运行完成后">
        <div class="steps">
          <StepLine title="simulation_dataset" note="供结果审查和报告生成消费" status="done" :chip="{ label: '结构化数据', variant: 'ok' }" />
          <StepLine title="运行日志与事件流" note="供运行台实时监控和错误定位" status="done" :chip="{ label: '可观测', variant: 'ok' }" />
        </div>
      </Panel>
    </PageState>
  </section>
</template>

<script setup lang="ts">
import PageState from '../components/PageState.vue';
import Panel from '../components/Panel.vue';
import StepLine from '../components/StepLine.vue';
import { useRunStore } from '../stores/run';

const run = useRunStore();
</script>
