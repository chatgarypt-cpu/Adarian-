"""
Adarian: 多智能体异步舆情预判系统
---

各模块说明：
- schemas/: Pydantic schema contract library
- llm_client.py: LLM 统一调用封装
- phase1/: 实体提取与分类 package (Analyzer/Generator/Validator 协作)
- phase2/: 微型社交拓扑构建 package
- phase3/: 异步时间步推演 package
- phase4/: 宏观洞察生成 package
"""

__version__ = "1.2.6"

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
