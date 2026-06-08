"""Phase 3 Parser: RiskClassifier — LLM-based risk type classification.

Compresses Phase 3 simulation outputs into a stable query text, then asks the
LLM to pick the Top-3 risk types from the 26-type taxonomy defined in
`spec/risk_mapping.yaml` and mirrored in `src.schemas.phase4`.

Designed to be a single LLM call per dataset; the caller (SimulationDatasetParser)
is responsible for invoking this only once per parse.
"""

from typing import Any, Dict, List

from src.llm_client import get_llm_client
from src.schemas.phase1 import EntityExtractionOutput
from src.schemas.phase3 import ClassificationOutput, TickLog
from src.schemas.phase4 import DOMAIN_LABELS, RISK_TYPE_LABELS, TYPE_TO_DOMAIN_MAP


# Per-type "typical scenario" hints — used in the LLM catalog so the model can
# distinguish types within the same domain. Sourced from spec/risk_mapping.yaml
# description fields (and stable hand-written fallbacks for the v0.2 entries
# that ship without an explicit scenario in the YAML).
_TYPE_SCENARIOS: Dict[str, str] = {
    # 治理信任类
    "regulatory_trust_risk": "监管动作被质疑、被认为失职或被指控为利益相关方",
    "law_enforcement_credibility_risk": "执法/警察行为引发冲突或被质疑程序",
    "transparency_risk": "处置过程信息不公开、回应迟缓或被怀疑隐瞒",
    "accountability_escalation_risk": "舆论从质疑事实升级为追责、问责具体官员",
    "policy_interpretation_pressure_risk": "政策被误读、引发广泛担忧或激烈争论",
    # 公共安全与民生类
    "food_product_safety_risk": "食品/产品质量问题或品牌信任危机",
    "campus_minor_protection_risk": "校园暴力、未成年人侵害、家校冲突",
    "public_safety_concern_risk": "公共场所安全事件、突发治安、群体性事件",
    "livelihood_vulnerable_protection_risk": "弱势群体保障、困难群众、欠薪、扶贫",
    "public_health_event_risk": "传染病防控、医疗资源、疫苗、医疗事故",
    "environmental_ecological_risk": "污染、生态破坏、环评、气候争议",
    # 传播演化类
    "negative_narrative_aggregation_risk": "负面叙事快速聚合，话题被反复放大",
    "group_polarization_fragmentation_risk": "群体立场极度分化、对立尖锐",
    "secondary_spread_issue_overflow_risk": "议题从原事件外溢、引发次生讨论",
    "rumor_fact_confusion_risk": "谣言与事实并存、真相难以澄清",
    # 信息安全与意识形态类
    "ai_deepfake_abuse_risk": "AI 合成、伪造视频/语音/图文被传播或滥用",
    "data_network_security_risk": "数据泄露、网络安全事件、平台漏洞",
    "ideology_foreign_narrative_risk": "境外信息操纵、涉外叙事、意识形态对冲",
    "tech_ethics_ai_governance_risk": "算法歧视、科技伦理、关键基础设施技术风险",
    # 治理执行压力类
    "public_service_response_pressure_risk": "公共服务供给不足、回应能力受压",
    "grassroots_governance_pressure_risk": "街道/社区/基层一线承压",
    "cross_dept_coordination_boundary_risk": "部门协同失败、责任互相推诿",
    "platform_governance_consumer_overflow_risk": "平台/消费争议外溢为公共事件",
    # 经济金融类
    "financial_market_instability_risk": "股市/债市/汇市剧烈波动或危机信号",
    "local_debt_fiscal_risk": "地方债、城投债、财政可持续性",
    "employment_labor_dispute_risk": "大规模裁员、欠薪、劳资纠纷",
    "housing_estate_risk": "房价、烂尾、断供、地产债务",
    "financial_fraud_illegal_fundraising_risk": "P2P、虚拟货币、养老诈骗、非法集资",
}

_SYSTEM_PROMPT = (
    "You are a risk classification expert for a government governance "
    "simulation system.\n"
    "You will receive a compressed summary of a simulated public opinion event.\n"
    "You will also receive a catalog of 26 risk types grouped by domain.\n"
    "Your task: select the top 3 most applicable risk types for this event.\n"
    "Ensure the 3 selected types cover different risk dimensions if the event "
    "evidence supports it — prefer diversity across domains.\n"
    "Output ONLY valid type IDs from the catalog. Do not invent new types.\n"
    "Output exactly 3 types, ordered by relevance (most relevant first).\n"
    "Return a JSON object with a 'primary_types' array."
)

# How many of the latest active speakers to surface as representative comments.
_NUM_RECENT_COMMENTS = 4
_TICKS_TO_SCAN_FOR_COMMENTS = 3
_COMMENT_MAX_CHARS = 80




class RiskClassifier:
    """Compresses simulation data and asks the LLM to pick Top-3 risk types."""

    # ------------------------------------------------------------------
    # Query text construction
    # ------------------------------------------------------------------

    @staticmethod
    def _format_metric(value: Any, fmt: str = ".2f") -> str:
        if value is None:
            return "n/a"
        try:
            return format(value, fmt)
        except (TypeError, ValueError):
            return str(value)

    def _pick_representative_comments(
        self, tick_logs: List[TickLog],
    ) -> List[Dict[str, Any]]:
        """Pick up to 3-5 active speakers from the final 2-3 ticks.

        Selection rules (in order of preference, then by tick descending):
        1. Active speaker in the most recent tick.
        2. Sort by stance_score absolute deviation from the final mean (most
           diagnostic of polarized voices).
        3. Deduplicate by (group_name, comment prefix).
        """
        if not tick_logs:
            return []

        recent = tick_logs[-_TICKS_TO_SCAN_FOR_COMMENTS:]
        final_mean = tick_logs[-1].global_metrics.mean_stance

        candidates: List[Dict[str, Any]] = []
        seen: set = set()
        for tl in reversed(recent):
            for entry in tl.entries:
                if entry.speaker_status != "active":
                    continue
                if not entry.comment:
                    continue
                dedup_key = (entry.group_name, entry.comment[:30])
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                candidates.append({
                    "tick": tl.tick,
                    "group_name": entry.group_name,
                    "stance_score": entry.current_stance,
                    "stance_deviation": abs(entry.current_stance - final_mean),
                    "comment": entry.comment,
                })

        candidates.sort(
            key=lambda c: (c["stance_deviation"], c["tick"]),
            reverse=True,
        )
        return candidates[:_NUM_RECENT_COMMENTS]

    def _build_query_text(
        self,
        extraction_output: EntityExtractionOutput,
        tick_logs: List[TickLog],
        x_t_sequence: List[float],
        simulation_result: Dict[str, Any],
    ) -> str:
        """Compress simulation data into a stable query text (~400-500 tokens)."""
        # --- Event header ---
        event_lines: List[str] = [
            "[Event]",
            f"name: {extraction_output.event_summary}",
            f"type: {extraction_output.event_type}",
            f"scale: {self._format_metric(extraction_output.event_scale, '.2f')}",
            f"controversy: {self._format_metric(extraction_output.event_controversy, '.2f')}",
        ]

        risk_verdict = simulation_result.get("risk_verdict", {}) or {}
        event_lines.append(
            f"risk_level: {risk_verdict.get('label') or risk_verdict.get('level') or 'n/a'}"
        )

        # --- Key entities (name + type + role) ---
        entity_lines = ["[Key Entities]"]
        for ent in extraction_output.event_entities[:8]:
            entity_lines.append(
                f"- {ent.name} | {ent.type} | role={ent.role}"
            )
        if len(extraction_output.event_entities) > 8:
            entity_lines.append(
                f"- ... +{len(extraction_output.event_entities) - 8} more"
            )

        # --- Key groups with final stance + max delta ---
        stance_matrix = simulation_result.get("agent_stance_matrix") or []
        group_lines = ["[Key Groups]"]
        if stance_matrix:
            sorted_rows = sorted(
                stance_matrix,
                key=lambda r: r.get("max_delta", 0) if isinstance(r, dict) else 0,
                reverse=True,
            )[:6]
            for row in sorted_rows:
                if not isinstance(row, dict):
                    continue
                group_lines.append(
                    f"- {row.get('group_name', '?')} | "
                    f"final={self._format_metric(row.get('final_stance'), '.1f')} | "
                    f"max_delta={self._format_metric(row.get('max_delta'), '.2f')}"
                )
        else:
            group_lines.append("- (no agent_stance_matrix)")

        # --- Representative comments ---
        comment_lines = ["[Representative Comments]"]
        rep_comments = self._pick_representative_comments(tick_logs)
        if rep_comments:
            for c in rep_comments:
                txt = (c["comment"] or "").strip().replace("\n", " ")
                if len(txt) > _COMMENT_MAX_CHARS:
                    txt = txt[: _COMMENT_MAX_CHARS - 1] + "…"
                comment_lines.append(
                    f"- tick={c['tick']} {c['group_name']} "
                    f"(stance={self._format_metric(c['stance_score'], '.1f')}): {txt}"
                )
        else:
            comment_lines.append("- (no active comments in final ticks)")

        # --- Metrics ---
        final_x = x_t_sequence[-1] if x_t_sequence else None
        start_x = x_t_sequence[0] if x_t_sequence else None
        negative_trend = (
            max(0.0, start_x - final_x)
            if (start_x is not None and final_x is not None and len(x_t_sequence) > 1)
            else 0.0
        )
        final_pol = (
            tick_logs[-1].global_metrics.polarization_index if tick_logs else None
        )
        # max_negative_shift from stance matrix
        max_neg_shift = 0.0
        if stance_matrix:
            for row in stance_matrix:
                if not isinstance(row, dict):
                    continue
                init = row.get("initial_stance")
                final = row.get("final_stance")
                if init is None or final is None:
                    continue
                max_neg_shift = max(max_neg_shift, max(0.0, init - final))

        metric_lines = [
            "[Metrics]",
            f"final_x (mean stance): {self._format_metric(final_x, '.2f')}",
            f"final_polarization_index: {self._format_metric(final_pol, '.2f')}",
            f"negative_trend: {self._format_metric(negative_trend, '.2f')}",
            f"max_negative_shift: {self._format_metric(max_neg_shift, '.2f')}",
        ]

        return "\n".join(
            event_lines + [""] + entity_lines + [""] + group_lines + [""] +
            comment_lines + [""] + metric_lines
        )

    # ------------------------------------------------------------------
    # Type catalog construction
    # ------------------------------------------------------------------

    def _build_type_catalog(self) -> str:
        """Build the 26-type catalog — one line per type.

        Format: `<type_id>: <label> | <domain_label> | <typical_scenario>`
        """
        lines: List[str] = []
        for type_id, domain_id in TYPE_TO_DOMAIN_MAP.items():
            label = RISK_TYPE_LABELS.get(type_id, type_id)
            domain_label = DOMAIN_LABELS.get(domain_id, domain_id)
            scenario = _TYPE_SCENARIOS.get(type_id, "")
            lines.append(f"{type_id}: {label} | {domain_label} | {scenario}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_primary_types(primary_types: List[str]) -> None:
        if len(primary_types) != 3:
            raise ValueError(
                f"primary_types must contain exactly 3 entries, got {len(primary_types)}: "
                f"{primary_types}"
            )
        if len(set(primary_types)) != 3:
            raise ValueError(f"primary_types contains duplicates: {primary_types}")
        invalid = [t for t in primary_types if t not in RISK_TYPE_LABELS]
        if invalid:
            raise ValueError(f"primary_types contains unknown risk types: {invalid}")
        # Also require them to be in the 26-type taxonomy (not the legacy 13).
        invalid_legacy = [t for t in primary_types if t not in TYPE_TO_DOMAIN_MAP]
        if invalid_legacy:
            raise ValueError(
                f"primary_types contains legacy/non-26-type IDs: {invalid_legacy}. "
                f"RiskClassifier only emits types from the 26-type taxonomy."
            )
        # Warn if all 3 types map to the same domain (non-blocking)
        domains = set(TYPE_TO_DOMAIN_MAP[t] for t in primary_types if t in TYPE_TO_DOMAIN_MAP)
        if len(domains) == 1:
            domain_label = DOMAIN_LABELS.get(list(domains)[0], list(domains)[0])
            import logging
            logging.warning(
                "RiskClassifier: all 3 types in single domain '%s': %s",
                domain_label, primary_types,
            )

    def classify(
        self,
        extraction_output: EntityExtractionOutput,
        tick_logs: List[TickLog],
        x_t_sequence: List[float],
        simulation_result: Dict[str, Any],
    ) -> ClassificationOutput:
        """Build query text → call LLM → parse response → validate.

        The LLM is called as `caller="classify"`, which the TokenTracker maps to
        the "Phase 3 Parser" phase.
        """
        query_text = self._build_query_text(
            extraction_output, tick_logs, x_t_sequence, simulation_result
        )
        catalog = self._build_type_catalog()

        user_prompt = (
            "You are given a compressed summary of a simulated public opinion "
            "event and a catalog of 26 risk types. "
            "Select the top 3 most applicable risk types.\n\n"
            "### Event Summary\n"
            f"{query_text}\n\n"
            "### Risk Type Catalog\n"
            f"{catalog}\n\n"
            "Select exactly 3 risk types from the catalog above.\n"
            "Output as JSON: {\"primary_types\": [\"type_id_1\", "
            "\"type_id_2\", \"type_id_3\"]}"
        )

        llm = get_llm_client()
        result = llm.generate(
            system=_SYSTEM_PROMPT,
            user=user_prompt,
            response_model=ClassificationOutput,
        )

        # Defensive validation — LLMClient already validates via Pydantic, but
        # we also enforce the 26-type taxonomy constraint here.
        self._validate_primary_types(result.primary_types)
        return result


__all__ = ["RiskClassifier"]
