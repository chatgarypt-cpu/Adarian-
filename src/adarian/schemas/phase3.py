"""Phase 3 schema contracts."""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


MAX_AGENT_COMMENT_CHARS = 1000
MAX_AGENT_REASONING_CHARS = 600


class AgentEntry(BaseModel):
    """单个 Agent 的发言条目"""
    agent_id: int = Field(..., description="Agent 唯一ID")
    group_name: str = Field(..., description="所属群体名称")
    saw_posts_from: List[int] = Field(..., description="本轮读取的发言者 ID 列表")
    previous_stance: float = Field(..., ge=1.0, le=10.0, description="上一轮立场分")
    current_stance: float = Field(..., ge=1.0, le=10.0, description="本轮立场分")
    stance_delta: float = Field(..., description="立场变化量，绝对值表示变化程度")
    susceptibility: float = Field(..., ge=0.0, le=1.0, description="该 agent 的易感性（新增 v1.1.9）")
    change_reason: str = Field(..., description="立场变化原因：within_effective_delta | bounded_by_susceptibility（新增 v1.1.9）")
    comment: str = Field(..., max_length=MAX_AGENT_COMMENT_CHARS, description="发表的评论内容")
    reasoning: str = Field(..., max_length=MAX_AGENT_REASONING_CHARS, description="立场理由")
    speaker_status: Optional[Literal["active", "silent", "blocked", "failed"]] = Field(
        default=None, description="白盒观测：本轮发言状态"
    )
    speaker_reason: Optional[Literal[
        "selected_by_scheduler",
        "not_selected_by_scheduler",
        "can_speak_false",
        "event_entity_statement",
        "llm_generation_failed",
        "parser_failed",
        "runtime_error",
        "unknown",
    ]] = Field(default=None, description="白盒观测：发言状态原因")
    decision_source: Optional[Literal[
        "phase1_can_speak",
        "phase3_speaker_selector",
        "llm_client",
        "runtime_exception",
        "unknown",
    ]] = Field(default=None, description="白盒观测：决策来源")
    selector_score: Optional[float] = Field(default=None, description="白盒观测：speaker selector 分数")
    selector_rank: Optional[int] = Field(default=None, description="白盒观测：speaker selector 排名")
    candidate_count: Optional[int] = Field(default=None, description="白盒观测：本轮候选 speaker 数")
    selected_count: Optional[int] = Field(default=None, description="白盒观测：本轮选中 speaker 数")
    speaker_budget: Optional[int] = Field(default=None, description="白盒观测：本轮 speaker 预算")
    selection_policy: Optional[str] = Field(default=None, description="白盒观测：speaker selection 策略")
    can_speak_reason: Optional[str] = Field(default=None, description="白盒观测：不可发言原因")
    speech_availability: Optional[Literal[
        "direct_quote",
        "reported_speech",
        "official_statement",
        "no_source",
        "unknown",
    ]] = Field(default=None, description="白盒观测：发言来源可用性")
    source_basis: Optional[Literal[
        "seed_material",
        "external_search",
        "none",
        "unknown",
    ]] = Field(default=None, description="白盒观测：来源依据")


class GlobalMetrics(BaseModel):
    """全局指标。"""
    mean_stance: float = Field(..., ge=1.0, le=10.0, description="全局平均立场分，即 x(t)")
    std_stance: float = Field(..., ge=0.0, description="立场标准差，衡量群体分裂程度")
    polarization_index: float = Field(..., ge=0.0, le=1.0, description="极化指数 = std/mean")


class TickLog(BaseModel):
    """每轮交互日志"""
    tick: int = Field(..., ge=0, description="轮次编号（0=事件实体发言）")
    entries: List[AgentEntry] = Field(..., description="所有 Agent 的发言条目")
    global_metrics: GlobalMetrics = Field(..., description="本轮全局指标")


class SpeakerSelectionResult(BaseModel):
    """自适应 speaker 选择结果。"""
    selected_speakers: List[int] = Field(default_factory=list, description="本轮被选中发言的 agent ids")
    silent_agents: List[int] = Field(default_factory=list, description="本轮静默更新的 agent ids")
    selector_scores: Dict[int, float] = Field(default_factory=dict, description="每个候选 agent 的 selector 分数")
    selector_ranks: Dict[int, int] = Field(default_factory=dict, description="每个候选 agent 的 selector 排名，1 为最高")
    ratio: float = Field(..., ge=0.0, le=1.0, description="本轮目标发言比例")
    spreader_count: int = Field(default=0, ge=0, description="本轮传播者总数")
    computed_num_speakers: int = Field(default=0, ge=0, description="规则计算得到的目标发言数")
    expected_selected_count: int = Field(default=0, ge=0, description="本轮期望被选中的 speaker 数")
    actual_selected_count: int = Field(default=0, ge=0, description="本轮实际被选中的 speaker 数")
    is_full_selection: bool = Field(default=False, description="本轮是否全量选择")
    full_selection_reason: str = Field(default="not_full_selection", description="全量选择原因分类")
    validation_basis: str = Field(default="selected_speakers", description="当前校验所依据的 speaker 集合")


class SilentAgentUpdate(BaseModel):
    """静默 agent 的轻量更新结果。"""
    agent_id: int = Field(..., ge=0, description="Agent 唯一ID")
    previous_stance: float = Field(..., ge=1.0, le=10.0, description="更新前立场分")
    current_stance: float = Field(..., ge=1.0, le=10.0, description="更新后立场分")
    stance_delta: float = Field(..., description="立场变化量")
    saw_posts_from: List[int] = Field(default_factory=list, description="本轮被动看到的发言者 ID 列表")
    change_reason: str = Field(..., description="silent agent 变化原因")
    comment: str = Field(default="（未发言）", description="静默 agent 的占位评论")
    reasoning: str = Field(default="本轮未进入公开发言队列", description="静默 agent 的解释")
    activity_state: str = Field(default="silent", description="为未来 state machine 预留的活动状态入口")


class ClassificationOutput(BaseModel):
    """RiskClassifier 输出：Top-3 风险类型 ID。"""
    primary_types: List[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Top 3 risk types from the 28-type taxonomy, ordered by relevance",
    )


__all__ = [
    "AgentEntry",
    "GlobalMetrics",
    "MAX_AGENT_COMMENT_CHARS",
    "MAX_AGENT_REASONING_CHARS",
    "TickLog",
    "SpeakerSelectionResult",
    "SilentAgentUpdate",
    "ClassificationOutput",
]
