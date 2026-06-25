import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import Card from '../Card.vue';
import Chip from '../Chip.vue';
import Panel from '../Panel.vue';
import StepLine from '../StepLine.vue';

describe('design components', () => {
  it('renders Panel head and body', () => {
    const wrapper = mount(Panel, {
      props: { title: '事件材料', note: '必填' },
      slots: { default: '<div class="inside">content</div>' },
    });
    expect(wrapper.find('.panel-title').text()).toBe('事件材料');
    expect(wrapper.find('.panel-note').text()).toBe('必填');
    expect(wrapper.find('.inside').exists()).toBe(true);
  });

  it('renders Card content', () => {
    const wrapper = mount(Card, {
      props: { title: '说清楚事件', description: '描述', label: '指标', metric: true },
    });
    expect(wrapper.classes()).toContain('metric');
    expect(wrapper.text()).toContain('说清楚事件');
    expect(wrapper.text()).toContain('描述');
  });

  it('renders Chip variants', () => {
    const wrapper = mount(Chip, { props: { label: '通过', variant: 'ok' } });
    expect(wrapper.classes()).toContain('ok');
    expect(wrapper.text()).toBe('通过');
  });

  it('renders StepLine marker and chip', () => {
    const wrapper = mount(StepLine, {
      props: {
        title: '事件背景已填写',
        note: '可以进入下一步',
        status: 'done',
        chip: { label: '通过', variant: 'ok' },
      },
    });
    expect(wrapper.classes()).toContain('done');
    expect(wrapper.text()).toContain('✓');
    expect(wrapper.text()).toContain('通过');
  });
});
