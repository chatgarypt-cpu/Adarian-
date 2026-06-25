# Adarian 前端设计规格 (Frontend Spec)

> 基于 `adarian_frontend_sidebar_prototype_v2.html` 提取。
> v1.5.0a/b/c 三份计划的前端实现参考。

---

## 1. 设计系统 (Design System)

### 1.1 布局

```
.app {
  display: grid;
  grid-template-columns: 268px 1fr;   /* 左侧边栏 + 右侧主内容区 */
  min-height: 100vh;
}
```

- 左侧侧边栏固定 268px，半透明毛玻璃效果（`backdrop-filter: blur(16px)`）
- 右侧主内容区可滚动（`height: 100vh; overflow: auto`）
- 深色科技风背景：网格线叠加（42px 间距）、径向渐变光晕

### 1.2 颜色

| Token | 值 | 用途 |
|-------|-----|------|
| `--bg` | `#06111f` | 主背景 |
| `--panel` | `rgba(9,24,42,.78)` | 面板背景 |
| `--line` | `rgba(81,220,255,.24)` | 边框（默认） |
| `--line2` | `rgba(81,220,255,.58)` | 边框（高亮） |
| `--cyan` | `#51dcff` | 主色调、品牌色、激活状态 |
| `--blue` | `#1f8cff` | 强调色、部分按钮 |
| `--green` | `#35f0a0` | 成功/已完成 |
| `--red` | `#ff5e73` | 失败/错误 |
| `--amber` | `#f2c94c` | 警告/注意 |
| `--text` | `#e8f7ff` | 主文字 |
| `--muted` | `#88a8bd` | 辅助文字 |

### 1.3 组件

**Panel** — 圆角面板容器
```
border: 1px solid var(--line);
background: var(--panel);
border-radius: 12px;
.panel-head { padding: 14px 16px; border-bottom }
.panel-title { font-weight: 720 }
.panel-note { color: var(--muted); font-size: 12px }
.panel-body { padding: 16px }
```

**Card** — 内部卡片
```
border: 1px solid rgba(81,220,255,.18);
background: rgba(2,10,18,.48);
border-radius: 10px;
padding: 14px;
.card strong { font-size: 16px }
.card p { color: var(--muted); font-size: 13px }
```

**Chip** — 标签/状态标记
```
已选择/可用 → .chip.ok { background: var(--green) 或绿色边框 }
未选择/待定 → .chip { 默认边框 }
不可用/异常 → .chip.bad { border-color: var(--red); color: var(--red) }
建议/注意 → .chip.warn { border-color: var(--amber); color: var(--amber) }
```

**StepLine** — 步骤/检查项
```
.step-line: grid, 含左侧标记（✓ / ! / ○ / 数字）、中间标题+说明、右侧状态芯片
.done → 已完成（含 ✓）
.current → 当前步骤（含 !）
```

**Mini** — 顶部统计数据
```
border: 1px solid var(--line);
padding: 10px 12px;
.mini span { color: var(--muted); font-size: 12px }
.mini strong { font-size: 18px }
```

**World status card** — 运行监控中的推演轮次状态
```
.world-top { 第 N 轮推演 + 状态徽章 }
.world h3 { 模型名称 }
.ev { 指标行：结果数据 / 主要风险 / 耗时 }
.badge.ok { 已完成 }
.badge.run { 运行中 }
```

**LogBox** — 运行日志
```
背景半透明，monospace 字体
```

**Table** — 数据表格
```
标准 table + thead + tbody，行内 chip 状态标记
```

**Button** — 按钮
```
.primary { cyan渐变背景，深色文字 } — 主要操作
.ghost { 半透明边框 } — 次要操作
```

---

## 2. 8 个页面详细规格

### 01 — 事件录入 (seed)

**顶部：** 第 01 步 / 事件录入 / 副标题
**3 个 Mini：** 系统状态·当前任务·今日批次

**左侧面板：事件材料**
- textarea（舆情事件描述，预设 placeholder）
- 任务名称 input
- 材料来源 select（手动录入 / 本地材料文件 / 历史事件复用）
- 快捷输入 chips（校园食品安全 / 车企降价争议 / 文旅接待争议 / 平台投诉扩散）
- 按钮组：保存事件材料（.primary）+ 使用示例事件（.ghost）

**右侧面板：录入检查**
- 3 条 StepLine：事件背景已填写（通过） / 核心主体已识别（通过） / 时间线可补充（建议）

**底部面板：本阶段要完成什么**
- 3 张 Card：说清楚事件 / 明确关键主体 / 保留材料入口

**States：**
- empty：textarea 空，录入检查全部灰色，保存按钮 disabled
- populated：textarea 有内容，录入检查动态更新
- saved：保存成功，弹 toast（3 秒自动消失）
- error：保存失败，错误信息在面板内展示

---

### 02 — 推演配置 (config)

**顶部：** 第 02 步 / 推演配置 / 副标题

**3 面板并排：**
- **推演规模** — 平行推演轮数 input / 每轮模拟步数 input / 输出批次名称 input
- **推演重点** — chips 选择（风险扩散 / 群体分化 / 官方回应 / 平台外溢）+ 添加重点按钮
- **输出内容** — StepLine（推演结果数据 开启 / 运行日志 开启 / 报告草稿 后续）

**底部面板：配置预览**
- 4 个 Mini 指标：平行轮数 / 模拟步数 / 推演重点 / 预计产物

**States：**
- default：显示默认值（3 轮 / 40 步）
- modified：用户修改后，预览面板自动更新
- validated：配置检查通过后，底部可点击"下一步"

---

### 03 — 模型调度 (models)

**顶部：** 第 03 步 / 模型调度 / 副标题

**面板一：模型选择**
- 4 列 grid 展示模型卡片，每张 card 含：
  - 模型名称（strong）
  - 描述（p）
  - 两个 chip：已选择/未选择 + 可用/不可用
- 点击卡片切换选择状态

**面板二（左右并排）：**
- **可用性检测** — table 列出每个模型的：名称 / 状态（chip） / 响应时间 / 建议；操作按钮：重新检测（.primary）+ 只选择可用模型（.ghost）
- **调度建议** — StepLine：主模型已选择 / 对照模型已选择 / 异常模型已排除

**States：**
- loading：检测中，显示 spinner
- healthy：全部模型通过，调度建议全绿
- partial：部分模型失败，调度建议显示注意
- empty：无模型可选，显示空状态说明

---

### 04 — 运行监控 (run)

**顶部：** 第 04 步 / 运行监控 / 副标题

**4 个 Mini 指标：** 推演轮数 / 已完成 / 运行中 / 失败

**面板一：运行监控**
- 3 列 grid，每列一个 world status card：
  - 顶部：第 N 轮推演 + 状态 badge（已完成 / 运行中）
  - 模型名（h3）
  - 3 行 ev：结果数据 / 主要风险（或当前阶段） / 耗时（或已运行）

**面板二：运行日志**
- LogBox 组件，latest-first，每行带时间戳

**States：**
- pending：推演已排队，未开始
- running：部分 world 在跑，Mini 实时更新
- completed：全部完成，审查按钮可点
- partial-failure：部分 world 失败，用红色标记，显示错误摘要
- cancelled：用户取消后，标记为 cancelled

---

### 05 — 结果审查 (review)

**顶部：** 第 05 步 / 结果审查 / 副标题

**左右并排：**
- **主要风险对比** — table：推演轮次 / 主要风险 / 风险等级（chip） / 结果状态（chip）
- **审查结论** — StepLine：风险类型基本一致（稳定） / 第三轮仍在运行（等待） / 可进入报告准备（可选）

**底部面板：结果证据**
- 3 张 Card，每张一个风险类型的描述和证据

**States：**
- partial：部分 world 还在跑，结论显示"等待"
- complete：全部 world 完成，结论全绿，报告按钮可用
- empty：无数据，显示空状态

---

### 06 — 报告生成 (report)

**顶部：** 第 06 步 / 报告生成 / 副标题

**左右并排：**
- **报告生成** — 报告类型 select / 面向对象 select / 使用结果 select + 生成报告草稿（primary）+ 预览报告结构（ghost）
- **报告结构** — StepLine 五式结构：舆情概要 / 演化分析 / 风险研判 / 对策建议 / 附录

**底部面板：报告状态**
- 待生成时显示 empty state 说明文字
- 已生成时显示报告文件列表

**States：**
- empty：未选择任何结果，按钮 disabled
- ready：已选择结果，按钮可用
- generating：生成中，spinner
- generated：生成完成，显示文件列表

---

### 07 — 历史任务 (history)

**顶部：** 第 07 步 / 历史任务 / 副标题

**面板一：历史任务**
- table：任务名称 / 创建时间 / 状态（chip） / 主要风险 / 操作（ghost button）
- 分页控制

**面板二：可复用内容**
- 3 张 Card：复用事件材料 / 复用推演配置 / 打开报告草稿

**States：**
- loading：加载中
- empty：无历史记录，显示空状态提示
- populated：有历史记录，table 填充

---

### 08 — 系统设置 (settings)

**顶部：** 第 08 步 / 系统设置 / 副标题

**3 面板并排：**
- **模型管理** — StepLine 每个模型的可用状态
- **输出位置** — 默认保存目录 input / 历史任务保留 select
- **显示设置** — StepLine：业务语言优先（开启） / 技术详情（折叠）

**底部面板：系统检查**
- 4 个 Mini 指标：模型接口（正常） / 任务目录（可写） / 报告入口（待接入） / 日志服务（正常）

---

## 3. 路由与状态管理

### 3.1 路由

```typescript
const routes = [
  { path: '/', redirect: '/seed' },
  { path: '/seed', component: SeedPage },
  { path: '/config', component: ConfigPage },
  { path: '/models', component: ModelsPage },
  { path: '/run', component: RunPage },
  { path: '/review', component: ReviewPage },
  { path: '/report', component: ReportPage },
  { path: '/history', component: HistoryPage },
  { path: '/settings', component: SettingsPage },
];
```

### 3.2 跨页状态

使用 Pinia store 管理跨页面状态：

```typescript
// stores/run.ts
{
  seedText: string;
  config: { parallelWorlds, ticks, batchName, focuses };
  models: string[];
  activeBatch: { batchId, status, worlds };
  history: BatchSummary[];
  settings: Settings;
}
```

### 3.3 导航状态持久化

- 刷新后回到上次步骤，不重置到第 1 步
- localStorage 存储当前步骤索引

---

## 4. API 类型映射

每个页面对应的后端 API：

| 页面 | API | 请求 | 响应 |
|------|-----|------|------|
| 01-seed | `POST /api/seed` | `{seed_text, task_name, source}` | `{id, checks[]}` |
| 02-config | `GET/POST /api/config` | `{parallel_worlds, ticks, ...}` | `{config}` |
| 03-models | `GET /api/models` | — | `[{id, name, status, health}]` |
| 03-models | `POST /api/models/health` | `{model_ids[]}` | `[{id, latency, error}]` |
| 04-run | `POST /api/run` | `{seed_text, models, config}` | `{batch_id}` |
| 04-run | `GET /api/run/<id>/status` | — | `{batch_id, worlds[], all_completed}` |
| 05-review | `GET /api/review/<batch_id>` | — | `{worlds[], risk_comparison[]}` |
| 06-report | `POST /api/report` | `{batch_id, type, audience}` | `{report_id, download_url}` |
| 07-history | `GET /api/history` | `?page=&page_size=` | `[{batch_id, name, time, status}]` |
| 08-settings | `GET/PUT /api/settings` | `{key: value}` | `{settings}` |
| 04-cancel | `POST /api/cancel/<batch_id>` | — | `{status}` |
| 04-retry | `POST /api/run/<batch_id>/<world_id>/retry` | `{model?}` | `{status}` |
| abort | `POST /api/run/<batch_id>/abort` | — | `{status}` |
