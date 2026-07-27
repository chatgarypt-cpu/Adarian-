import { flushPromises, mount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import { describe, expect, it, vi } from 'vitest';
import RunPage from '../04-run.vue';
import WorldPage from '../09-world.vue';

vi.mock('../../api/client', () => ({
  api: {
    getWorldSummary: vi.fn().mockResolvedValue({
      id: 'batch:world_0',
      batch_id: 'batch',
      world_index: 0,
      model: 'm1',
      status: 'completed',
      run_dir: '/tmp/world_0',
      dataset: {
        available: true,
        state: 'available',
        dataset_path: '/tmp/world_0/simulation_dataset.json',
        event_entities_count: 1,
        opinions_count: 1,
        risk_verdict: { label: '高风险' },
        risk_type_classification: { type_labels: ['负向叙事聚合'] },
        source_context: {},
      },
      run_meta: {},
      elapsed_seconds: 3.4,
    }),
    getWorldTicks: vi.fn().mockResolvedValue({
      world_index: 0,
      model: 'm1',
      state: 'available',
      tick_logs_path: '/tmp/world_0/tick_logs.json',
      ticks: [{ tick: 1, entries: [{ group_name: '群体A', comment: '发言' }] }],
    }),
    getWorldLog: vi.fn().mockResolvedValue({
      batch_id: 'batch',
      world_index: 0,
      state: 'available',
      path: '/tmp/world_0/run.log',
      lines: ['RUN START', 'RUN END'],
    }),
    getWorldEvents: vi.fn().mockResolvedValue({
      batch_id: 'batch',
      world_index: 0,
      scope: 'world',
      events: [{ id: 'e1', scope: 'world', kind: 'phase_start', tone: 'run', title: '阶段开始', message: 'PHASE START' }],
    }),
  },
}));

describe('workflow page smoke', () => {
  it('mounts the run monitor fallback without real batch data', () => {
    const wrapper = mount(RunPage, {
      global: { plugins: [createPinia()] },
    });
    expect(wrapper.text()).toContain('尚未启动推演');
    expect(wrapper.text()).toContain('启动真实推演');
  });

  it('mounts the world detail page with mocked API data', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/world', component: WorldPage }],
    });
    router.push('/world?batch_id=batch&world_index=0');
    await router.isReady();

    const wrapper = mount(WorldPage, {
      global: { plugins: [createPinia(), router] },
    });
    await flushPromises();

    expect(wrapper.text()).toContain('World 摘要');
    expect(wrapper.text()).toContain('负向叙事聚合');
    expect(wrapper.text()).toContain('RUN END');
  });
});
