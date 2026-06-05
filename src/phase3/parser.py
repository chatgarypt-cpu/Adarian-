"""Phase 3: Simulation Dataset Parser — 纯编排聚合层"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.schemas.phase1 import EntityExtractionOutput
from src.schemas.phase2 import Phase2Output
from src.schemas.phase3 import TickLog
from src.phase3.risk_analyzer import RiskAnalyzer
from src.phase3.inflection_detector import InflectionDetector
from src.phase3.stance_analyzer import StanceAnalyzer


class SimulationDatasetParser:
    def __init__(self):
        self._risk_analyzer = RiskAnalyzer()
        self._inflection_detector = InflectionDetector()
        self._stance_analyzer = StanceAnalyzer()

    def parse(
        self,
        extraction_output: EntityExtractionOutput,
        phase2_output: Phase2Output,
        tick_logs: List[TickLog],
        x_t_sequence: List[float],
        *,
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

        # Risk type classification
        risk_types = self._risk_analyzer.classify_risk_types(
            audience_mode, risk_basis, tick_logs
        )
        from src.schemas.phase4 import RISK_LEVEL_LABELS, RISK_TYPE_LABELS
        risk_type_labels = [RISK_TYPE_LABELS.get(rt, rt) for rt in risk_types]

        # Inflection detection
        inflection_points = self._inflection_detector.detect(
            tick_logs, phase2_output
        )

        # Stance analysis
        agent_stance_matrix = self._stance_analyzer.build_agent_stance_matrix(tick_logs)

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

        # Final metrics
        final_x = x_t_sequence[-1] if x_t_sequence else None
        final_pol = tick_logs[-1].global_metrics.polarization_index if tick_logs else None

        dataset = {
            "_schema_version": "v1",
            "_generated_by": "phase3_parser",
            "run_info": {
                "event_name": extraction_output.event_summary,
                "event_scale": extraction_output.event_scale,
                "event_controversy": extraction_output.event_controversy,
                "event_type": extraction_output.event_type,
                "total_ticks": len(tick_logs),
                "audience_mode": audience_mode,
            },
            "simulation_result": {
                "x_t_sequence": x_t_sequence,
                "final_x": final_x,
                "final_polarization_index": final_pol,
                "emotion_trajectory": emotion_trajectory,
                "inflection_points": inflection_points,
                "risk_verdict": {
                    "level": risk_level.value if hasattr(risk_level, 'value') else str(risk_level),
                    "label": RISK_LEVEL_LABELS.get(risk_level.value if hasattr(risk_level, 'value') else str(risk_level), str(risk_level)),
                    "basis_text": risk_basis,
                    "signals": signals,
                },
                "risk_type_classification": {
                    "primary_types": risk_types,
                    "type_labels": risk_type_labels,
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

    def save_dataset(self, dataset: Dict[str, Any], output_path: str) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
