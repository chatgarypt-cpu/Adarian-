# Control Plane Retirement

## 0. Purpose

本文件定义当前 control plane MVP 的退役方案。

退役对象：
- `control/state.json`（已归档到 `docs/_archive/control_plane/control/state.json`）
- `control/inbox.md`（已归档到 `docs/_archive/control_plane/control/inbox.md`）
- `control/snapshot.md`（已归档到 `docs/_archive/control_plane/control/snapshot.md`）
- `scripts/generate_snapshot.py`（已归档到 `docs/_archive/control_plane/generate_snapshot.py`）

相关依赖：
- `scripts/probes/reduced_schema_chain_probe.py`
- `scripts/probes/p1a_prompt_probe.py`
- `scripts/probes/p1g_prompt_probe.py`

退役原因以已确认事实为准：
- control plane 未成为权威状态源
- control plane 增加了新的手工维护链路
- control plane 与现有主流程重叠
- control plane 当前触发频率低，用户已明确决策应彻底移除

当前执行状态：
- Phase 1：已完成，停止新增 control plane 功能
- Phase 2：已完成，probe 已不再读写 `control/`
- Phase 3：已完成，文件已归档至 `docs/_archive/control_plane/`
- Phase 4：已完成，主流程文档已声明 control plane 退役

---

## 1. Retirement Principles

### 1.1 No Silent Breakage

退役前必须先清理脚本依赖，不能直接删除 `control/` 导致 probe 或辅助脚本静默失效。

### 1.2 No New Control Features

从本文件生效起，不再向 `control/`、`generate_snapshot.py`、相关回写逻辑追加新功能。

### 1.3 Preserve Audit Trail

退役的是 workflow 组件，不是历史证据。历史文件可以归档，但不应无痕抹除。

---

## 2. Scope

### 2.1 Files to Retire

- `docs/_archive/control_plane/control/state.json`
- `docs/_archive/control_plane/control/inbox.md`
- `docs/_archive/control_plane/control/snapshot.md`
- `docs/_archive/control_plane/generate_snapshot.py`

### 2.2 Files to Refactor Before Retirement

- `scripts/probes/reduced_schema_chain_probe.py`
- `scripts/probes/p1a_prompt_probe.py`
- `scripts/probes/p1g_prompt_probe.py`

### 2.3 Files to Update

- `docs/skills/workflow_core.md`
- `docs/audit/workflow/workflow_audit_report.md`
- `docs/audit/workflow/next_workflow_design.md`
- 如存在 workflow index / README / 操作文档，也应同步移除 control plane 引用

---

## 3. Dependency Facts

已核实依赖如下（执行前）：

- `scripts/generate_snapshot.py`
  - 直接读取 `control/state.json`
  - 直接读取 `control/inbox.md`
  - 覆盖写入 `control/snapshot.md`

- `scripts/probes/reduced_schema_chain_probe.py`
  - 直接依赖 `control/state.json`
  - 直接依赖 `control/inbox.md`
  - 会把 probe 结果 append 回 `control/inbox.md`

- `scripts/probes/p1a_prompt_probe.py`
  - 直接依赖 `control/inbox.md`
  - 会把 probe 结果 append 回 `control/inbox.md`

- `scripts/probes/p1g_prompt_probe.py`
  - 直接依赖 `control/inbox.md`
  - 会把 probe 结果 append 回 `control/inbox.md`

因此退役不是“删除目录”这么简单，而是“先去耦，再归档”。

当前状态（执行后）：

- `scripts/probes/reduced_schema_chain_probe.py` 已移除对 `control/state.json` / `control/inbox.md` 的依赖
- `scripts/probes/p1a_prompt_probe.py` 已移除对 `control/inbox.md` 的依赖
- `scripts/probes/p1g_prompt_probe.py` 已移除对 `control/inbox.md` 的依赖
- `control/` 与 `generate_snapshot.py` 已从现行路径移出并归档

---

## 4. Retirement Plan

### Phase 1: Freeze

目标：
- 停止扩展 control plane

动作：
- 不再新增 `control/` 字段
- 不再新增新的 snapshot 逻辑
- 不再新增新的脚本回写 `control/`

完成标准：
- 新变更中不再出现对 `control/` 的新增依赖

### Phase 2: Remove Runtime Dependencies

目标：
- 让 probe 和辅助脚本不再依赖 `control/`

动作：
- `reduced_schema_chain_probe.py` 去掉对 `control/state.json` / `control/inbox.md` 的读写
- `p1a_prompt_probe.py` 去掉对 `control/inbox.md` 的回写
- `p1g_prompt_probe.py` 去掉对 `control/inbox.md` 的回写

推荐替代：
- probe 结果只写各自 `profiling/output/probes/...` 或 `profiling/output/runs/...`
- 不再回写 workflow 层状态文件

完成标准：
- grep 项 `control/`、`state.json`、`inbox.md` 在 probe 脚本中消失

当前结果：
- 已完成

### Phase 3: Archive or Remove Control Files

目标：
- 退役 control plane 主体

动作二选一：

方案 A：归档
- 将 `control/` 及 `generate_snapshot.py` 移至归档区
- 保留历史证据，但不再参与主流程

方案 B：删除
- 删除 `control/`
- 删除 `generate_snapshot.py`

推荐：
- 如果需要保留 workflow 演化证据，用方案 A
- 如果用户明确只要干净主线，用方案 B

当前执行：
- 已采用方案 A（归档）

### Phase 4: Update Workflow Docs

目标：
- 文档层声明 control plane 已退役

动作：
- 在 `workflow_core.md` 中移除 control plane 作为现行流程组件的暗示
- 在 workflow 设计文档中明确其为已退役实验层
- 在必要处记录“退役决定”和退役日期

完成标准：
- 主流程文档不再把 control plane 当成现行组件

当前结果：
- 已完成

---

## 5. Risks

### Risk-01: Probe Breakage

如果先删 `control/` 再改 probe，脚本会直接报错。

控制措施：
- 必须先完成依赖去耦

### Risk-02: Historical Context Loss

如果直接删除 control 文件，可能丢失一次 workflow 实验的运行截面。

控制措施：
- 若需保留证据，先归档再删除

### Risk-03: Authority Vacuum

如果退役 control plane，但未同步明确新的运行状态权威源，会出现新的空档。

控制措施：
- 退役动作必须和 authority 收敛同步进行

---

## 6. Exit Criteria

control plane 退役完成的标准：

- `control/` 不再被运行脚本读写
- `generate_snapshot.py` 不再参与主流程
- 主流程文档不再依赖 control plane
- 运行状态只保留一套权威来源

---

## 7. Decision

当前建议：
- 先 Freeze
- 再去掉 probe/runtime 依赖
- 最后归档或删除 `control/`

这比直接删目录更稳，因为它先消除运行时耦合，再处理文件层退役。
