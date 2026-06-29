import type { BatchSummary, ModelGateway, ModelSummary, ReportFile, RiskComparison, SeedResponse, SettingsResponse, WorldStatus } from './types';

export const delay = <T>(data: T, ms = 220): Promise<T> =>
  new Promise((resolve) => window.setTimeout(() => resolve(data), ms));

export const seedResponse: SeedResponse = {
  id: 'seed-campus-food',
  checks: [
    { label: '事件背景已填写', note: '可以进入下一步', status: 'passed' },
    { label: '核心主体已识别', note: '学生、家长、商家、监管部门', status: 'passed' },
    { label: '时间线可补充', note: '建议补充首发时间和官方回应时间', status: 'suggested' },
  ],
};

export const modelGateways: ModelGateway[] = [
  {
    id: 'internal',
    name: '默认内网中转站',
    baseUrl: 'http://127.0.0.1:8000/v1',
    provider: 'openai-compatible',
    status: 'connected',
    note: '自动识别 OpenAI-compatible 模型列表',
    hasApiKey: true,
    models: [
      { id: 'qwen80b', gatewayId: 'internal', name: 'qwen3-80b-tke', description: '推荐用于主推演。', selected: true, available: true, latency: '0.41 秒', advice: '推荐' },
      { id: 'qwen32b', gatewayId: 'internal', name: 'qwen3-32b-tke', description: '适合快速对照。', selected: false, available: true, latency: '0.52 秒', advice: '可参与对照' },
      { id: 'qwen35b', gatewayId: 'internal', name: 'qwen36-35b', description: '当前主力基线模型。', selected: false, available: true, latency: '0.66 秒', advice: '稳定基线' },
    ],
  },
  {
    id: 'minimax',
    name: 'MiniMax 网关',
    baseUrl: 'https://api.minimax.chat/v1',
    provider: 'minimax',
    status: 'connected',
    note: '语言表达对照模型池',
    hasApiKey: true,
    models: [
      { id: 'minimax-text', gatewayId: 'minimax', name: 'MiniMax-Text-01', description: '适合报告语气和文本表达对照。', selected: true, available: true, latency: '0.45 秒', advice: '可参与对照' },
      { id: 'minimax-long', gatewayId: 'minimax', name: 'MiniMax-LongContext', description: '适合长材料归纳。', selected: false, available: true, latency: '0.71 秒', advice: '长文本备选' },
    ],
  },
  {
    id: 'deepseek',
    name: 'DeepSeek 网关',
    baseUrl: 'https://api.deepseek.com/v1',
    provider: 'deepseek',
    status: 'offline',
    note: '当前连接异常，保留为后续接入位',
    hasApiKey: false,
    models: [
      { id: 'deepseek-chat', gatewayId: 'deepseek', name: 'deepseek-chat', description: '当前连接异常。', selected: false, available: false, advice: '暂不使用' },
      { id: 'deepseek-reasoner', gatewayId: 'deepseek', name: 'deepseek-reasoner', description: '推理对照模型。', selected: false, available: false, advice: '等待网关恢复' },
    ],
  },
];

export const models: ModelSummary[] = modelGateways.flatMap((gateway) => gateway.models);

export const worlds: WorldStatus[] = [
  {
    id: 'world-1',
    round: '第 1 轮推演',
    model: '通义 80B',
    status: 'completed',
    rows: [
      { label: '结果数据', value: '已生成', tone: 'ok' },
      { label: '主要风险', value: '3 类' },
      { label: '耗时', value: '119.9 秒' },
    ],
  },
  {
    id: 'world-2',
    round: '第 2 轮推演',
    model: 'MiniMax',
    status: 'completed',
    rows: [
      { label: '结果数据', value: '已生成', tone: 'ok' },
      { label: '主要风险', value: '3 类' },
      { label: '耗时', value: '98.2 秒' },
    ],
  },
  {
    id: 'world-3',
    round: '第 3 轮推演',
    model: '通义 32B',
    status: 'running',
    rows: [
      { label: '结果数据', value: '生成中', tone: 'warn' },
      { label: '当前阶段', value: '演化模拟' },
      { label: '已运行', value: '42.8 秒' },
    ],
  },
];

export const logs = `[17:37:56] 推演任务已创建：校园食品安全_batch
[17:37:56] 第 1 轮推演开始：通义 80B
[17:39:56] 第 1 轮推演完成：识别 3 类主要风险
[17:40:08] 第 2 轮推演开始：MiniMax
[17:41:46] 第 2 轮推演完成：识别 3 类主要风险
[17:42:02] 第 3 轮推演开始：通义 32B`;

export const riskComparison: RiskComparison[] = [
  { world: '第 1 轮', risks: '负面叙事聚集、群体分化、平台外溢', level: '中风险', levelVariant: 'warn', status: '可用', statusVariant: 'ok' },
  { world: '第 2 轮', risks: '群体分化、监管压力、负面叙事聚集', level: '中风险', levelVariant: 'warn', status: '可用', statusVariant: 'ok' },
  { world: '第 3 轮', risks: '生成中', level: '待定', status: '运行中', statusVariant: 'warn' },
];

export const reportFiles: ReportFile[] = [
  { id: 'report-1', name: '校园食品安全争议舆情风险研判报告.md', url: '#' },
  { id: 'report-2', name: '领导摘要.md', url: '#' },
];

export const history: BatchSummary[] = [
  { batchId: 'campus-food', name: '校园食品安全争议推演', createdAt: '今天 17:37', status: 'running', risk: '3 类' },
  { batchId: 'auto-price', name: '车企降价争议推演', createdAt: '昨天 21:14', status: 'completed', risk: '4 类' },
  { batchId: 'tourism-service', name: '文旅接待争议推演', createdAt: '昨天 16:28', status: 'completed', risk: '3 类' },
];

export const settings: SettingsResponse = {
  maxConcurrent: 3,
  outputDir: 'outputs/runs/',
  retentionDays: 30,
  technicalMode: false,
  report_gateway_id: '',
  report_model_id: '',
  report_temperature: 0.3,
  report_max_tokens: 8192,
  report_skill_id: 'default_government',
};
