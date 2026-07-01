#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simulation_dataset 字段契约不变量测试。

测试目标：验证 pipeline 输出的 simulation_dataset.json 满足所有下游消费端的
字段契约。不测具体数值（event_scale=0.8 还是 0.6），只测结构完整性和字段间
一致性（invariants）。

不变量清单：
  1. 顶层三段结构（run_info / source_context / simulation_result）必须存在
  2. run_info 数值在合法边界内
  3. risk_verdict 的 level↔label 映射一致
  4. risk_type_classification 的类型/标签/域映射不断链
  5. opinion_spreaders 百分比和 ≈ 100%
  6. 模拟序列（x_t_sequence / emotion_trajectory）长度与 total_ticks 一致
  7. source_context 实体字段完整性
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#
# ── 测试夹具 ──
#

DATASET_CACHE = None


def dataset() -> dict[str, Any]:
    """读取缓存的 simulation_dataset.json 作为测试数据。"""
    global DATASET_CACHE
    if DATASET_CACHE is not None:
        return DATASET_CACHE

    # 使用最近一次成功的 test8 运行输出
    path = Path("outputs/runs/2026-06-07/test8_171149/run_629691_90957/simulation_dataset.json")
    if not path.exists():
        raise FileNotFoundError(
            f"测试需要真实的 simulation_dataset.json: {path}\n"
            "请先跑一次 pipeline 生成数据，或者手动指定一个可用路径。"
        )
    with path.open(encoding="utf-8") as f:
        DATASET_CACHE = json.load(f)
    return DATASET_CACHE


#
# ── 不变量：顶层结构 ──
#


def test_top_level_structure():
    """simulation_dataset 必须有 run_info / source_context / simulation_result 三段。"""
    d = dataset()
    for section in ("run_info", "source_context", "simulation_result"):
        assert section in d, f"缺少顶级字段: {section}"
        assert isinstance(d[section], dict), f"{section} 必须是 dict"


def test_schema_version():
    """_schema_version 必须存在且标记为 v2。"""
    d = dataset()
    assert d.get("_schema_version") == "v2", "缺 _schema_version 或不是 v2"


#
# ── 不变量：run_info 数值边界 ──
#


def test_run_info_scale_and_controversy_in_range():
    """event_scale / event_controversy 在 [0, 1] 范围内。"""
    info = dataset()["run_info"]
    scale = info.get("event_scale", -1)
    controversy = info.get("event_controversy", -1)
    assert 0.0 <= scale <= 1.0, f"event_scale 超出 [0,1]: {scale}"
    assert 0.0 <= controversy <= 1.0, f"event_controversy 超出 [0,1]: {controversy}"


def test_run_info_has_required_fields():
    """run_info 必须包含所有下游需要的字段。"""
    info = dataset()["run_info"]
    for field in ("event_name", "event_type", "total_ticks"):
        assert field in info, f"run_info 缺少字段: {field}"
    assert isinstance(info["total_ticks"], int), "total_ticks 必须是 int"
    assert info["total_ticks"] >= 0, "total_ticks 必须 >= 0"


def test_run_info_seed_text_if_present():
    """seed_text 如果存在则必须有内容（新版本 parser 写入，旧版本可能缺失）。"""
    seed = dataset()["run_info"].get("seed_text")
    if seed is not None:
        assert isinstance(seed, str) and len(seed) > 0, "seed_text 不为空"


#
# ── 不变量：risk_verdict 标签一致性 ──
#


def test_risk_verdict_level_label_consistency():
    """risk_verdict.level 和 label 必须 1:1 对应。"""
    verdict = dataset()["simulation_result"]["risk_verdict"]
    level = verdict["level"]
    label = verdict["label"]
    LABEL_MAP = {
        "low": "低风险",
        "medium": "中风险",
        "high": "高风险",
        "critical": "重大风险",
    }
    assert level in LABEL_MAP, f"未知风险等级: {level}"
    assert label == LABEL_MAP[level], (
        f"{level} 的标签应为 {LABEL_MAP[level]}，实际为 {label}"
    )


def test_risk_verdict_has_signals():
    """risk_verdict 必须有 basis_text 和 signals。"""
    verdict = dataset()["simulation_result"]["risk_verdict"]
    assert "basis_text" in verdict, "risk_verdict 缺 basis_text"
    assert isinstance(verdict.get("signals"), dict), "signals 必须是 dict"
    assert verdict["signals"], "signals 不能为空"


#
# ── 不变量：risk_type_classification 类型↔标签↔域 一致性 ──
#


def test_risk_type_labels_match_types():
    """primary_types 和 type_labels 必须一一对应且通过 RISK_TYPE_LABELS 校验。"""
    from adarian.schemas.risk import RISK_TYPE_LABELS

    rtc = dataset()["simulation_result"].get("risk_type_classification", {})
    types = rtc.get("primary_types", [])
    labels = rtc.get("type_labels", [])
    assert len(types) == len(labels), f"类型({len(types)})和标签({len(labels)})数量不一致"
    for t, l in zip(types, labels):
        expected = RISK_TYPE_LABELS.get(t)
        assert expected is not None, f"未知风险类型: {t}"
        assert l == expected, f"{t} 的标签应为 {expected}，实际为 {l}"


def test_risk_type_domain_mapping_consistency():
    """primary_types[0] 的 primary_domain 必须匹配 TYPE_TO_DOMAIN_MAP。"""
    from adarian.schemas.risk import DOMAIN_LABELS, TYPE_TO_DOMAIN_MAP

    rtc = dataset()["simulation_result"].get("risk_type_classification", {})
    types = rtc.get("primary_types", [])
    if not types:
        return  # 空类型列表不做域校验

    # 向后兼容：旧 dataset 可能没有 primary_domain
    domain = rtc.get("primary_domain")
    domain_label = rtc.get("primary_domain_label")
    if not domain:
        return  # 旧 dataset 不强制校验

    expected_domain = TYPE_TO_DOMAIN_MAP.get(types[0], "")
    assert domain == expected_domain, (
        f"{types[0]} 的域应为 {expected_domain}，实际为 {domain}"
    )
    expected_label = DOMAIN_LABELS.get(domain, "")
    if domain_label:
        assert domain_label == expected_label, (
            f"域 {domain} 的标签应为 {expected_label}，实际为 {domain_label}"
        )


#
# ── 不变量：opinion_spreaders 百分比和 ──
#


def test_opinion_spreader_percentage_sum():
    """opinion_spreaders 的 estimated_percentage 总和 ≈ 100%。"""
    spreaders = dataset()["source_context"].get("opinion_spreaders", [])
    assert len(spreaders) > 0, "opinion_spreaders 不能为空"
    total = sum(s.get("estimated_percentage", 0) for s in spreaders)
    assert 99.0 <= total <= 101.0, (
        f"百分比和应为 100%，实际为 {total}"
    )


#
# ── 不变量：序列长度一致性 ──
#


def test_x_t_sequence_length():
    """x_t_sequence 长度必须等于 total_ticks。"""
    d = dataset()
    ticks = d["run_info"]["total_ticks"]
    seq = d["simulation_result"].get("x_t_sequence", [])
    assert len(seq) == ticks, (
        f"x_t_sequence 长度应为 {ticks}，实际为 {len(seq)}"
    )


def test_emotion_trajectory_length():
    """emotion_trajectory 长度必须等于 total_ticks。"""
    d = dataset()
    ticks = d["run_info"]["total_ticks"]
    traj = d["simulation_result"].get("emotion_trajectory", [])
    assert len(traj) == ticks, (
        f"emotion_trajectory 长度应为 {ticks}，实际为 {len(traj)}"
    )


def test_final_x_matches_sequence_end():
    """final_x 必须等于 x_t_sequence 的最后一个值。"""
    sr = dataset()["simulation_result"]
    seq = sr.get("x_t_sequence", [])
    final_x = sr.get("final_x")
    if seq and final_x is not None:
        assert abs(final_x - seq[-1]) < 0.001, (
            f"final_x ({final_x}) 不等于 x_t_sequence[-1] ({seq[-1]})"
        )


#
# ── 不变量：source_context 实体字段完整性 ──
#


def test_event_entities_have_required_fields():
    """每个 event_entity 必须有 name / type / role。"""
    entities = dataset()["source_context"].get("event_entities", [])
    assert len(entities) > 0, "event_entities 不能为空"
    for entity in entities:
        for field in ("name", "type", "role"):
            assert field in entity, f"event_entity 缺少字段: {field}"


def test_opinion_spreaders_have_required_fields():
    """每个 opinion_spreader 必须有 group_name / stance_score / estimated_percentage。"""
    spreaders = dataset()["source_context"].get("opinion_spreaders", [])
    assert len(spreaders) > 0, "opinion_spreaders 不能为空"
    for s in spreaders:
        for field in ("group_name", "stance_score", "estimated_percentage"):
            assert field in s, f"opinion_spreader 缺少字段: {field}"


#
# ── 不变量：source_artifact_refs ──
#


def test_source_artifact_refs_exist():
    """source_artifact_refs 必须存在（供 whitebox/diagnostic 使用）。"""
    refs = dataset().get("source_artifact_refs", {})
    for key in ("tick_logs", "entities_and_relations", "social_graph"):
        assert key in refs, f"source_artifact_refs 缺少字段: {key}"
