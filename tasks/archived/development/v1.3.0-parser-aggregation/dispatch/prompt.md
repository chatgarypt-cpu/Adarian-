载入 karpathy-coding 行为准则。

use a workflow to: 实现 v1.3.0 Phase 3 Parser Aggregation Layer 和 Phase 4 Dual-Consumption Validation

## 背景

Adarian MVP 是一个多智能体舆情推演系统。当前 Phase 4（报告层）中承载了本应属于 Phase 3（模拟层）的确定性计算逻辑（risk 判定、inflection 检测、stance 分析）。本轮在 Phase 3 中新增子模块独立重建这些计算，再通过 Phase 4 双版本消费验证抽离是否成功。

## 执行步骤

### Step 1: 创建 3 个 Phase 3 子模块（并行）

按 §6.1-6.3 的接口签名，同时在 `src/phase3/` 下创建三个文件：

#### src/phase3/risk_analyzer.py

```python
from typing import Any, Dict, List, Optional, Tuple
from src.schemas.phase1 import EntityExtractionOutput
from src.schemas.common import TickLog
from src.schemas.phase4 import RiskLevel

class RiskAnalyzer:
    def assess_risk(
        self,
        x_t_sequence: List[float],
        tick_logs: List[TickLog],
        *,
        extraction_output: Optional[EntityExtractionOutput] = None,
    ) -> Tuple[RiskLevel, str]:
        """评估整体风险。参考 Phase 4 report_agent.py 中 assess_risk()（~L418-509）独立重建。"""
        ...

    def compute_signals(
        self,
        x_t_sequence: List[float],
        tick_logs: List[TickLog],
        *,
        extraction_output: Optional[EntityExtractionOutput] = None,
    ) -> Dict[str, Any]:
        """计算 risk signals（negative_trend, final_polarization, max_negative_shift, event_prior_floor, sensitive_prior_hit）。"""
        ...

    def determine_audience_mode(
        self,
        extraction_output: Optional[EntityExtractionOutput],
    ) -> str:
        """决定受众模式：generic_government | law_enforcement_facing | regulator_facing | public_management_facing。"""
        ...

    def classify_risk_types(
        self,
        audience_mode: str,
        risk_assessment: str,
        tick_logs: List[TickLog],
    ) -> List[str]:
        """根据 audience_mode 和 risk_assessment 分类风险类型。"""
        ...
```

必须独立重建以下辅助依赖（不得从 Phase 4 import）：
- audience mode keywords（LAW_ENFORCEMENT_KEYWORDS, REGULATOR_KEYWORDS, PUBLIC_MANAGEMENT_KEYWORDS）
- risk type selection keyword map（约 80 行常量和 keyword_map）
- sensitive prior risk type set（SENSITIVE_PRIOR_RISK_TYPES）
- max negative shift helper（从 stance matrix 计算最大负向偏移）
- event_scale / event_controversy prior_floor logic

#### src/phase3/inflection_detector.py

```python
from typing import List
from src.schemas.common import TickLog
from src.schemas.phase2 import Phase2Output

class InflectionDetector:
    def detect(
        self,
        tick_logs: List[TickLog],
        phase2_output: Phase2Output,
        *,
        pol_threshold: float = 0.1,
        max_points: int = 3,
    ) -> List[dict]:
        """检测拐点。phase2_output 用于 agent_id → group_name 映射。不得省略。"""
        ...
```

#### src/phase3/stance_analyzer.py

```python
from typing import List, Optional
from src.schemas.common import TickLog

class StanceAnalyzer:
    def build_agent_stance_matrix(
        self,
        tick_logs: List[TickLog],
    ) -> List[dict]:
        """构建立场矩阵。first_log = tick_logs[1]（跳过 Tick 0），如果 tick_logs 不足两轮则 graceful degrade。"""
        ...

    def max_negative_shift(
        self,
        tick_logs: List[TickLog],
    ) -> Optional[float]:
        """计算最大负向偏移量。返回 None 表示无负向偏移。"""
        ...
```

### Step 2: 创建 Parser 聚合层

#### src/phase3/parser.py

```python
class SimulationDatasetParser:
    def parse(
        self,
        extraction_output,
        phase2_output,
        tick_logs,
        x_t_sequence,
        *,
        source_artifact_refs=None,
    ) -> dict:
        ...

    def save_dataset(self, dataset, output_path):
        ...
```

Parser 是纯编排/聚合层：它调用 Phase 3 子模块，但自己不新增分析逻辑。不得包含零计算逻辑或 LLM 调用。

输出的 simulation_dataset 必须遵循以下最小契约结构：

```json
{
  "_schema_version": "v1",
  "_generated_by": "phase3_parser",
  "run_info": {
    "event_name": "string",
    "event_scale": "float|null",
    "event_controversy": "float|null",
    "event_type": "string|null",
    "total_ticks": "int",
    "audience_mode": "string"
  },
  "simulation_result": {
    "x_t_sequence": ["float"],
    "final_x": "float|null",
    "final_polarization_index": "float|null",
    "emotion_trajectory": [{"tick": "int", "mean_stance": "float|null", "std_stance": "float|null", "polarization_index": "float|null", "key_event": "string"}],
    "inflection_points": [{"tick": "int", "agent_id": "int|null", "group_name": "string", "pivotal_comment": "string", "impact_description": "string", "pol_delta": "float|null", "stance_delta": "float|null"}],
    "risk_verdict": {"level": "low|medium|high|critical", "label": "低风险|中风险|高风险|重大风险", "basis_text": "string", "signals": {"negative_trend": "float|null", "final_polarization": "float|null", "max_negative_shift": "float|null", "event_prior_floor": "string|null", "sensitive_prior_hit": "bool|null"}},
    "risk_type_classification": {"primary_types": ["string"], "type_labels": ["string"]},
    "agent_stance_matrix": [{"agent_id": "int", "group_name": "string", "initial_stance": "float|null", "final_stance": "float|null", "max_delta": "float|null", "attitude": "stable|declining|rising|volatile|unknown"}]
  },
  "source_artifact_refs": {"tick_logs": "string", "entities_and_relations": "string", "social_graph": "string"},
  "known_limitations": ["string"]
}
```

### Step 3: 更新 src/phase3/__init__.py

最小化修改，re-export 新增模块的关键类。

### Step 4: 创建 Phase 4 双版本消费（基于现有 report_agent.py）

在现有的 `src/phase4/report_agent.py` 中增加**消费路径隔离包装**：

**旧版 Phase 4 Consumer（baseline）：**
- 保持原有行为不变
- 从原始 tick_logs / x_t_sequence / extraction_output / phase2_output 中自行走旧路径
- 不读取 simulation_dataset
- 不调用 Phase 3 新增子模块
- 输出作为 baseline

**新版 Phase 4 Consumer（candidate）：**
- 只从 simulation_dataset 或 Phase 3 新结构化接口中读取
- 消费字段：risk_verdict、inflection_points、emotion_trajectory、agent_stance_matrix、risk_type_classification
- 不允许自行重新计算上述字段——仅作为接收容器/生成器
- 输出作为 candidate

**修改边界：**
- ✅ 允许：增加旧/新消费路径隔离包装、wrapper、bypass 测试入口
- ✅ 允许：增加 dispatch_prompt + task_config 支持的试验入口
- ❌ 禁止：修改 prompt、narrative、normalizer、title 语义
- ❌ 禁止：修改 risk / inflection / stance / metrics 计算逻辑
- ❌ 禁止：删除原计算函数

对外保持 facade / orchestrator 不变——main.py 和现有调用方不受影响。

### Step 5: 编写测试

每个新增子模块至少 3 个单元测试：

| 测试类型 | 说明 |
|---------|------|
| 正常输入路径 | 标准 tick_logs 输入，验证输出结构正确 |
| 空输入 / 缺字段 graceful degrade | 空列表/None 输入不崩溃 |
| 边界条件 / 阈值条件 | 极化边缘值、0 agent 场景 |

测试文件：
- `tests/test_phase3_risk_analyzer.py`
- `tests/test_phase3_inflection_detector.py`
- `tests/test_phase3_stance_analyzer.py`
- `tests/test_phase3_parser.py`
- `tests/test_phase4_dual_consumption_bypass.py`（包含 bypass 对比逻辑）

### Step 6: 运行 bypass 对比

在同一输入下运行新旧两个路径，比对以下字段：

| 比对字段 | 说明 |
|---------|------|
| risk_verdict.level vs old risk_level | 浮点容差 1e-6 |
| risk_verdict.label vs old risk_level_label | 文本精确匹配 |
| inflection_points 数量与核心字段 | 结构比对 |
| emotion_trajectory / metrics_snapshot | 逐字段比对 |
| x_t_sequence / final_x | 浮点容差 1e-6 |
| primary_risk_types / risk_type_labels | 列表内容比对 |

### Step 7: 验证

运行以下验证命令：

```bash
.venv/bin/python -m py_compile src/phase3/risk_analyzer.py src/phase3/inflection_detector.py src/phase3/stance_analyzer.py src/phase3/parser.py
.venv/bin/python -m pytest tests/test_phase3_risk_analyzer.py tests/test_phase3_inflection_detector.py tests/test_phase3_stance_analyzer.py tests/test_phase3_parser.py -v
.venv/bin/python -m pytest tests/test_phase4_dual_consumption_bypass.py -v
.venv/bin/python -m pytest tests/ --ignore=docs -v
.venv/bin/python main.py seeds/test8.txt
```

### Step 8: 写证据文件

把完成情况写入 `tasks/active/v1.3.0-parser-aggregation/outputs/closeout_evidence.md`：
- 新增了哪些文件、每文件的行数和职责
- 测试通过数量
- bypass 对比结果（一致/差异及解释）
- 任何 Phase 3 module coupling finding（子模块间隐式依赖）
- 未完成的 carry-over

## 禁止事项

1. 不得从 `src/phase4/report_agent.py` import 内部函数（辅助函数、关键词常量）
2. 不得修改 `src/phase1/`、`src/phase2/`、`src/phase3/tick_simulation.py`、`src/phase3/speaker_selector.py`、`src/phase3/context_builder.py`、`src/phase3/simulation_card.py`、`src/phase3/state_updater.py`
3. 不得修改 `src/phase4/report_prompts.py`、`src/phase4/report_narrative.py`、`src/phase4/report_normalizer.py`、`src/phase4/report_title.py`
4. 不得修改 `main.py`、`config.py`、`src/schemas/`、`src/llm_client.py`、`src/utils/`、`src/whitebox/`
5. 不得删除任何现有文件
6. 不得新增 LLM 调用
7. 不得把 review finding 自动升级为任务

## 完成条件

1. risk_analyzer / inflection_detector / stance_analyzer / parser 新模块存在且可通过 py_compile
2. inflection_detector 接口包含 phase2_output 参数
3. risk_analyzer 接口包含 extraction_output 参数，辅助函数独立重建
4. simulation_dataset 使用独立新 schema，不修改现有 schema
5. 旧版 Phase 4 不消费 simulation_dataset
6. 新版 Phase 4 只消费 simulation_dataset 中的结构化字段
7. old output 与 new output 关键字段完成 bypass 比对
8. 新增单元测试通过
9. 回归测试通过
10. forbidden files 未被修改
11. 未新增 LLM 调用

报告使用中文。
