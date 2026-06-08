"""分析层 — 独立于 Phase 3 仿真引擎的纯分析模块。

各分析器消费 Phase 3 产出的结构化数据（tick_logs / x_t_sequence）
和 Phase 1 产出的实体数据（extraction_output），输出业务分析结果。

与 Phase 3 的边界：
- Phase 3 负责仿真推演（SimulationEngine）
- analysis 负责结果分析（风险/拐点/立场）
- 两者通过 tick_logs + x_t_sequence + extraction_output 通信
"""
from .risk_analyzer import RiskAnalyzer
from .inflection_detector import InflectionDetector
from .stance_analyzer import StanceAnalyzer

__all__ = [
    "RiskAnalyzer",
    "InflectionDetector",
    "StanceAnalyzer",
]
