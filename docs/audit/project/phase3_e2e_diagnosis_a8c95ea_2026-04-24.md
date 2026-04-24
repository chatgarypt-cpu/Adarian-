# a8c95ea 版本 Phase3 最小 E2E 诊断报告

日期：2026-04-24  
基线提交：`a8c95ea`  
工作区：`d:\项目开发\研一\adarian\adarian mvp`

## 结论

当前版本不是“Phase3 业务逻辑跑起来后接口报错”，而是更早一层的问题：

1. Phase3 入口模块 `src/phase3_tick_simulation.py` 在导入阶段就失败，主因是它依赖的 3 个子模块根本不存在于当前提交中。
2. 即使临时补齐这 3 个模块的占位实现，Phase3 还会立即撞上第二个接口契约错误：`select_speakers()` 返回 `dict`，但调用方把它当成对象属性访问。
3. 即使继续修掉第二个错误，Phase2 到 Phase3 的人设字段透传仍然是断的，后续 `build_simulation_card()` / 轻量 prompt 质量会受影响，且实现若不做空值兜底，仍有继续报错的风险。

## 本次最小 E2E 测试

### 测试目标

验证在 `a8c95ea` 基线下，利用现成的 Phase1/Phase2 结构化输出，最小化地进入 `run_phase3()`，确认真实失败位置。

### 测试方式

不重新跑 LLM，只复用已有输出：

- `outputs/entities_and_relations.json`
- `outputs/social_graph.json`
- `seeds/example_event.txt`

然后调用：

```python
from main import run_phase3
run_phase3(extraction_output, phase2_output, seed_text)
```

### 测试结果

Phase1 输出加载成功：`5` 个事件实体，`7` 个意见传播者。  
Phase2 输出加载成功：`12` 个节点，`31` 条边。  
调用 `run_phase3()` 后立即失败。

真实 traceback：

```text
Traceback (most recent call last):
  File "<stdin>", line 19, in <module>
  File "D:\项目开发\研一\adarian\adarian mvp\main.py", line 137, in run_phase3
    from src.phase3_tick_simulation import (
        SimulationEngine, save_tick_logs, print_simulation_summary
    )
  File "D:\项目开发\研一\adarian\adarian mvp\src\phase3_tick_simulation.py", line 36, in <module>
    from src.phase3.context_builder import build_lightweight_context
ModuleNotFoundError: No module named 'src.phase3.context_builder'
```

## 主故障定位

### 故障 1：Phase3 顶层导入依赖缺失

证据：

- [main.py](/d:/项目开发/研一/adarian/adarian%20mvp/main.py:126) 的 `run_phase3()` 会在函数体内导入 `src.phase3_tick_simulation`
- [main.py](/d:/项目开发/研一/adarian/adarian%20mvp/main.py:137) 开始触发该导入
- [phase3_tick_simulation.py](/d:/项目开发/研一/adarian/adarian%20mvp/src/phase3_tick_simulation.py:36) 导入 `src.phase3.context_builder`
- [phase3_tick_simulation.py](/d:/项目开发/研一/adarian/adarian%20mvp/src/phase3_tick_simulation.py:37) 导入 `src.phase3.simulation_card`
- [phase3_tick_simulation.py](/d:/项目开发/研一/adarian/adarian%20mvp/src/phase3_tick_simulation.py:39) 导入 `src.phase3.state_updater`

而当前提交 `a8c95ea` 的 Git 跟踪结果只有：

```text
src/phase3/speaker_selector.py
src/phase3_tick_simulation.py
```

`src/phase3/` 目录实际也只有一个文件：`speaker_selector.py`。

这说明：

- 不是本地环境漏同步
- 不是 `PYTHONPATH` 配置问题
- 不是运行时数据问题
- 而是 **提交本身包含了对未落地子模块的硬依赖**

### 根因判断

这是一次“解耦重构写到一半”的典型状态：

- `phase3_tick_simulation.py` 已经按子模块架构写了导入和调用点
- 但 `context_builder.py`、`simulation_card.py`、`state_updater.py` 并未进入该提交
- 结果导致 Phase3 不是逻辑失败，而是模块边界直接不可导入

## 次级故障定位

为了确认缺模块是否是唯一问题，我做了一个“去遮罩”验证：

- 临时向 `sys.modules` 注入最小 stub
- 只为绕过 3 个缺失模块的导入
- 然后直接执行 `SimulationEngine(...).run_tick(1)`

结果立刻得到第二个真实报错：

```text
Traceback (most recent call last):
  File "<stdin>", line 39, in <module>
  File "D:\项目开发\研一\adarian\adarian mvp\src\phase3_tick_simulation.py", line 735, in run_tick
    spreader_count=selection.spreader_count,
                   ^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'dict' object has no attribute 'spreader_count'
```

### 故障 2：`select_speakers()` 返回形状与调用方不一致

证据：

- [phase3_tick_simulation.py](/d:/项目开发/研一/adarian/adarian%20mvp/src/phase3_tick_simulation.py:726) 调用 `select_speakers(...)`
- [phase3_tick_simulation.py](/d:/项目开发/研一/adarian/adarian%20mvp/src/phase3_tick_simulation.py:735) 开始按对象属性读取 `selection.spreader_count`
- [phase3_tick_simulation.py](/d:/项目开发/研一/adarian/adarian%20mvp/src/phase3_tick_simulation.py:744) 继续读取 `selection.selected_speakers`

但实际实现是：

- [speaker_selector.py](/d:/项目开发/研一/adarian/adarian%20mvp/src/phase3/speaker_selector.py:24) `select_speakers(...) -> dict`
- [speaker_selector.py](/d:/项目开发/研一/adarian/adarian%20mvp/src/phase3/speaker_selector.py:45) 直接 `return { ... }`

这不是类型提示小问题，而是确定会在运行时触发的接口契约错误。

### 更深一层的契约漂移

Schema 里其实已经定义了目标返回结构：

- [schemas.py](/d:/项目开发/研一/adarian/adarian%20mvp/src/schemas.py:556) `class SpeakerSelectionResult`
- [schemas.py](/d:/项目开发/研一/adarian/adarian%20mvp/src/schemas.py:570) `class SilentAgentUpdate`
- [schemas.py](/d:/项目开发/研一/adarian/adarian%20mvp/src/schemas.py:543) `class SimulationCard`

但当前实现没有遵守这个设计态：

- `speaker_selector.py` 没有返回 `SpeakerSelectionResult`
- 也没有提供 `silent_agents`、`ratio`、`validation_basis` 等设计字段

这说明当前代码不是“模块缺了而已”，而是 **Phase3 子模块化重构的接口设计和落地实现已经出现漂移**。

## 数据契约问题

### 故障 3：Phase2 没把人设字段透传给 GraphNode

上游 Phase1 输出里，意见传播者的人设字段是完整存在的：

- `outputs/entities_and_relations.json` 中可见 `persona_name`
- 同文件中也有 `occupation`、`personality`、`motivation`、`typical_phrases`

但 Phase2 构图时没有透传这些字段：

- [phase2_topology_builder.py](/d:/项目开发/研一/adarian/adarian%20mvp/src/phase2_topology_builder.py:122) 构造 opinion spreader 的 `GraphNode`
- [phase2_topology_builder.py](/d:/项目开发/研一/adarian/adarian%20mvp/src/phase2_topology_builder.py:131) 截止到这里只传了基础字段，没有传 persona 相关字段

因此保存后的 `outputs/social_graph.json` 中，这些字段全部是 `null`。

### 影响

这会直接影响后续 3 个接口中的至少 2 个：

- `build_simulation_card(agent, current_stance)` 很可能需要从 `GraphNode` 提取压缩人设
- `build_lightweight_context(...)` 的 prompt 质量依赖这些人设摘要

如果你只补模块文件，但不修 Phase2 透传，后续会出现两类结果：

1. 若 helper 做了空值兜底，Phase3 可能能跑，但 persona 驱动能力显著退化。
2. 若 helper 假定这些字段非空，Phase3 会继续在构卡或拼 prompt 时出错。

## 当前源码状态诊断

### 真实状态

- `src/phase3_tick_simulation.py` 已经迁移到“主入口 + 子模块 helper”结构
- `src/phase3/speaker_selector.py` 已存在
- `src/phase3/context_builder.py` 不存在
- `src/phase3/simulation_card.py` 不存在
- `src/phase3/state_updater.py` 不存在
- `src/phase3/__init__.py` 也不存在

说明：

`__init__.py` 缺失本身不是这次报错的直接原因。Python 现代命名空间包允许没有它。真正致命的是被导入的子模块文件本体不存在。

### 架构层判断

当前 `a8c95ea` 处于“Phase1/2 基本可用，但 Phase3 重构中断”的半完成状态。

所以这不是一个单点 bug，而是一个 **未完成重构被提前接入主链路** 的问题。

## 修改意见

### 优先级 P0：先让 Phase3 能导入

有两条路径，二选一，不能混用一半。

#### 方案 A：补齐新架构缺失子模块

需要新增：

- `src/phase3/context_builder.py`
- `src/phase3/simulation_card.py`
- `src/phase3/state_updater.py`

并且满足当前主文件调用契约：

- `build_simulation_card(agent, current_stance) -> SimulationCard`
- `build_lightweight_context(card, event_summary, event_entity_name, event_entity_post, followed, history) -> tuple[str, str]`
- `update_silent_agent(agent_id, previous_stance, susceptibility, followed_comments) -> SilentAgentUpdate`

适用场景：

- 你要保留新的 Phase3 解耦方向
- 后续还准备继续演进子模块

#### 方案 B：回退到旧的单文件 Phase3

做法：

- 删除 `phase3_tick_simulation.py` 中对 3 个 helper 子模块的顶层导入
- 把相关逻辑内联回 `phase3_tick_simulation.py`

适用场景：

- 你当前目标是“先把 a8c95ea 跑通”
- 不想在这个基线上继续承接未完成重构

我的判断：

如果你当前最关心“尽快恢复可运行基线”，方案 B 更稳。  
如果你当前最关心“沿着新架构继续修”，方案 A 更对路。

### 优先级 P1：修复 `select_speakers()` 契约

无论选方案 A 还是 B，这个都要修。

建议统一到 Schema 设计：

- `select_speakers(...) -> SpeakerSelectionResult`

至少要保证调用方当前读取的字段全部存在：

- `spreader_count`
- `computed_num_speakers`
- `expected_selected_count`
- `actual_selected_count`
- `selected_speakers`
- `is_full_selection`
- `full_selection_reason`

最小修法：

- 让 `speaker_selector.py` 返回 `SpeakerSelectionResult(...)`

不建议的修法：

- 把 `phase3_tick_simulation.py` 全部改成字典下标访问

原因：

- `schemas.py` 已经提供了明确的数据契约
- 继续用裸 `dict` 会把 Phase3 子模块边界继续做脏

### 优先级 P1：修复 Phase2 -> Phase3 人设透传

建议在 [phase2_topology_builder.py](/d:/项目开发/研一/adarian/adarian%20mvp/src/phase2_topology_builder.py:122) 构造 `GraphNode` 时，把这些字段一并传下去：

- `persona_name`
- `age_range`
- `occupation`
- `personality`
- `motivation`
- `typical_phrases`

否则：

- `SimulationCard` 无法稳定构建高质量 persona 摘要
- `context_builder` 只能靠空值兜底
- Phase3 生成质量会显著低于设计预期

### 优先级 P2：补最小接口测试

当前这类错误之所以能进入主链路，本质上是缺少模块边界级 smoke test。

至少建议加 3 类测试：

1. `import src.phase3_tick_simulation` 必须通过
2. `select_speakers()` 返回值必须满足 `SpeakerSelectionResult`
3. 使用固定 JSON 样本加载 `EntityExtractionOutput + Phase2Output` 后，`SimulationEngine(...).run_tick(1)` 至少能走到 LLM 调用前

## 建议执行顺序

1. 先决定是“补新架构”还是“退回旧架构”
2. 修 Phase3 缺失模块或回退主文件
3. 立刻修 `select_speakers()` 返回契约
4. 同步修 Phase2 人设字段透传
5. 最后补 smoke test，防止同类半重构状态再次进入主链路

## 最终判断

`a8c95ea` 可以视为“Phase1/Phase2 最接近可用基线”，但 **不能视为完整可运行的端到端版本**。

从工程角度看，当前版本的核心问题不是 LLM 输出不稳定，也不是单个函数写错，而是：

- Phase3 重构未完成就接入主链路
- 子模块接口契约未统一
- Phase2 到 Phase3 的数据契约没有同步完成

这三个问题叠在一起，导致当前版本在 Phase3 入口必然失败。
