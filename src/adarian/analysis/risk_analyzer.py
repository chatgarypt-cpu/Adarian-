"""
Phase 3: Risk Analyzer
---
Independently rebuilds risk analysis logic from Phase 4 report_agent.py,
providing a decoupled risk assessment layer within Phase 3.

v1.4.2 — classify_risk_types (keyword legacy) removed.
  sensitive_prior_hit → sensitive_context_hit:
  deterministic audience_mode / polarization check, no longer relies on
  old 13-type keyword classification. Final risk_type_classification
  continues via RiskClassifier (LLM-based 28-type catalog).
"""

from typing import Any, Dict, List, Optional, Tuple

from adarian.schemas.phase1 import EntityExtractionOutput
from adarian.schemas.phase3 import TickLog
from adarian.schemas.phase4 import RiskLevel, AudienceMode, RISK_LEVEL_LABELS


# ---------------------------------------------------------------------------
# Module-level constants (independently defined)
# ---------------------------------------------------------------------------

LAW_ENFORCEMENT_KEYWORDS = ("公安", "交警", "派出所", "执法", "警方")
REGULATOR_KEYWORDS = ("市监局", "市场监督管理局", "监管部门", "食药监")
PUBLIC_MANAGEMENT_KEYWORDS = ("教育局", "卫健委", "住建局", "属地政府", "街道办")


class RiskAnalyzer:
    """Decoupled risk analyzer that replicates Phase 4 assess_risk logic
    without importing anything from the archived inline report agent."""

    # ------------------------------------------------------------------
    # Audience mode detection
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_audience_text(extraction_output: EntityExtractionOutput) -> str:
        """Build concatenated text from extraction_output fields for keyword matching."""
        parts: List[str] = [
            extraction_output.event_summary,
            extraction_output.event_type,
        ]
        for entity in extraction_output.event_entities:
            parts.extend([
                entity.name,
                entity.role,
                entity.original_statement or "",
                entity.can_speak_reason or "",
            ])
        for spreader in extraction_output.opinion_spreaders:
            parts.extend([
                spreader.group_name,
                spreader.related_event_entity,
                spreader.description,
                spreader.communication_style,
            ])
        for relation in extraction_output.relations:
            parts.extend([relation.source, relation.target, relation.type])
        return "\n".join(part for part in parts if part)

    def determine_audience_mode(
        self, extraction_output: Optional[EntityExtractionOutput],
    ) -> str:
        """Determine audience mode using deterministic keyword priority rules.

        Returns one of the AudienceMode enum *string values*:
        ``law_enforcement_facing``, ``regulator_facing``,
        ``public_management_facing``, or ``generic_government``.
        """
        if extraction_output is None:
            return AudienceMode.GENERIC_GOVERNMENT.value

        text = self._collect_audience_text(extraction_output)

        if any(kw in text for kw in LAW_ENFORCEMENT_KEYWORDS):
            return AudienceMode.LAW_ENFORCEMENT_FACING.value
        if any(kw in text for kw in REGULATOR_KEYWORDS):
            return AudienceMode.REGULATOR_FACING.value
        if any(kw in text for kw in PUBLIC_MANAGEMENT_KEYWORDS):
            return AudienceMode.PUBLIC_MANAGEMENT_FACING.value
        return AudienceMode.GENERIC_GOVERNMENT.value

    # ------------------------------------------------------------------
    # Sensitive context detection (replaces old classify_risk_types path)
    # ------------------------------------------------------------------

    def _compute_sensitive_context_hit(
        self,
        extraction_output: Optional[EntityExtractionOutput],
        tick_logs: Optional[List[TickLog]],
    ) -> bool:
        """Determine if the event context is sensitive from a governance perspective.

        Returns True if either:
        - The audience mode indicates a specific governance domain (law enforcement,
          regulator, or public management), meaning the event involves entities
          like police, market regulators, or local government.
        - The final polarization index >= 0.50, indicating high public polarization.

        This replaces the old ``sensitive_prior_hit`` that relied on legacy
        keyword-based risk type classification (``classify_risk_types()``).
        The new helper is purely deterministic and does not depend on the old
        13-type taxonomy.
        """
        if extraction_output is None:
            return False

        audience_mode = self.determine_audience_mode(extraction_output)
        if audience_mode != AudienceMode.GENERIC_GOVERNMENT.value:
            return True

        if tick_logs and tick_logs[-1].global_metrics.polarization_index >= 0.50:
            return True

        return False

    # ------------------------------------------------------------------
    # Stance matrix helper (mirrors _build_code_owned_agent_stance_matrix)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_stance_matrix(tick_logs: List[TickLog]) -> List[Dict[str, Any]]:
        """Build per-agent stance matrix from tick_logs."""
        if not tick_logs:
            return []

        start_log = tick_logs[1] if len(tick_logs) >= 2 else tick_logs[0]
        end_log = tick_logs[-1]
        start_entries = {entry.agent_id: entry for entry in start_log.entries}
        end_entries = {entry.agent_id: entry for entry in end_log.entries}

        rows: List[Dict[str, Any]] = []
        for agent_id in sorted(set(start_entries) & set(end_entries)):
            start_entry = start_entries[agent_id]
            end_entry = end_entries[agent_id]
            initial = start_entry.current_stance
            final = end_entry.current_stance
            rows.append({
                "agent_id": agent_id,
                "group_name": end_entry.group_name,
                "start_tick": start_log.tick,
                "end_tick": end_log.tick,
                "initial_stance": initial,
                "final_stance": final,
                "delta": final - initial,
            })
        return rows

    # ------------------------------------------------------------------
    # Signal computation (used by both compute_signals and assess_risk)
    # ------------------------------------------------------------------

    def _compute_signals_internal(
        self,
        x_t_sequence: List[float],
        tick_logs: List[TickLog],
        extraction_output: Optional[EntityExtractionOutput],
    ) -> Dict[str, Any]:
        """Compute all risk signals from raw inputs."""
        start_x = x_t_sequence[0]
        final_x = x_t_sequence[-1]
        negative_pressure = max(0.0, 5.0 - final_x)
        negative_trend = max(0.0, start_x - final_x) if len(x_t_sequence) > 1 else 0.0
        final_pol = tick_logs[-1].global_metrics.polarization_index if tick_logs else 0.0

        # max_negative_shift from stance matrix
        rows = self._build_stance_matrix(tick_logs)
        if rows:
            max_negative_shift = max(
                max(0.0, row["initial_stance"] - row["final_stance"]) for row in rows
            )
        else:
            max_negative_shift = None

        # Event-level priors
        event_scale = extraction_output.event_scale if extraction_output is not None else 0.0
        event_controversy = extraction_output.event_controversy if extraction_output is not None else 0.0

        high_sensitive_prior = event_scale >= 0.7 and event_controversy >= 0.7

        # Sensitive context hit: deterministic audience / polarization check.
        # Replaces old ``sensitive_prior_hit`` that used legacy keyword classification.
        sensitive_context_hit = self._compute_sensitive_context_hit(
            extraction_output, tick_logs
        )

        return {
            "start_x": start_x,
            "final_x": final_x,
            "negative_pressure": negative_pressure,
            "negative_trend": negative_trend,
            "final_pol": final_pol,
            "max_negative_shift": max_negative_shift,
            "event_scale": event_scale,
            "event_controversy": event_controversy,
            "high_sensitive_prior": high_sensitive_prior,
            "sensitive_context_hit": sensitive_context_hit,
        }

    # ------------------------------------------------------------------
    # Public signal API
    # ------------------------------------------------------------------

    def compute_signals(
        self,
        x_t_sequence: List[float],
        tick_logs: List[TickLog],
        *,
        extraction_output: Optional[EntityExtractionOutput] = None,
    ) -> Dict[str, Any]:
        """Compute risk signals from simulation data.

        Returns a dict with: negative_trend, final_polarization,
        max_negative_shift, event_prior_floor, sensitive_context_hit,
        and all other intermediate signals used by assess_risk.
        """
        if not x_t_sequence:
            return {
                "negative_trend": 0.0,
                "final_polarization": 0.0,
                "max_negative_shift": None,
                "event_prior_floor": "normal",
                "sensitive_context_hit": False,
            }

        signals = self._compute_signals_internal(x_t_sequence, tick_logs, extraction_output)

        # Derived: event_prior_floor
        if signals["event_scale"] >= 0.7 and signals["event_controversy"] >= 0.7:
            event_prior_floor = "high"
        else:
            event_prior_floor = "normal"

        return {
            "negative_trend": signals["negative_trend"],
            "final_polarization": signals["final_pol"],
            "max_negative_shift": signals["max_negative_shift"],
            "event_prior_floor": event_prior_floor,
            "sensitive_context_hit": signals["sensitive_context_hit"],
            # Extra signals for full visibility
            "start_x": signals["start_x"],
            "final_x": signals["final_x"],
            "negative_pressure": signals["negative_pressure"],
            "event_scale": signals["event_scale"],
            "event_controversy": signals["event_controversy"],
            "high_sensitive_prior": signals["high_sensitive_prior"],
        }

    # ------------------------------------------------------------------
    # Risk assessment (exact behavioral parity with report_agent.py L418-509)
    # ------------------------------------------------------------------

    def assess_risk(
        self,
        x_t_sequence: List[float],
        tick_logs: List[TickLog],
        *,
        extraction_output: Optional[EntityExtractionOutput] = None,
    ) -> Tuple[RiskLevel, str]:
        """Evaluate risk level from simulation data.

        Returns (RiskLevel, assessment_string) with identical semantics
        to report_agent.assess_risk for the same inputs.
        """
        # Early return: empty data
        if not x_t_sequence:
            return RiskLevel.LOW, "数据不足，无法评估"

        # ---- Core metrics ----
        signals = self._compute_signals_internal(x_t_sequence, tick_logs, extraction_output)
        final_x = signals["final_x"]
        negative_trend = signals["negative_trend"]
        final_pol = signals["final_pol"]
        max_negative_shift = signals["max_negative_shift"]
        event_scale = signals["event_scale"]
        event_controversy = signals["event_controversy"]
        high_sensitive_prior = signals["high_sensitive_prior"]
        sensitive_context_hit = signals["sensitive_context_hit"]

        # ---- Shift thresholds ----
        material_negative_shift = max_negative_shift is not None and max_negative_shift >= 1.2
        strong_negative_shift = max_negative_shift is not None and max_negative_shift >= 2.0
        critical_negative_shift = max_negative_shift is not None and max_negative_shift >= 2.5

        # ---- Signal collections ----
        medium_signals = [
            final_x <= 4.7,
            negative_trend >= 0.4,
            final_pol >= 0.30,
            material_negative_shift,
            high_sensitive_prior,
            sensitive_context_hit,
        ]
        high_signals = [
            final_pol >= 0.45 and (negative_trend >= 0.4 or material_negative_shift),
            strong_negative_shift and sensitive_context_hit,
            final_x <= 4.0 and negative_trend >= 0.5,
            high_sensitive_prior and final_pol >= 0.40,
        ]
        critical_ready = (
            final_x <= 3.0
            and final_pol >= 0.45
            and critical_negative_shift
            and (
                event_scale >= 0.7
                or event_controversy >= 0.8
                or sensitive_context_hit
            )
        )

        # ---- Priority resolution ----
        if critical_ready:
            risk_level = RiskLevel.CRITICAL
        elif any(high_signals):
            risk_level = RiskLevel.HIGH
        elif any(medium_signals):
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # ---- Build assessment string ----
        signal_parts = [
            f"模拟立场均值={final_x:.1f}",
            f"负向趋势={negative_trend:.1f}",
            f"模拟极化指数={final_pol:.2f}",
        ]
        if max_negative_shift is not None:
            signal_parts.append(f"关键群体最大负向迁移={max_negative_shift:.1f}")
        else:
            signal_parts.append("关键群体负向迁移数据不足")
        if high_sensitive_prior:
            signal_parts.append("高敏事件先验达到中风险下限")
        if sensitive_context_hit:
            signal_parts.append("敏感治理语境命中")

        if risk_level == RiskLevel.CRITICAL:
            prefix = "重大风险，低模拟立场均值、高模拟极化、关键群体负向迁移和高敏先验同时出现"
        elif risk_level == RiskLevel.HIGH:
            prefix = "高风险，多个负向压力信号叠加，需重点关注"
        elif risk_level == RiskLevel.MEDIUM:
            prefix = "中等风险，已出现负向压力、分化或高敏先验信号"
        else:
            prefix = "低风险，未发现明显负向压力、分化压力、群体跃迁或高敏先验"

        return risk_level, f"{prefix}（{'、'.join(signal_parts)}）"
