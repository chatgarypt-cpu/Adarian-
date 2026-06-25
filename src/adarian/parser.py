"""Phase 3: Simulation Dataset Parser — 纯编排聚合层"""
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from adarian.schemas.phase1 import EntityExtractionOutput
from adarian.schemas.phase2 import Phase2Output
from adarian.schemas.phase3 import TickLog
from adarian.analysis.risk_analyzer import RiskAnalyzer
from adarian.analysis.inflection_detector import InflectionDetector
from adarian.analysis.stance_analyzer import StanceAnalyzer
from adarian.analysis.classifier import RiskClassifier
from adarian.schemas.phase4 import (
    DOMAIN_LABELS,
    RISK_LEVEL_LABELS,
    RISK_TYPE_LABELS,
    TYPE_TO_DOMAIN_MAP,
)


class SimulationDatasetParser:
    def __init__(self):
        self._risk_analyzer = RiskAnalyzer()
        self._inflection_detector = InflectionDetector()
        self._stance_analyzer = StanceAnalyzer()
        self._risk_classifier = RiskClassifier()

    def parse(
        self,
        extraction_output: EntityExtractionOutput,
        phase2_output: Phase2Output,
        tick_logs: List[TickLog],
        x_t_sequence: List[float],
        *,
        seed_text: str = "",
        source_artifact_refs: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Parse simulation outputs into a structured dataset."""

        # Audience mode
        audience_mode = self._risk_analyzer.determine_audience_mode(extraction_output)

        # Risk assessment
        risk_level, risk_basis = self._risk_analyzer.assess_risk(
            x_t_sequence, tick_logs, extraction_output=extraction_output
        )
        signals = self._risk_analyzer.compute_signals(
            x_t_sequence, tick_logs, extraction_output=extraction_output
        )

        # Inflection detection
        inflection_points = self._inflection_detector.detect(
            tick_logs, phase2_output
        )

        # Stance analysis
        agent_stance_matrix = self._stance_analyzer.build_agent_stance_matrix(tick_logs)

        # RiskClassifier — LLM-based Top-3 from the 28-type taxonomy.
        # Must run after agent_stance_matrix is built (consumed in query text)
        # and before risk_type_classification dict is assembled.
        from adarian.utils.runtime_logger import get_runtime_logger
        _log = get_runtime_logger()
        _log.log_phase_start("analysis_risk_classifier")
        _risk_t0 = time.time()
        classification_output = self._risk_classifier.classify(
            extraction_output,
            tick_logs,
            x_t_sequence,
            {  # simulation_result is built last; assemble a minimal one for the classifier
                "x_t_sequence": x_t_sequence,
                "risk_verdict": {
                    "level": risk_level.value if hasattr(risk_level, 'value') else str(risk_level),
                    "label": RISK_LEVEL_LABELS.get(
                        risk_level.value if hasattr(risk_level, 'value') else str(risk_level),
                        str(risk_level),
                    ),
                    "basis_text": risk_basis,
                    "signals": signals,
                },
                "agent_stance_matrix": agent_stance_matrix,
            },
        )
        _log.log_phase_end("analysis_risk_classifier", time.time() - _risk_t0)

        # Emotion trajectory
        emotion_trajectory = []
        for tl in tick_logs:
            emotion_trajectory.append({
                "tick": tl.tick,
                "mean_stance": tl.global_metrics.mean_stance,
                "std_stance": tl.global_metrics.std_stance,
                "polarization_index": tl.global_metrics.polarization_index,
                "key_event": "",
            })

        # Full per-tick per-agent entries
        tick_entries = []
        for tl in tick_logs:
            tick_entries.append({
                "tick": tl.tick,
                "entries": [
                    {
                        "agent_id": e.agent_id,
                        "group_name": e.group_name,
                        "comment": e.comment,
                        "previous_stance": e.previous_stance,
                        "current_stance": e.current_stance,
                        "stance_delta": e.stance_delta,
                        "reasoning": e.reasoning,
                        "speaker_status": e.speaker_status,
                        "susceptibility": e.susceptibility,
                        "change_reason": e.change_reason,
                    }
                    for e in tl.entries
                ],
            })

        # Final metrics
        final_x = x_t_sequence[-1] if x_t_sequence else None
        final_pol = tick_logs[-1].global_metrics.polarization_index if tick_logs else None

        dataset = {
            "_schema_version": "v2",
            "_generated_by": "phase3_parser",
            "run_info": {
                "event_name": extraction_output.event_summary,
                "event_scale": extraction_output.event_scale,
                "event_controversy": extraction_output.event_controversy,
                "event_type": extraction_output.event_type,
                "total_ticks": len(tick_logs),
                "audience_mode": audience_mode,
                "seed_text": seed_text,
            },
            "source_context": {
                "event_summary": extraction_output.event_summary,
                "event_type": extraction_output.event_type,
                "event_entities": [
                    {
                        "name": e.name,
                        "type": e.type,
                        "role": e.role,
                        "can_speak": e.can_speak,
                        "original_statement": e.original_statement,
                    }
                    for e in extraction_output.event_entities
                ],
                "opinion_spreaders": [
                    {
                        "group_name": s.group_name,
                        "related_event_entity": s.related_event_entity,
                        "stance_score": s.stance_score,
                        "estimated_percentage": s.estimated_percentage,
                    }
                    for s in extraction_output.opinion_spreaders
                ],
                "relations": [
                    {
                        "source": r.source,
                        "target": r.target,
                        "type": r.type,
                    }
                    for r in extraction_output.relations
                ],
            },
            "simulation_result": {
                "x_t_sequence": x_t_sequence,
                "final_x": final_x,
                "final_polarization_index": final_pol,
                "emotion_trajectory": emotion_trajectory,
                "tick_entries": tick_entries,
                "inflection_points": inflection_points,
                "risk_verdict": {
                    "level": risk_level.value if hasattr(risk_level, 'value') else str(risk_level),
                    "label": RISK_LEVEL_LABELS.get(risk_level.value if hasattr(risk_level, 'value') else str(risk_level), str(risk_level)),
                    "basis_text": risk_basis,
                    "signals": signals,
                },
                "risk_type_classification": {
                    "primary_types": classification_output.primary_types,
                    "type_labels": [RISK_TYPE_LABELS[t] for t in classification_output.primary_types],
                    "primary_domain": TYPE_TO_DOMAIN_MAP.get(classification_output.primary_types[0], ""),
                    "primary_domain_label": DOMAIN_LABELS.get(
                        TYPE_TO_DOMAIN_MAP.get(classification_output.primary_types[0], ""), ""
                    ),
                },
                "agent_stance_matrix": agent_stance_matrix,
            },
            "source_artifact_refs": source_artifact_refs or {
                "tick_logs": "",
                "entities_and_relations": "",
                "social_graph": "",
            },
            "known_limitations": [],
        }

        return dataset
