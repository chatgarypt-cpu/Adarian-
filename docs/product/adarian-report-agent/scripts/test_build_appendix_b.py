"""Full integration tests for build_appendix_b.py.

Run with: pytest scripts/test_build_appendix_b.py -v
"""

import json
import re
import sys
import shutil
import time
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import build_appendix_b as builder
from build_appendix_b import (
    parse_input_json,
    load_aggregation_config,
    load_simulation_datasets,
    aggregate_multi_world,
    filter_by_schema,
    write_appendix_b,
    build_safe_event_slug,
    load_risk_mapping,
    load_risk_policy,
    validate_risk_sections,
    main,
)


def _valid_risk(
    *,
    type_id="negative_narrative_aggregation_risk",
    type_label="负向叙事聚合风险",
    domain="communication_evolution",
    domain_label="传播演化类",
    level_id="medium",
    level_label="中风险",
    trigger_reason="负向叙事持续聚合",
):
    return {
        "type_id": type_id,
        "type_label": type_label,
        "domain": domain,
        "domain_label": domain_label,
        "level_id": level_id,
        "level_label": level_label,
        "trigger_signals": ["negative_trend"],
        "trigger_reason": trigger_reason,
        "reality_translation": "负面讨论持续聚集，可能放大公众对事件处置的质疑。",
    }


def _valid_measure(risk):
    return {
        "risk_type_id": risk["type_id"],
        "risk_label": risk["type_label"],
        "trigger_reason_ref": risk["trigger_reason"],
        "level_id_ref": risk["level_id"],
        "responsible_body": "事件主体",
        "action_direction": "信息公开与解释回应",
        "measure": "围绕风险及时发布事实说明和处置进展。",
    }


def _remove_test_workdir(workdir):
    for attempt in range(3):
        try:
            shutil.rmtree(workdir)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            # The managed Windows sandbox allows test writes in the workspace
            # but denies child-process deletion; leave an ignored artifact.
            return
        except OSError:
            if attempt == 2:
                raise
            time.sleep(0.05)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_workdir(request):
    """Create a per-test working directory.

    Codex's Windows sandbox denies writes inside directories created through
    tempfile.TemporaryDirectory(), so use a normal workspace-relative directory.
    """
    safe_name = "".join(
        ch if ch.isalnum() or ch in ("_", "-") else "_"
        for ch in request.node.name
    )[:80]
    root = Path(__file__).parent / ".test_workdir"
    workdir = root / f"{safe_name}_{uuid.uuid4().hex}"
    workdir.mkdir(parents=True, exist_ok=False)
    yield workdir
    _remove_test_workdir(workdir)


@pytest.fixture
def _make_input_json(tmp_workdir):
    """Factory: create an input JSON with given overrides."""
    def _make(
        *,
        event_name="测试事件",
        seed_text="测试事件材料内容",
        worlds_data=None,
        world_count=1,
    ):
        if worlds_data is None:
            worlds_data = []
            for i in range(world_count):
                wdir = tmp_workdir / f"world_{i}"
                wdir.mkdir(parents=True, exist_ok=True)
                sim = {
                    "run_info": {"event_scale": 0.8, "event_controversy": 0.6},
                    "simulation_result": {
                        "risk_verdict": {"level": "medium", "signals": {}},
                        "risk_type_classification": {"primary_types": []},
                    },
                }
                (wdir / "simulation_dataset.json").write_text(
                    json.dumps(sim, ensure_ascii=False), encoding="utf-8"
                )
                worlds_data.append({
                    "label": f"world_{i}",
                    "simulation_dataset_path": str(wdir / "simulation_dataset.json"),
                })

        seed_file = tmp_workdir / "seed.txt"
        seed_file.write_text(seed_text, encoding="utf-8")

        input_data = {
            "event_name": event_name,
            "seed_input_path": str(seed_file),
            "worlds": worlds_data,
        }
        input_path = tmp_workdir / "input.json"
        input_path.write_text(json.dumps(input_data, ensure_ascii=False), encoding="utf-8")
        return input_path
    return _make


@pytest.fixture
def minimal_input_json(_make_input_json):
    """Minimal valid input JSON with one world."""
    return _make_input_json()


@pytest.fixture
def multi_world_input_json(_make_input_json):
    """Input JSON with 3 worlds for aggregation tests."""
    return _make_input_json(world_count=3)


# ===================================================================
# parse_input_json
# ===================================================================

class TestParseInputJson:
    # -- happy path (pre-existing) --
    def test_returns_dict_with_required_keys(self, minimal_input_json):
        result = parse_input_json(str(minimal_input_json))
        assert isinstance(result, dict)
        assert "event_name" in result
        assert "seed_input_path" in result
        assert "worlds" in result

    def test_event_name_is_string(self, minimal_input_json):
        result = parse_input_json(str(minimal_input_json))
        assert isinstance(result["event_name"], str)
        assert len(result["event_name"]) > 0

    def test_worlds_is_non_empty_list(self, minimal_input_json):
        result = parse_input_json(str(minimal_input_json))
        assert isinstance(result["worlds"], list)
        assert len(result["worlds"]) >= 1

    def test_each_world_has_label_and_path(self, minimal_input_json):
        result = parse_input_json(str(minimal_input_json))
        for w in result["worlds"]:
            assert "label" in w
            assert "simulation_dataset_path" in w

    def test_raises_filenotfound_for_missing_input(self):
        with pytest.raises(FileNotFoundError):
            parse_input_json(str(Path("nonexistent_dir") / "input.json"))

    def test_raises_valueerror_for_invalid_json(self, tmp_workdir):
        bad_path = tmp_workdir / "bad.json"
        bad_path.write_text("not valid json {{{", encoding="utf-8")
        with pytest.raises(ValueError):
            parse_input_json(str(bad_path))

    def test_accepts_utf8_bom_input_json(self, tmp_workdir):
        p = tmp_workdir / "bom_input.json"
        payload = {
            "event_name": "x",
            "seed_input_path": "./seed.txt",
            "worlds": [{"label": "w0", "simulation_dataset_path": "./w0.json"}],
        }
        p.write_bytes("\ufeff".encode("utf-8") + json.dumps(payload).encode("utf-8"))
        result = parse_input_json(str(p))
        assert result["event_name"] == "x"

    # -- H-2: schema validation --
    def test_raises_valueerror_when_event_name_missing(self, tmp_workdir):
        p = tmp_workdir / "no_event_name.json"
        p.write_text(json.dumps({"seed_input_path": "/x", "worlds": [{}]}), encoding="utf-8")
        with pytest.raises(ValueError, match="event_name"):
            parse_input_json(str(p))

    def test_raises_valueerror_when_seed_input_path_missing(self, tmp_workdir):
        p = tmp_workdir / "no_seed.json"
        p.write_text(json.dumps({"event_name": "x", "worlds": [{}]}), encoding="utf-8")
        with pytest.raises(ValueError, match="seed_input_path"):
            parse_input_json(str(p))

    def test_raises_valueerror_when_worlds_missing(self, tmp_workdir):
        p = tmp_workdir / "no_worlds.json"
        p.write_text(json.dumps({"event_name": "x", "seed_input_path": "/x"}), encoding="utf-8")
        with pytest.raises(ValueError, match="worlds"):
            parse_input_json(str(p))

    def test_raises_valueerror_when_worlds_empty(self, tmp_workdir):
        p = tmp_workdir / "empty_worlds.json"
        p.write_text(json.dumps({"event_name": "x", "seed_input_path": "/x", "worlds": []}), encoding="utf-8")
        with pytest.raises(ValueError, match="at least"):
            parse_input_json(str(p))

    def test_raises_valueerror_when_world_missing_label(self, tmp_workdir):
        p = tmp_workdir / "no_label.json"
        p.write_text(json.dumps({
            "event_name": "x", "seed_input_path": "/x",
            "worlds": [{"simulation_dataset_path": "/y"}]
        }), encoding="utf-8")
        with pytest.raises(ValueError, match="label"):
            parse_input_json(str(p))

    def test_raises_valueerror_when_world_missing_path(self, tmp_workdir):
        p = tmp_workdir / "no_ds_path.json"
        p.write_text(json.dumps({
            "event_name": "x", "seed_input_path": "/x",
            "worlds": [{"label": "w0"}]
        }), encoding="utf-8")
        with pytest.raises(ValueError, match="simulation_dataset_path"):
            parse_input_json(str(p))

    def test_raises_valueerror_when_event_name_not_string(self, tmp_workdir):
        p = tmp_workdir / "bad_type.json"
        p.write_text(json.dumps({"event_name": 123, "seed_input_path": "/x", "worlds": [{"label": "w", "simulation_dataset_path": "/y"}]}), encoding="utf-8")
        with pytest.raises(ValueError, match="event_name"):
            parse_input_json(str(p))


# ===================================================================
# build_safe_event_slug
# ===================================================================

class TestBuildSafeEventSlug:
    def test_preserves_alphanumeric_and_chinese(self):
        assert "测试事件ABC123" in build_safe_event_slug("测试事件ABC123")

    def test_replaces_windows_illegal_chars(self):
        result = build_safe_event_slug("事件:测试/验证?")
        assert ":" not in result
        assert "/" not in result
        assert "?" not in result

    def test_collapses_consecutive_underscores(self):
        result = build_safe_event_slug("事件//测试??验证")
        assert "__" not in result

    def test_limits_to_80_chars(self):
        long_name = "测" * 100
        assert len(build_safe_event_slug(long_name)) <= 80

    def test_empty_input_returns_fallback(self):
        assert build_safe_event_slug("") == "untitled_event"

    # -- M-3: edge-case hardening --
    def test_strips_newlines_and_carriage_returns(self):
        result = build_safe_event_slug("事件\r\n名称")
        assert "\r" not in result
        assert "\n" not in result
        assert "事件_名称" in result or "事件名称" in result

    def test_strips_tabs_and_vertical_whitespace(self):
        result = build_safe_event_slug("事\t件\v名")
        assert "\t" not in result
        assert "\v" not in result

    def test_all_whitespace_input_returns_fallback(self):
        result = build_safe_event_slug("   \t  \n  ")
        assert result == "untitled_event"

    def test_filters_zero_width_chars(self):
        # zero-width space U+200B and zero-width non-joiner U+200C
        result = build_safe_event_slug("事件​名称‌测试")
        assert "​" not in result
        assert "‌" not in result

    def test_preserves_emoji(self):
        result = build_safe_event_slug("事件🔥测试")
        assert "🔥" in result

    def test_strips_leading_trailing_underscores(self):
        result = build_safe_event_slug("___事件___")
        assert not result.startswith("_")
        assert not result.endswith("_")


# ===================================================================
# load_simulation_datasets
# ===================================================================

class TestLoadSimulationDatasets:
    def test_returns_list_of_dicts(self, minimal_input_json):
        input_data = parse_input_json(str(minimal_input_json))
        result = load_simulation_datasets(
            input_data["worlds"],
            str(Path(minimal_input_json).parent),
        )
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)

    def test_result_count_matches_world_count(self, multi_world_input_json):
        input_data = parse_input_json(str(multi_world_input_json))
        result = load_simulation_datasets(
            input_data["worlds"],
            str(Path(multi_world_input_json).parent),
        )
        assert len(result) == 3

    def test_raises_filenotfound_for_missing_dataset(self, tmp_workdir):
        missing = tmp_workdir / "missing.json"  # file never created
        worlds = [{"label": "ghost", "simulation_dataset_path": str(missing)}]
        with pytest.raises(FileNotFoundError):
            load_simulation_datasets(worlds, str(tmp_workdir))

    def test_raises_valueerror_for_corrupt_dataset_json(self, tmp_workdir):
        bad = tmp_workdir / "bad.json"
        bad.write_text("{{ not json", encoding="utf-8")
        worlds = [{"label": "bad", "simulation_dataset_path": str(bad)}]
        with pytest.raises(ValueError):
            load_simulation_datasets(worlds, str(tmp_workdir))


# ===================================================================
# load_aggregation_config
# ===================================================================

class TestLoadAggregationConfig:
    def test_loads_project_yaml_subset(self, tmp_workdir):
        config_path = tmp_workdir / "aggregation_config.yaml"
        config_path.write_text(
            "\n".join([
                "version: 1",
                "numeric_metrics:",
                "  - output_prefix: custom_scale",
                "    source_path: run_info.event_scale",
                "    aggregate: mean",
                "    keep_distribution: true",
                "frequency_metrics:",
                "  custom_levels:",
                "    source_path: simulation_result.risk_verdict.level",
            ]),
            encoding="utf-8",
        )
        config = load_aggregation_config(config_path)
        assert config["numeric_metrics"][0]["output_prefix"] == "custom_scale"
        assert config["frequency_metrics"]["custom_levels"]["source_path"] == (
            "simulation_result.risk_verdict.level"
        )

    def test_loads_risk_order_and_source_whitelists(self, tmp_workdir):
        config_path = tmp_workdir / "aggregation_config.yaml"
        config_path.write_text(
            "\n".join([
                "version: 1",
                "risk_level_order:",
                "  low: 1",
                "  medium: 2",
                "  high: 3",
                "bounded_source_evidence:",
                "  risk_verdict:",
                "    - level",
                "    - label",
                "    - signals",
                "  risk_type_classification:",
                "    - primary_types",
                "evolution_source_fields:",
                "  - source_context.event_entities",
                "  - simulation_result.emotion_trajectory",
            ]),
            encoding="utf-8",
        )
        config = load_aggregation_config(config_path)
        assert config["risk_level_order"] == {"low": 1, "medium": 2, "high": 3}
        assert config["bounded_source_evidence"]["risk_verdict"] == [
            "level",
            "label",
            "signals",
        ]
        assert config["bounded_source_evidence"]["risk_type_classification"] == [
            "primary_types"
        ]
        assert config["evolution_source_fields"] == [
            "source_context.event_entities",
            "simulation_result.emotion_trajectory",
        ]


# ===================================================================
# aggregate_multi_world
# ===================================================================

class TestAggregateMultiWorld:
    def test_single_world_returns_identity(self):
        datasets = [{"run_info": {"event_scale": 0.8}}]
        result = aggregate_multi_world(datasets, {})
        assert result["event_scale_avg"] == 0.8
        assert result["event_scale_distribution"] == [0.8]

    def test_multi_world_computes_mean(self):
        datasets = [
            {"run_info": {"event_scale": 0.6}},
            {"run_info": {"event_scale": 0.8}},
            {"run_info": {"event_scale": 1.0}},
        ]
        result = aggregate_multi_world(datasets, {})
        assert result["event_scale_avg"] == pytest.approx(0.8)

    def test_multi_world_returns_distribution(self):
        datasets = [
            {"run_info": {"event_scale": 0.6}},
            {"run_info": {"event_scale": 0.8}},
        ]
        result = aggregate_multi_world(datasets, {})
        assert "event_scale_distribution" in result
        assert len(result["event_scale_distribution"]) == 2

    def test_handles_empty_datasets(self):
        result = aggregate_multi_world([], {})
        assert result == {}

    def test_uses_configured_numeric_and_frequency_metrics(self):
        datasets = [
            {
                "run_info": {"event_scale": 0.4},
                "simulation_result": {"risk_verdict": {"level": "low"}},
            },
            {
                "run_info": {"event_scale": 0.8},
                "simulation_result": {"risk_verdict": {"level": "high"}},
            },
        ]
        config = {
            "numeric_metrics": [
                {"output_prefix": "custom_scale", "source_path": "run_info.event_scale"}
            ],
            "frequency_metrics": {
                "custom_levels": {
                    "source_path": "simulation_result.risk_verdict.level"
                }
            },
        }
        result = aggregate_multi_world(datasets, config)
        assert result["custom_scale_avg"] == pytest.approx(0.6)
        assert result["custom_scale_distribution"] == [0.4, 0.8]
        assert result["custom_levels"] == {"low": 1, "high": 1}

    # -- Phase 3: deterministic aggregation contract --
    def test_counts_risk_level_distribution(self):
        datasets = [
            {"simulation_result": {"risk_verdict": {"level": "high"}}},
            {"simulation_result": {"risk_verdict": {"level": "medium"}}},
            {"simulation_result": {"risk_verdict": {"level": "high"}}},
        ]
        result = aggregate_multi_world(datasets, {})
        assert result["risk_level_distribution"] == {"high": 2, "medium": 1}

    def test_counts_risk_type_frequency(self):
        datasets = [
            {"simulation_result": {"risk_type_classification": {"primary_types": ["a", "b"]}}},
            {"simulation_result": {"risk_type_classification": {"primary_types": ["a", "c"]}}},
            {"simulation_result": {"risk_type_classification": {"primary_types": ["b"]}}},
        ]
        result = aggregate_multi_world(datasets, {})
        assert result["risk_type_frequency"] == {"a": 2, "b": 2, "c": 1}

    def test_preserves_bounded_world_evidence(self):
        datasets = [
            {
                "_world_label": "world_0",
                "run_info": {"event_scale": 0.8, "event_controversy": 0.7},
                "simulation_result": {
                    "risk_verdict": {
                        "level": "high",
                        "label": "高风险",
                        "basis_text": "basis",
                        "signals": {"negative_trend": 0.4},
                    },
                    "risk_type_classification": {
                        "primary_types": ["negative_narrative_aggregation_risk"],
                        "type_labels": ["负向叙事聚合风险"],
                        "primary_domain": "communication_evolution",
                        "primary_domain_label": "传播演化类",
                    },
                },
            }
        ]
        result = aggregate_multi_world(datasets, {})
        assert result["world_evidence"][0]["label"] == "world_0"
        assert result["world_evidence"][0]["risk_verdict"]["level"] == "high"
        assert result["world_evidence"][0]["risk_verdict"]["signals"] == {"negative_trend": 0.4}
        assert result["world_evidence"][0]["risk_type_classification"]["primary_types"] == [
            "negative_narrative_aggregation_risk"
        ]

    def test_uses_configured_bounded_source_evidence(self):
        datasets = [
            {
                "_world_label": "world_0",
                "simulation_result": {
                    "risk_verdict": {
                        "level": "high",
                        "label": "High",
                        "basis_text": "basis",
                        "signals": {"negative_trend": 0.4},
                    },
                    "risk_type_classification": {
                        "primary_types": ["negative_narrative_aggregation_risk"],
                        "type_labels": ["Negative narrative"],
                    },
                },
            }
        ]
        config = {
            "bounded_source_evidence": {
                "risk_verdict": ["level"],
                "risk_type_classification": ["primary_types"],
            }
        }
        result = aggregate_multi_world(datasets, config)
        assert result["world_evidence"][0]["risk_verdict"] == {"level": "high"}
        assert result["world_evidence"][0]["risk_type_classification"] == {
            "primary_types": ["negative_narrative_aggregation_risk"]
        }

    def test_computes_worst_reasonable_level_and_outliers(self):
        datasets = [
            {"_world_label": "base", "simulation_result": {"risk_verdict": {"level": "low", "label": "Low"}}},
            {"_world_label": "pressure", "simulation_result": {"risk_verdict": {"level": "medium", "label": "Medium"}}},
            {"_world_label": "stress", "simulation_result": {"risk_verdict": {"level": "high", "label": "High"}}},
        ]
        config = {"risk_level_order": {"low": 1, "medium": 2, "high": 3}}
        result = aggregate_multi_world(datasets, config)
        assert result["worst_reasonable_level"] == "high"
        assert result["worst_reasonable_level_label"] == "High"
        assert result["outlier_worlds"] == ["stress"]

    def test_no_outlier_when_worst_level_is_majority(self):
        datasets = [
            {"_world_label": "w0", "simulation_result": {"risk_verdict": {"level": "high", "label": "High"}}},
            {"_world_label": "w1", "simulation_result": {"risk_verdict": {"level": "high", "label": "High"}}},
            {"_world_label": "w2", "simulation_result": {"risk_verdict": {"level": "medium", "label": "Medium"}}},
        ]
        config = {"risk_level_order": {"low": 1, "medium": 2, "high": 3}}
        result = aggregate_multi_world(datasets, config)
        assert result["worst_reasonable_level"] == "high"
        assert result["outlier_worlds"] == []


# ===================================================================
# filter_by_schema
# ===================================================================

class TestFilterBySchema:
    def test_keeps_whitelisted_keys(self):
        data = {"keep_me": 42, "drop_me": "should not appear"}
        schema = {"keep_me": {}}
        result = filter_by_schema(data, schema)
        assert "keep_me" in result
        assert "drop_me" not in result

    def test_handles_nested_dicts(self):
        data = {"outer": {"inner_keep": 1, "inner_drop": 2}}
        schema = {"outer": {"inner_keep": {}}}
        result = filter_by_schema(data, schema)
        assert result["outer"]["inner_keep"] == 1
        assert "inner_drop" not in result["outer"]

    def test_handles_empty_data(self):
        assert filter_by_schema({}, {"key": {}}) == {}

    def test_handles_none_schema(self):
        data = {"a": 1}
        assert filter_by_schema(data, None) == data


# ===================================================================
# write_appendix_b
# ===================================================================

class TestWriteAppendixB:
    def test_writes_json_file(self, tmp_workdir):
        data = {"meta": {"event_name": "测试"}}
        output_path = tmp_workdir / "appendix_b.json"
        write_appendix_b(data, str(output_path))
        assert output_path.exists()
        written = json.loads(output_path.read_text(encoding="utf-8"))
        assert written["meta"]["event_name"] == "测试"

    def test_creates_parent_directories(self, tmp_workdir):
        data = {"meta": {}}
        output_path = tmp_workdir / "deep" / "nested" / "appendix_b.json"
        write_appendix_b(data, str(output_path))
        assert output_path.exists()

    def test_raises_typeerror_for_non_dict(self, tmp_workdir):
        with pytest.raises(TypeError):
            write_appendix_b("not a dict", str(tmp_workdir / "out.json"))


# ===================================================================
# Reference contracts
# ===================================================================

class TestReferenceContracts:
    def test_schema_source_paths_match_dataset_fields(self):
        references_dir = Path(__file__).parent.parent / "references"
        schema_text = (references_dir / "appendix_b_schema.yaml").read_text(encoding="utf-8")
        dataset_text = (references_dir / "dataset_fields.yaml").read_text(encoding="utf-8")
        dataset_paths = set(re.findall(r"^\s*-\s+path:\s+([^\s]+)$", dataset_text, re.MULTILINE))

        raw_paths = re.findall(
            r"^\s+-\s+(datasets\[\]\.[^\s]+|dataset\.[^\s]+)$",
            schema_text,
            re.MULTILINE,
        )
        normalized_paths = {
            path.replace("datasets[].", "").replace("dataset.", "", 1)
            for path in raw_paths
        }

        assert "simulation_result[].simulation_result.risk_verdict.level" not in schema_text
        assert "simulation_result[].run_info.event_scale" not in schema_text
        assert normalized_paths <= dataset_paths

    def test_risk_rules_include_actual_scale_and_controversy_paths(self):
        references_dir = Path(__file__).parent.parent / "references"
        rules_text = (references_dir / "risk_rules.yaml").read_text(encoding="utf-8")
        required_paths = {
            "evolution_analysis.event_scale_avg",
            "evolution_analysis.event_scale_distribution",
            "evolution_analysis.event_controversy_avg",
            "evolution_analysis.event_controversy_distribution",
        }
        for path in required_paths:
            assert path in rules_text

    def test_no_confirmed_risks_exception_is_declared_in_schema_and_policy(self):
        references_dir = Path(__file__).parent.parent / "references"
        schema_text = (references_dir / "appendix_b_schema.yaml").read_text(encoding="utf-8")
        rules_text = (references_dir / "risk_rules.yaml").read_text(encoding="utf-8")

        assert "- path: risk_assessment.no_confirmed_risks_reason" in schema_text
        assert "allow_no_confirmed_risks_with_reason: true" in rules_text

    def test_countermeasure_pair_references_are_documented_consistently(self):
        references_dir = Path(__file__).parent.parent / "references"
        files = [
            references_dir / "appendix_b_schema.md",
            references_dir / "risk_rules.md",
            references_dir / "countermeasure_templates.yaml",
            Path(__file__).parent.parent / "SKILL.md",
        ]
        for path in files:
            text = path.read_text(encoding="utf-8")
            assert "trigger_reason_ref" in text
            assert "level_id_ref" in text

    def test_raw_internal_metric_branches_are_not_marked_allowed_in_body(self):
        schema_text = (
            Path(__file__).parent.parent / "references" / "appendix_b_schema.yaml"
        ).read_text(encoding="utf-8")

        for path in [
            "evolution_analysis.opinion_spreaders",
            "evolution_analysis.emotion_trajectory",
            "evolution_analysis.agent_stance_matrix",
            "evolution_analysis.inflection_points",
            "source_evidence.worlds",
        ]:
            block = re.search(
                rf"- path: {re.escape(path)}\n(?P<body>(?:    .+\n|      .+\n)+)",
                schema_text,
            )
            assert block is not None
            assert "allowed_in_body: false" in block.group("body")

    def test_filter_by_schema_paths_removes_undeclared_t1_keys(self):
        assert hasattr(builder, "filter_by_schema_paths")
        data = {
            "meta": {"event_name": "x", "extra": "drop"},
            "evolution_analysis": {"worlds_count": 1, "extra_metric": 99},
            "source_evidence": {"worlds": [], "extra": "drop"},
            "risk_assessment": {"risks": []},
        }
        allowed_paths = {
            "meta.event_name",
            "evolution_analysis.worlds_count",
            "source_evidence.worlds",
        }
        result = builder.filter_by_schema_paths(data, allowed_paths)
        assert result == {
            "meta": {"event_name": "x"},
            "evolution_analysis": {"worlds_count": 1},
            "source_evidence": {"worlds": []},
        }

# ===================================================================
# main (CLI entry)
# ===================================================================

class TestMain:
    def test_mode_evolution_exits_zero(self, minimal_input_json, tmp_workdir):
        output = tmp_workdir / "out.json"
        rc = main(
            mode="evolution",
            input_path=str(minimal_input_json),
            output_path=str(output),
        )
        assert rc == 0
        assert output.exists()

    def test_mode_evolution_writes_phase3_top_level_keys(self, minimal_input_json, tmp_workdir):
        output = tmp_workdir / "out.json"
        rc = main(
            mode="evolution",
            input_path=str(minimal_input_json),
            output_path=str(output),
        )
        assert rc == 0
        data = json.loads(output.read_text(encoding="utf-8"))
        assert set(data.keys()) == {"meta", "evolution_analysis", "source_evidence"}
        assert data["meta"]["generated_at"]
        assert "risk_level_distribution" in data["evolution_analysis"]
        assert "risk_type_frequency" in data["evolution_analysis"]
        assert data["source_evidence"]["worlds"][0]["risk_verdict"]["level"] == "medium"

    def test_mode_evolution_paths_are_declared_in_schema_yaml(self, minimal_input_json, tmp_workdir):
        output = tmp_workdir / "out.json"
        rc = main(
            mode="evolution",
            input_path=str(minimal_input_json),
            output_path=str(output),
        )
        assert rc == 0
        data = json.loads(output.read_text(encoding="utf-8"))
        schema_path = Path(__file__).parent.parent / "references" / "appendix_b_schema.yaml"
        schema_text = schema_path.read_text(encoding="utf-8")
        declared_paths = set(re.findall(r"^\s+- path: ([^\s]+)$", schema_text, re.MULTILINE))
        required_paths = {
            "meta.event_name",
            "meta.generated_at",
            "meta.worlds_count",
            "source_evidence.worlds",
        }
        required_paths.update(f"evolution_analysis.{key}" for key in data["evolution_analysis"].keys())
        assert required_paths <= declared_paths

    def test_mode_risk_preserves_existing_risk_sections(self, minimal_input_json, tmp_workdir):
        evolution_out = tmp_workdir / "appendix_b.json"
        risk = _valid_risk()
        appendix = {
            "meta": {"event_name": "x"},
            "evolution_analysis": {
                "event_scale_avg": 0.5,
                "event_scale_distribution": [0.4, 0.5, 0.6],
                "event_controversy_avg": 0.7,
                "event_controversy_distribution": [0.6, 0.7, 0.8],
                "risk_level_distribution": {"low": 1},
            },
            "source_evidence": {
                "worlds": [
                    {
                        "label": "w0",
                        "risk_verdict": {
                            "level": "medium",
                            "label": "中风险",
                            "signals": {
                                "negative_trend": 0.4,
                                "final_polarization": 0.55,
                            },
                        },
                    }
                ]
            },
            "risk_assessment": {
                "risks": [risk]
            },
            "countermeasures": {
                "measures": [_valid_measure(risk)]
            },
        }
        evolution_out.write_text(json.dumps(appendix, ensure_ascii=False), encoding="utf-8")
        rc = main(
            mode="risk",
            input_path=str(minimal_input_json),
            output_path=str(evolution_out),
        )
        assert rc == 0
        preserved = json.loads(evolution_out.read_text(encoding="utf-8"))
        assert preserved["risk_assessment"]["risks"] == appendix["risk_assessment"]["risks"]
        assert preserved["countermeasures"]["measures"] == appendix["countermeasures"]["measures"]

    def test_mode_risk_rejects_unknown_risk_type(self, minimal_input_json, tmp_workdir):
        appendix_path = tmp_workdir / "appendix_b.json"
        risk = _valid_risk(type_id="invented_risk")
        appendix = {
            "risk_assessment": {"risks": [risk]},
            "countermeasures": {"measures": [_valid_measure(risk)]},
        }
        appendix_path.write_text(json.dumps(appendix, ensure_ascii=False), encoding="utf-8")

        assert main(mode="risk", input_path=str(minimal_input_json), output_path=str(appendix_path)) != 0

    def test_mode_risk_rejects_mismatched_risk_label_or_domain(self, minimal_input_json, tmp_workdir):
        appendix_path = tmp_workdir / "appendix_b.json"
        risk = _valid_risk(type_label="错误标签", domain="governance_trust")
        appendix = {
            "risk_assessment": {"risks": [risk]},
            "countermeasures": {"measures": [_valid_measure(risk)]},
        }
        appendix_path.write_text(json.dumps(appendix, ensure_ascii=False), encoding="utf-8")

        assert main(mode="risk", input_path=str(minimal_input_json), output_path=str(appendix_path)) != 0

    def test_mode_risk_requires_existing_risk_sections(self, minimal_input_json, tmp_workdir):
        evolution_out = tmp_workdir / "appendix_b.json"
        appendix = {
            "meta": {"event_name": "x"},
            "evolution_analysis": {},
            "source_evidence": {"worlds": []},
        }
        evolution_out.write_text(json.dumps(appendix, ensure_ascii=False), encoding="utf-8")
        rc = main(
            mode="risk",
            input_path=str(minimal_input_json),
            output_path=str(evolution_out),
        )
        assert rc != 0

    def test_mode_risk_rejects_empty_risk_sections_without_reason(self, minimal_input_json, tmp_workdir):
        appendix_path = tmp_workdir / "appendix_b.json"
        appendix = {
            "meta": {"event_name": "x"},
            "evolution_analysis": {},
            "source_evidence": {"worlds": []},
            "risk_assessment": {"risks": []},
            "countermeasures": {"measures": []},
        }
        appendix_path.write_text(json.dumps(appendix, ensure_ascii=False), encoding="utf-8")
        rc = main(
            mode="risk",
            input_path=str(minimal_input_json),
            output_path=str(appendix_path),
        )
        assert rc != 0

    def test_mode_risk_accepts_explicit_no_confirmed_risks_reason(self, minimal_input_json, tmp_workdir):
        appendix_path = tmp_workdir / "appendix_b.json"
        appendix = {
            "meta": {"event_name": "x"},
            "evolution_analysis": {},
            "source_evidence": {"worlds": []},
            "risk_assessment": {
                "risks": [],
                "no_confirmed_risks_reason": "Evidence does not support confirmed risks.",
            },
            "countermeasures": {"measures": []},
        }
        appendix_path.write_text(json.dumps(appendix, ensure_ascii=False), encoding="utf-8")
        rc = main(
            mode="risk",
            input_path=str(minimal_input_json),
            output_path=str(appendix_path),
        )
        assert rc == 0

    def test_mode_risk_rejects_no_confirmed_reason_when_risks_exist(self, minimal_input_json, tmp_workdir):
        appendix_path = tmp_workdir / "appendix_b.json"
        risk = _valid_risk()
        appendix = {
            "risk_assessment": {
                "risks": [risk],
                "no_confirmed_risks_reason": "Evidence does not support confirmed risks.",
            },
            "countermeasures": {"measures": [_valid_measure(risk)]},
        }
        appendix_path.write_text(json.dumps(appendix, ensure_ascii=False), encoding="utf-8")

        assert main(mode="risk", input_path=str(minimal_input_json), output_path=str(appendix_path)) != 0

    def test_mode_risk_rejects_more_than_three_confirmed_risks(self, minimal_input_json, tmp_workdir):
        appendix_path = tmp_workdir / "appendix_b.json"
        risks = [
            _valid_risk(),
            _valid_risk(
                type_id="group_polarization_fragmentation_risk",
                type_label="群体极化与舆论撕裂风险",
            ),
            _valid_risk(
                type_id="secondary_spread_issue_overflow_risk",
                type_label="次生传播与议题外溢风险",
            ),
            _valid_risk(
                type_id="rumor_fact_confusion_risk",
                type_label="谣言与事实混淆风险",
            ),
        ]
        appendix = {
            "risk_assessment": {"risks": risks},
            "countermeasures": {"measures": [_valid_measure(risk) for risk in risks]},
        }
        appendix_path.write_text(json.dumps(appendix, ensure_ascii=False), encoding="utf-8")

        assert main(mode="risk", input_path=str(minimal_input_json), output_path=str(appendix_path)) != 0

    def test_mode_risk_rejects_countermeasure_label_or_reference_drift(self, minimal_input_json, tmp_workdir):
        appendix_path = tmp_workdir / "appendix_b.json"
        risk = _valid_risk()
        measure = _valid_measure(risk)
        measure["risk_label"] = "错误标签"
        measure["trigger_reason_ref"] = "错误原因"
        appendix = {
            "risk_assessment": {"risks": [risk]},
            "countermeasures": {"measures": [measure]},
        }
        appendix_path.write_text(json.dumps(appendix, ensure_ascii=False), encoding="utf-8")

        assert main(mode="risk", input_path=str(minimal_input_json), output_path=str(appendix_path)) != 0

    def test_mode_risk_rejects_missing_required_risk_fields(self, minimal_input_json, tmp_workdir):
        appendix_path = tmp_workdir / "appendix_b.json"
        appendix = {
            "meta": {"event_name": "x"},
            "evolution_analysis": {},
            "source_evidence": {"worlds": []},
            "risk_assessment": {
                "risks": [{"type_id": "r1", "type_label": "Risk 1"}],
            },
            "countermeasures": {
                "measures": [
                    {
                        "risk_type_id": "r1",
                        "risk_label": "Risk 1",
                        "responsible_body": "body",
                        "action_direction": "direction",
                        "measure": "measure",
                    }
                ]
            },
        }
        appendix_path.write_text(json.dumps(appendix, ensure_ascii=False), encoding="utf-8")
        rc = main(
            mode="risk",
            input_path=str(minimal_input_json),
            output_path=str(appendix_path),
        )
        assert rc != 0

    def test_mode_risk_rejects_missing_trigger_signals_or_reality_translation(self, minimal_input_json, tmp_workdir):
        appendix_path = tmp_workdir / "appendix_b.json"
        appendix = {
            "meta": {"event_name": "x"},
            "evolution_analysis": {},
            "source_evidence": {"worlds": []},
            "risk_assessment": {
                "risks": [
                    {
                        "type_id": "r1",
                        "type_label": "Risk 1",
                        "domain": "d1",
                        "domain_label": "Domain 1",
                        "level_id": "medium",
                        "level_label": "中风险",
                        "trigger_reason": "reason",
                    }
                ]
            },
            "countermeasures": {
                "measures": [
                    {
                        "risk_type_id": "r1",
                        "risk_label": "Risk 1",
                        "responsible_body": "body",
                        "action_direction": "direction",
                        "measure": "measure",
                    }
                ]
            },
        }
        appendix_path.write_text(json.dumps(appendix, ensure_ascii=False), encoding="utf-8")
        rc = main(
            mode="risk",
            input_path=str(minimal_input_json),
            output_path=str(appendix_path),
        )
        assert rc != 0

    def test_mode_risk_rejects_empty_trigger_signals(self, minimal_input_json, tmp_workdir):
        appendix_path = tmp_workdir / "appendix_b.json"
        appendix = {
            "meta": {"event_name": "x"},
            "evolution_analysis": {},
            "source_evidence": {"worlds": []},
            "risk_assessment": {
                "risks": [
                    {
                        "type_id": "r1",
                        "type_label": "Risk 1",
                        "domain": "d1",
                        "domain_label": "Domain 1",
                        "level_id": "medium",
                        "level_label": "中风险",
                        "trigger_signals": [],
                        "trigger_reason": "reason",
                        "reality_translation": "translation",
                    }
                ]
            },
            "countermeasures": {
                "measures": [
                    {
                        "risk_type_id": "r1",
                        "risk_label": "Risk 1",
                        "responsible_body": "body",
                        "action_direction": "direction",
                        "measure": "measure",
                    }
                ]
            },
        }
        appendix_path.write_text(json.dumps(appendix, ensure_ascii=False), encoding="utf-8")
        rc = main(
            mode="risk",
            input_path=str(minimal_input_json),
            output_path=str(appendix_path),
        )
        assert rc != 0

    def test_mode_risk_rejects_unmatched_countermeasure(self, minimal_input_json, tmp_workdir):
        appendix_path = tmp_workdir / "appendix_b.json"
        appendix = {
            "meta": {"event_name": "x"},
            "evolution_analysis": {},
            "source_evidence": {"worlds": []},
            "risk_assessment": {
                "risks": [
                    {
                        "type_id": "r1",
                        "type_label": "Risk 1",
                        "domain": "d1",
                        "domain_label": "Domain 1",
                        "level_id": "medium",
                        "level_label": "中风险",
                        "trigger_signals": ["signal"],
                        "trigger_reason": "reason",
                        "reality_translation": "translation",
                    }
                ]
            },
            "countermeasures": {
                "measures": [
                    {
                        "risk_type_id": "other",
                        "risk_label": "Other",
                        "responsible_body": "body",
                        "action_direction": "direction",
                        "measure": "measure",
                    }
                ]
            },
        }
        appendix_path.write_text(json.dumps(appendix, ensure_ascii=False), encoding="utf-8")
        rc = main(
            mode="risk",
            input_path=str(minimal_input_json),
            output_path=str(appendix_path),
        )
        assert rc != 0

    def test_invalid_mode_returns_nonzero(self, tmp_workdir):
        dummy = tmp_workdir / "dummy.json"
        dummy.write_text("{}", encoding="utf-8")
        rc = main(mode="invalid_mode", input_path=str(dummy), output_path=str(tmp_workdir / "out.json"))
        assert rc != 0

    def test_missing_input_returns_nonzero(self, tmp_workdir):
        rc = main(
            mode="evolution",
            input_path=str(tmp_workdir / "nonexistent.json"),
            output_path=str(tmp_workdir / "out.json"),
        )
        assert rc != 0

    # -- H-1: error handling for dataset failures --
    def test_evolution_missing_dataset_returns_nonzero(self, tmp_workdir):
        """main() returns non-zero when a world's simulation dataset is missing."""
        seed = tmp_workdir / "seed.txt"
        seed.write_text("test", encoding="utf-8")
        input_data = {
            "event_name": "test",
            "seed_input_path": str(seed),
            "worlds": [{"label": "w0", "simulation_dataset_path": str(tmp_workdir / "does_not_exist.json")}],
        }
        input_path = tmp_workdir / "input.json"
        input_path.write_text(json.dumps(input_data), encoding="utf-8")
        rc = main(mode="evolution", input_path=str(input_path), output_path=str(tmp_workdir / "out.json"))
        assert rc != 0

    def test_evolution_corrupt_dataset_returns_nonzero(self, tmp_workdir):
        """main() returns non-zero when a world's simulation dataset is not valid JSON."""
        seed = tmp_workdir / "seed.txt"
        seed.write_text("test", encoding="utf-8")
        bad_ds = tmp_workdir / "bad_ds.json"
        bad_ds.write_text("{{{ not json", encoding="utf-8")
        input_data = {
            "event_name": "test",
            "seed_input_path": str(seed),
            "worlds": [{"label": "w0", "simulation_dataset_path": str(bad_ds)}],
        }
        input_path = tmp_workdir / "input.json"
        input_path.write_text(json.dumps(input_data), encoding="utf-8")
        rc = main(mode="evolution", input_path=str(input_path), output_path=str(tmp_workdir / "out.json"))
        assert rc != 0

    def test_risk_missing_appendix_b_returns_nonzero(self, tmp_workdir):
        """main(mode=risk) returns non-zero when appendix_b.json doesn't exist yet."""
        seed = tmp_workdir / "seed.txt"
        seed.write_text("test", encoding="utf-8")
        input_data = {
            "event_name": "test",
            "seed_input_path": str(seed),
            "worlds": [{"label": "w0", "simulation_dataset_path": str(tmp_workdir / "missing.json")}],
        }
        input_path = tmp_workdir / "input.json"
        input_path.write_text(json.dumps(input_data), encoding="utf-8")
        rc = main(mode="risk", input_path=str(input_path), output_path=str(tmp_workdir / "no_such_appendix.json"))
        assert rc != 0

    def test_risk_corrupt_appendix_b_returns_nonzero(self, tmp_workdir):
        """main(mode=risk) returns non-zero when appendix_b.json is corrupt."""
        corrupt = tmp_workdir / "corrupt_appendix.json"
        corrupt.write_text("not json {{{", encoding="utf-8")
        seed = tmp_workdir / "seed.txt"
        seed.write_text("test", encoding="utf-8")
        input_data = {
            "event_name": "test",
            "seed_input_path": str(seed),
            "worlds": [{"label": "w0", "simulation_dataset_path": str(tmp_workdir / "missing.json")}],
        }
        input_path = tmp_workdir / "input.json"
        input_path.write_text(json.dumps(input_data), encoding="utf-8")
        rc = main(mode="risk", input_path=str(input_path), output_path=str(corrupt))
        assert rc != 0

    # -- H-2 / L-3: input validation propagated through CLI --
    def test_evolution_bad_input_schema_returns_nonzero(self, tmp_workdir):
        """main() returns non-zero when input JSON fails schema validation."""
        bad = tmp_workdir / "bad_input.json"
        bad.write_text(json.dumps({"event_name": 123}), encoding="utf-8")  # missing worlds + seed
        rc = main(mode="evolution", input_path=str(bad), output_path=str(tmp_workdir / "out.json"))
        assert rc != 0

    # -- 新增审计发现: load_risk_mapping 语义边界 --
    def test_load_risk_mapping_returns_none_for_missing_file(self, tmp_workdir):
        """load_risk_mapping() returns None when file doesn't exist, not {}."""
        result = load_risk_mapping(tmp_workdir / "does_not_exist.yaml")
        assert result is None

    def test_validate_risk_sections_skips_mapping_when_none(self):
        """validate_risk_sections() with risk_mapping=None skips mapping validation."""
        risk = _valid_risk()
        measure = _valid_measure(risk)
        appendix = {
            "risk_assessment": {"risks": [risk]},
            "countermeasures": {"measures": [measure]},
        }
        # risk_mapping=None 时应跳过映射校验，接受有效风险
        error = validate_risk_sections(
            appendix,
            risk_mapping=None,
            risk_policy={
                "min_confirmed_risks": 1,
                "max_confirmed_risks": 3,
                "allow_no_confirmed_risks_with_reason": False,
            },
            countermeasure_contract={
                "trigger_reason_ref": "trigger_reason",
                "level_id_ref": "level_id",
            },
        )
        assert error is None

    def test_validate_risk_sections_error_shows_expected_vs_actual_for_risk_label(self):
        """Error message for risk_label mismatch includes expected and actual values."""
        risk = _valid_risk(type_label="正确标签")
        measure = _valid_measure(risk)
        measure["risk_label"] = "错误标签"
        appendix = {
            "risk_assessment": {"risks": [risk]},
            "countermeasures": {"measures": [measure]},
        }
        error = validate_risk_sections(
            appendix,
            risk_mapping=None,
            risk_policy={
                "min_confirmed_risks": 1,
                "max_confirmed_risks": 3,
                "allow_no_confirmed_risks_with_reason": False,
            },
            countermeasure_contract={
                "trigger_reason_ref": "trigger_reason",
                "level_id_ref": "level_id",
            },
        )
        assert error is not None
        assert 'expected' in error.lower() or '期望' in error
        assert '正确标签' in error
        assert '错误标签' in error

    def test_validate_risk_sections_error_shows_expected_vs_actual_for_reference(self):
        """Error message for trigger_reason_ref mismatch includes expected and actual values."""
        risk = _valid_risk(trigger_reason="经核查的风险触发原因")
        measure = _valid_measure(risk)
        measure["trigger_reason_ref"] = "错误的摘要"
        appendix = {
            "risk_assessment": {"risks": [risk]},
            "countermeasures": {"measures": [measure]},
        }
        error = validate_risk_sections(
            appendix,
            risk_mapping=None,
            risk_policy={
                "min_confirmed_risks": 1,
                "max_confirmed_risks": 3,
                "allow_no_confirmed_risks_with_reason": False,
            },
            countermeasure_contract={
                "trigger_reason_ref": "trigger_reason",
                "level_id_ref": "level_id",
            },
        )
        assert error is not None
        assert 'expected' in error.lower()
        assert '经核查的风险触发原因' in error
        assert '错误的摘要' in error

    def test_validate_risk_sections_uses_defaults_when_policy_is_none(self):
        """validate_risk_sections() with risk_policy=None uses safe defaults."""
        risk = _valid_risk()
        measure = _valid_measure(risk)
        appendix = {
            "risk_assessment": {"risks": [risk]},
            "countermeasures": {"measures": [measure]},
        }
        error = validate_risk_sections(
            appendix,
            risk_mapping=None,
            risk_policy=None,
            countermeasure_contract=None,
        )
        assert error is None

    def test_validate_risk_sections_empty_mapping_does_not_false_positive(self):
        """risk_mapping=None (not {}) skips mapping enforcement; {} still enforces."""
        # {} enforces mapping, so valid type_id from _valid_risk() should be
        # rejected when the mapping is empty (no type defined).
        risk = _valid_risk()
        measure = _valid_measure(risk)
        appendix = {
            "risk_assessment": {"risks": [risk]},
            "countermeasures": {"measures": [measure]},
        }
        error = validate_risk_sections(
            appendix,
            risk_mapping={},
            risk_policy={
                "min_confirmed_risks": 1,
                "max_confirmed_risks": 3,
                "allow_no_confirmed_risks_with_reason": False,
            },
            countermeasure_contract={
                "trigger_reason_ref": "trigger_reason",
                "level_id_ref": "level_id",
            },
        )
        # 空映射中没有类型 → 应报错
        assert error is not None

    # -- L-3: boundary tests for file-missing and empty-input paths --
    def test_load_countermeasure_contract_returns_defaults_for_missing_file(self, tmp_workdir):
        """load_countermeasure_contract() returns built-in defaults when file doesn't exist."""
        result = builder.load_countermeasure_contract(tmp_workdir / "does_not_exist.yaml")
        assert result == {"trigger_reason_ref": "trigger_reason", "level_id_ref": "level_id"}

    def test_load_risk_policy_returns_defaults_for_missing_file(self, tmp_workdir):
        """load_risk_policy() returns built-in defaults when file doesn't exist."""
        result = load_risk_policy(tmp_workdir / "does_not_exist.yaml")
        assert result["min_confirmed_risks"] == 1
        assert result["max_confirmed_risks"] == 3
        assert result["allow_no_confirmed_risks_with_reason"] is False

    def test_filter_by_schema_paths_empty_allowed_returns_data_unchanged(self):
        """filter_by_schema_paths() returns data unchanged when allowed_paths is empty."""
        data = {"meta": {"event_name": "x"}, "evolution_analysis": {"worlds_count": 1}}
        result = builder.filter_by_schema_paths(data, set())
        assert result == data

    # -- M-1: keep_distribution honoured --
    def test_keep_distribution_false_skips_distribution(self):
        """When keep_distribution is false, _distribution field is omitted."""
        datasets = [
            {"run_info": {"event_scale": 0.6}},
            {"run_info": {"event_scale": 0.8}},
        ]
        config = {
            "numeric_metrics": [
                {
                    "output_prefix": "event_scale",
                    "source_path": "run_info.event_scale",
                    "keep_distribution": False,
                }
            ]
        }
        result = aggregate_multi_world(datasets, config)
        assert "event_scale_avg" in result
        assert "event_scale_distribution" not in result

    # -- M-2: hardcoded defaults match YAML --
    def test_hardcoded_defaults_match_aggregation_yaml(self):
        """Module-level defaults must stay in sync with aggregation_config.yaml."""
        references_dir = Path(__file__).parent.parent / "references"
        yaml_config = load_aggregation_config(references_dir / "aggregation_config.yaml")
        # If YAML loaded, defaults must match YAML content
        if yaml_config:
            defaults = builder._DEFAULT_NUMERIC_METRICS
            yaml_numeric = yaml_config.get("numeric_metrics", [])
            for default, yaml_entry in zip(defaults, yaml_numeric):
                assert default["output_prefix"] == yaml_entry["output_prefix"]
                assert default["source_path"] == yaml_entry["source_path"]
            defaults_freq = builder._DEFAULT_FREQUENCY_METRICS
            yaml_freq = yaml_config.get("frequency_metrics", {})
            assert set(defaults_freq.keys()) == set(yaml_freq.keys())

    # -- L-2: version field consumed --
    def test_load_aggregation_config_reads_version(self, tmp_workdir):
        """load_aggregation_config() reads the version field."""
        config_path = tmp_workdir / "agg.yaml"
        config_path.write_text("version: 2\n", encoding="utf-8")
        config = load_aggregation_config(config_path)
        assert config.get("version") == 2

    # -- M-3: unknown evolution source path warns --
    def test_unknown_evolution_source_warns(self, capsys, tmp_workdir):
        """_append_configured_evolution_sources warns stderr on unknown path."""
        datasets = [{"simulation_result": {}, "source_context": {}}]
        result: dict = {}
        builder._append_configured_evolution_sources(
            result, datasets, ["unknown.nested.field"]
        )
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "unknown.nested.field" in captured.err

    # -- H-1: evidence_layer / domain_bias / level_selection machine enforcement --
    def test_load_risk_policy_parses_evidence_layer_and_friends(self):
        """load_risk_policy() now returns evidence_layer, domain_bias, level_selection."""
        references_dir = Path(__file__).parent.parent / "references"
        policy = load_risk_policy(references_dir / "risk_rules.yaml")
        assert "evidence_layer" in policy
        assert "domain_bias" in policy
        assert "level_selection" in policy
        assert "high_pressure" in policy["evidence_layer"]
        assert "communication_evolution" in policy["domain_bias"]

    def test_evidence_validation_passes_when_domain_conditions_met(self):
        """Risk for governance_trust with high_pressure evidence passes."""
        risk = _valid_risk(
            domain="governance_trust",
            domain_label="治理信任类",
            level_id="high",
            level_label="高风险",
        )
        measure = _valid_measure(risk)
        appendix = {
            "evolution_analysis": {
                "event_scale_avg": 0.8,
                "event_scale_distribution": [0.7, 0.8, 0.9],
                "event_controversy_avg": 0.4,
                "event_controversy_distribution": [0.3, 0.4, 0.5],
                "risk_level_distribution": {"high": 1, "medium": 2},
            },
            "source_evidence": {
                "worlds": [
                    {
                        "label": "w0",
                        "risk_verdict": {
                            "level": "high",
                            "label": "高风险",
                            "signals": {"high_sensitive_prior": False},
                        },
                    }
                ]
            },
            "risk_assessment": {"risks": [risk]},
            "countermeasures": {"measures": [measure]},
        }
        references_dir = Path(__file__).parent.parent / "references"
        policy = load_risk_policy(references_dir / "risk_rules.yaml")
        error = validate_risk_sections(
            appendix,
            risk_mapping=None,
            risk_policy=policy,
            countermeasure_contract={
                "trigger_reason_ref": "trigger_reason",
                "level_id_ref": "level_id",
            },
        )
        # event_scale_avg=0.8 >= 0.75 → high_pressure satisfied
        # governance_trust needs [high_pressure] → condition met
        assert error is None

    def test_evidence_validation_fails_when_domain_conditions_unmet(self):
        """Risk without satisfying its domain's evidence conditions is rejected."""
        risk = _valid_risk(
            domain="governance_trust",
            domain_label="治理信任类",
            level_id="low",
            level_label="低风险",
        )
        measure = _valid_measure(risk)
        measure["level_id_ref"] = "low"
        appendix = {
            "evolution_analysis": {
                "event_scale_avg": 0.3,
                "event_scale_distribution": [0.2, 0.3, 0.4],
                "event_controversy_avg": 0.2,
                "event_controversy_distribution": [0.1, 0.2],
                "risk_level_distribution": {"low": 3},
            },
            "source_evidence": {
                "worlds": [
                    {
                        "label": "w0",
                        "risk_verdict": {
                            "level": "low",
                            "label": "低风险",
                            "signals": {"high_sensitive_prior": False},
                        },
                    }
                ]
            },
            "risk_assessment": {"risks": [risk]},
            "countermeasures": {"measures": [measure]},
        }
        references_dir = Path(__file__).parent.parent / "references"
        policy = load_risk_policy(references_dir / "risk_rules.yaml")
        error = validate_risk_sections(
            appendix,
            risk_mapping=None,
            risk_policy=policy,
            countermeasure_contract={
                "trigger_reason_ref": "trigger_reason",
                "level_id_ref": "level_id",
            },
        )
        # event_scale_avg=0.3 < 0.75, risk_level_distribution has no "high",
        # signals.high_sensitive_prior is False → high_pressure unmet
        # governance_trust needs [high_pressure] → rejected
        assert error is not None
        assert "evidence" in error.lower()

    def test_level_selection_enforces_upstream_level_consistency(self):
        """When prefer_upstream_level is true, risk level_id must match a world's level."""
        risk = _valid_risk(
            domain="governance_trust",
            domain_label="治理信任类",
            level_id="critical",
            level_label="极高风险",
        )
        measure = _valid_measure(risk)
        measure["level_id_ref"] = "critical"
        appendix = {
            "evolution_analysis": {
                "event_scale_avg": 0.8,
                "event_scale_distribution": [0.7, 0.8, 0.9],
                "event_controversy_avg": 0.4,
                "event_controversy_distribution": [0.3, 0.4],
                "risk_level_distribution": {"medium": 2, "high": 1},
            },
            "source_evidence": {
                "worlds": [
                    {
                        "label": "w0",
                        "risk_verdict": {
                            "level": "high",
                            "label": "高风险",
                            "signals": {"high_sensitive_prior": False},
                        },
                    }
                ]
            },
            "risk_assessment": {"risks": [risk]},
            "countermeasures": {"measures": [measure]},
        }
        references_dir = Path(__file__).parent.parent / "references"
        policy = load_risk_policy(references_dir / "risk_rules.yaml")
        error = validate_risk_sections(
            appendix,
            risk_mapping=None,
            risk_policy=policy,
            countermeasure_contract={
                "trigger_reason_ref": "trigger_reason",
                "level_id_ref": "level_id",
            },
        )
        # level_id is "critical" but upstream levels are ["high", "medium"] → mismatch
        assert error is not None
        assert "level" in error.lower()
