"""
Adarian: 多智能体异步舆情预判系统
---

各模块说明：
- schemas.py: Pydantic 数据模型定义
- llm_client.py: LLM 统一调用封装
- phase1_entity_extraction.py: 实体提取与分类模块 (v1.1.4 新增，Analyzer/Generator/Validator协作)
- phase2_topology_builder.py: 微型社交拓扑构建
- phase3_tick_simulation.py: 异步时间步推演
- phase4_report_agent.py: 宏观洞察生成器
"""

__version__ = "1.1.10"

# 导入主要模块方便使用
from .schemas import (
    # 枚举
    EntityCategory,
    ConfirmationBiasLevel,
    NodeRole,
    EdgeType,
    RiskLevel,
    # 实体模型
    Entity,
    OpinionSpreader,
    Relation,
    # 输出模型
    EntityExtractionOutput,
    # Phase 2
    GraphNode,
    GraphEdge,
    Phase2Output,
    # Phase 3
    TickLog,
    GlobalMetrics,
    AgentEntry,
    # Phase 4
    Phase4Output,
    InflectionPoint,
    EmotionTrajectory,
)
from .llm_client import LLMClient, init_llm_client, get_llm_client
