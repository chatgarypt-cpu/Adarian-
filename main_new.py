"""
Adarian 新路径 — 消费 Phase3 模块的 Phase 1-4 流水线。
---
与 main.py 的区别：
  Phase 3 tick simulation 后增加 Parser Aggregation 层
  Phase 4 消费 Phase3 parser 输出，不调 report_agent 内联函数

用法：
    python main_new.py [seed_file]

参数：
    seed_file: 种子文本文件路径，默认使用 seeds/example_event.txt
"""

import sys
import time
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

import config
from config import ensure_dirs
from src.llm_client import init_llm_client, get_llm_client
from src.schemas import EntityExtractionOutput, Phase2Output, Phase4Output, TickLog
from src.utils.runtime_logger import get_runtime_logger

console = Console()


def print_banner():
    """打印横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║           Adarian 新路径 — Phase3 模块化流水线              ║
║                         MVP v2.0                           ║
╚══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def run_phase1(seed_file: str, output_path: Path = None):
    """执行 Phase 1：实体提取与分类（Analyzer/Generator/Validator 协作）"""
    from src.phase1 import extract_entities_from_file, save_entities_output

    console.print(Panel("[bold]Phase 1: 实体提取与分类（Analyzer/Generator/Validator 协作）[/bold]", border_style="cyan"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Analyzer/Generator/Validator 协作提取实体...", total=1)
        extraction_output = extract_entities_from_file(seed_file)
        progress.update(task, completed=1)

    entities_file = save_entities_output(extraction_output, output_path=output_path)

    console.print(f"  事件实体数量: {len(extraction_output.event_entities)}")
    console.print(f"  意见传播者数量: {len(extraction_output.opinion_spreaders)}")
    console.print(f"  事件类型: {extraction_output.event_type}")
    console.print(f"  事件规模: {extraction_output.event_scale:.2f}")
    console.print(f"  事件争议性: {extraction_output.event_controversy:.2f}\n")

    return extraction_output, entities_file


def run_phase2(
    extraction_output: EntityExtractionOutput,
    output_path: Optional[Path] = None,
) -> Phase2Output:
    """执行 Phase 2：社交拓扑构建"""
    from src.phase2 import (
        build_topology_from_extraction,
        validate_topology,
        save_social_graph,
    )

    console.print(Panel("[bold]Phase 2: 社交拓扑构建[/bold]", border_style="cyan"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]构建拓扑...", total=1)
        phase2_output = build_topology_from_extraction(extraction_output)
        progress.update(task, completed=1)

    validate_topology(phase2_output)
    save_social_graph(phase2_output, output_path=output_path)

    event_entity_count = sum(1 for n in phase2_output.nodes if n.entity_category == "event_entity")
    spreader_count = sum(1 for n in phase2_output.nodes if n.entity_category == "opinion_spreader")
    edge_count = len(phase2_output.edges)

    console.print(f"  事件实体（Core）: {event_entity_count}")
    console.print(f"  意见传播者（Periphery）: {spreader_count}")
    console.print(f"  总边数: {edge_count}\n")

    return phase2_output


def run_phase3(
    extraction_output: EntityExtractionOutput,
    phase2_output: Phase2Output,
    seed_text: str,
    output_path: Optional[Path] = None,
) -> Tuple[List[TickLog], List[float]]:
    """执行 Phase 3：多轮涌现推演"""
    from src.phase3 import (
        SimulationEngine, save_tick_logs, print_simulation_summary,
    )

    console.print(Panel("[bold]Phase 3: 多轮涌现推演[/bold]", border_style="cyan"))

    engine = SimulationEngine(extraction_output, phase2_output, seed_text)
    tick_logs = engine.run_simulation(max_ticks=config.MAX_TICKS)
    save_tick_logs(tick_logs, output_path=output_path)
    print_simulation_summary(tick_logs)

    x_t_sequence = engine.get_x_t_sequence()
    console.print(f"\n  x(t) 序列: {' -> '.join([f'{x:.2f}' for x in x_t_sequence])}\n")

    return tick_logs, x_t_sequence


# ── Phase 3 Parser（新路径新增）────────────────────────────────

def run_phase3_parser(
    extraction_output: EntityExtractionOutput,
    phase2_output: Phase2Output,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
) -> dict:
    """
    执行 Phase 3 Parser Aggregation — 消费所有 Phase3 模块。

    调用 SimulationDatasetParser.parse()，其内部实例化：
      - risk_analyzer.py       → 受众模式 / 风险判定 / 信号 / 风险类型
      - inflection_detector.py → 拐点检测
      - stance_analyzer.py     → 立场矩阵
    """
    from src.phase3.parser import SimulationDatasetParser

    console.print(Panel("[bold]Phase 3 Parser: 聚合分析（消费所有 Phase3 模块）[/bold]", border_style="cyan"))

    parser = SimulationDatasetParser()
    dataset = parser.parse(
        extraction_output,
        phase2_output,
        tick_logs,
        x_t_sequence,
    )

    rv = dataset["simulation_result"]["risk_verdict"]
    rt = dataset["simulation_result"]["risk_type_classification"]
    console.print(f"  风险等级: {rv['level']} ({rv['label']})")
    console.print(f"  风险类型: {rt['primary_types']}")
    console.print(f"  拐点数量: {len(dataset['simulation_result']['inflection_points'])}")
    console.print(f"  极化指数: {dataset['simulation_result']['final_polarization_index']:.4f}\n")

    return dataset


# ── Phase 4（新路径 — 消费 Phase3 parser 输出）─────────────

def _build_report_context_new(
    extraction_output, tick_logs, x_t_sequence, phase2_output, dataset,
) -> str:
    """构建 LLM 报告上下文，使用 Phase3 parser 数据替代内联函数。"""
    sim = dataset["simulation_result"]
    rv = sim.get("risk_verdict", {})
    rt = sim.get("risk_type_classification", {})
    matrix = sim.get("agent_stance_matrix", [])
    inflection_points = sim.get("inflection_points", [])
    emotion_trajectory = sim.get("emotion_trajectory", [])

    lines = []

    # 1. 事件概要
    lines.append("【事件概要】")
    lines.append(f"事件摘要：{extraction_output.event_summary}")
    lines.append(f"事件类型：{extraction_output.event_type}")

    # 2. 实体图谱
    lines.append("\n【实体图谱】")
    lines.append(f"事件实体：{len(extraction_output.event_entities)} 个")
    for entity in extraction_output.event_entities:
        lines.append(f"  - {entity.name}（{entity.type}）: {entity.role} | can_speak={entity.can_speak}")
        if entity.original_statement:
            lines.append(f"    原始发言：{entity.original_statement[:50]}...")
    lines.append(f"\n意见传播者：{len(extraction_output.opinion_spreaders)} 个")
    for s in extraction_output.opinion_spreaders:
        lines.append(f"  - {s.group_name} | 关联实体：{s.related_event_entity}，立场：{s.stance_score}，占比：{s.estimated_percentage}%")

    # 3. 轮次 0 发言
    lines.append("\n【轮次 0 事件实体发言】")
    if tick_logs:
        for entry in tick_logs[0].entries:
            if entry.comment:
                lines.append(f"  [{entry.group_name}]: {entry.comment[:80]}...")

    # 4. 模拟立场演化（从 Phase3 parser 输出的 emotion_trajectory）
    lines.append("\n【模拟立场演化数据】")
    lines.append("轮次 | 模拟立场均值 | 标准差 | 模拟极化指数 | 关键变化")
    lines.append("-" * 70)
    prev_pol = None
    for et in emotion_trajectory:
        key_event = et.get("key_event", "")
        lines.append(f"| {et['tick']} | {et['mean_stance']:.2f} | {et['std_stance']:.2f} | {et['polarization_index']:.2f} | {key_event} |")
        prev_pol = et.get("polarization_index")

    # 5. 立场矩阵（从 Phase3 parser 输出）
    lines.append("\n【立场矩阵】")
    if not matrix:
        lines.append("无可用 opinion spreader 立场矩阵。")
    else:
        lines.append("以下表格是 Markdown 报告中最终立场变化的唯一数值来源；不得重算。")
        lines.append("| Agent | 群体 | 起始立场 | 结束立场 | Delta |")
        lines.append("|---|---:|---:|---:|---:|")
        for row in matrix:
            lines.append(f"| #{row['agent_id']} | {row['group_name']} | {row['initial_stance']:.2f} | {row['final_stance']:.2f} | {row.get('max_delta', row['final_stance'] - row['initial_stance']):+.2f} |")

    # 6. 拐点（从 Phase3 parser 输出）
    lines.append("\n【模拟关键变化点】")
    if not inflection_points:
        lines.append("本轮模拟未发现显著模拟关键变化点。")
        lines.append("Markdown 报告不得声称存在模拟关键变化点，不得使用其他阈值自行识别模拟关键变化点。")
    else:
        lines.append("以下表格是 Markdown 报告中模拟关键变化点的唯一来源；不得新增其他模拟关键变化点。")
        lines.append("| 轮次 | Agent | 群体 | 影响 |")
        lines.append("|---:|---:|---|---|")
        for p in inflection_points:
            lines.append(f"| {p.get('tick', '')} | {p.get('agent_id', '')} | {p.get('group_name', '')} | {p.get('description', '')} |")

    # 7. 风险判定（从 Phase3 parser 输出的 risk_verdict）
    lines.append("\n【风险判定】（由 Phase3 RiskAnalyzer 计算）")
    lines.append(f"风险等级: {rv.get('level', 'unknown')}")
    lines.append(f"风险标签: {rv.get('label', '')}")
    lines.append(f"风险依据: {rv.get('basis_text', '')}")

    # 8. 最终风险类型
    if rt:
        lines.append("\n【风险类型分类】")
        for t, l in zip(rt.get("primary_types", []), rt.get("type_labels", [])):
            lines.append(f"  - {l}（{t}）")

    # 9. x(t) 序列
    lines.append(f"\n【x(t) 序列】{' → '.join(f'{x:.2f}' for x in x_t_sequence)}")
    if x_t_sequence:
        lines.append(f"起始 x(0): {x_t_sequence[0]:.2f} → 最终 x(t): {x_t_sequence[-1]:.2f}")

    # 10. 信号详情
    signals = rv.get("signals", {})
    if signals:
        lines.append("\n【风险信号详情】")
        for k, v in signals.items():
            lines.append(f"  {k}: {v}")

    return "\n".join(lines)


def run_phase4(
    extraction_output: EntityExtractionOutput,
    phase2_output: Phase2Output,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    dataset: dict,
    json_output_path: Optional[Path] = None,
    markdown_output_path: Optional[Path] = None,
) -> Phase4Output:
    """
    执行 Phase 4：宏观洞察生成（Phase3 驱动版）

    消费 Phase3 parser 输出的 risk_verdict / inflection_points / agent_stance_matrix，
    不调 report_agent 内联函数。
    """
    from src.phase4.report_narrative import generate_report_with_llm_narrative
    from src.phase4.report_agent import (
        _build_code_owned_report_contract_block,
        parse_llm_report_response,
        save_report,
        save_markdown_report,
    )

    console.print(Panel("[bold]Phase 4: 宏观洞察生成（Phase3 驱动）[/bold]", border_style="cyan"))

    report_context = _build_report_context_new(
        extraction_output, tick_logs, x_t_sequence, phase2_output, dataset,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]生成报告...", total=1)
        phase4_output, markdown = generate_report_with_llm_narrative(
            extraction_output,
            tick_logs,
            x_t_sequence,
            phase2_output=phase2_output,
            build_report_context=lambda *a, **kw: report_context,
            build_code_owned_contract_block=_build_code_owned_report_contract_block,
            parse_llm_report_response=parse_llm_report_response,
            get_llm_client_func=get_llm_client,
            simulation_dataset=dataset,
        )
        progress.update(task, completed=1)

    save_report(phase4_output, output_path=json_output_path)
    save_markdown_report(
        phase4_output,
        extraction_output,
        output_path=markdown_output_path,
        markdown=markdown,
    )

    return phase4_output


def _run_bypass_comparison(
    extraction_output, phase2_output, tick_logs, x_t_sequence, dataset,
) -> dict:
    """用同一组数据调旧路径 report_agent 内联函数，与 Phase3 模块输出逐维度对比。"""
    from src.phase4.report_agent import (
        assess_risk as old_assess_risk,
        determine_audience_mode as old_determine_audience,
        identify_inflection_points as old_identify_inflection,
        select_primary_risk_types as old_select_risk_types,
    )
    from src.schemas import RISK_TYPE_LABELS

    old_am = old_determine_audience(extraction_output)
    old_rl, old_basis = old_assess_risk(x_t_sequence, tick_logs, extraction_output=extraction_output)
    old_rt = old_select_risk_types(old_am, old_basis, tick_logs)
    old_ip = old_identify_inflection(tick_logs, phase2_output)
    old_rlv = old_rl.value if hasattr(old_rl, 'value') else str(old_rl)
    old_am_str = old_am.value if hasattr(old_am, 'value') else str(old_am)

    sim = dataset["simulation_result"]
    new_rlv = sim["risk_verdict"]["level"]
    new_rt = list(sim["risk_type_classification"]["primary_types"])
    new_ipc = len(sim["inflection_points"])
    new_am = dataset.get("run_info", {}).get("audience_mode", "")

    dims = [
        ("risk_level",         old_rlv,            new_rlv,          old_rlv == new_rlv),
        ("audience_mode",      old_am_str,          new_am,           old_am_str == new_am),
        ("inflection_count",   str(len(old_ip)),    str(new_ipc),     len(old_ip) == new_ipc),
        ("risk_types",         str(sorted(old_rt)), str(sorted(new_rt)), sorted(old_rt) == sorted(new_rt)),
    ]

    lines = ["[Bypass 对比] 旧路径 (report_agent) vs 新路径 (Phase3 模块)", "-" * 50]
    all_pass = True
    for name, old_v, new_v, match in dims:
        icon = "✅" if match else "❌"
        if not match:
            all_pass = False
        lines.append(f"  {icon} {name}: 旧={old_v}  新={new_v}")
    lines.append(f"\n  结论: {'✅ 全部通过 — 新旧语义等价' if all_pass else '❌ 存在不一致'}")

    result = "\n".join(lines)
    console.print(Panel(result, border_style="green" if all_pass else "red"))

    return {
        "all_match": all_pass,
        "dimensions": [
            {"name": name, "old": old_v, "new": new_v, "match": match}
            for name, old_v, new_v, match in dims
        ],
    }


# ── 以下与 main.py 完全相同 ──────────────────────────────────

def build_run_paths(seed_file: Path) -> dict:
    """Create the run directory and return all authoritative output paths."""
    now = datetime.now()
    batch_id = f"{seed_file.stem}_{now.strftime('%Y%m%d_%H%M%S')}"
    run_id = f"run_{now.strftime('%f')}_{os.getpid()}"
    batch_dir = config.OUTPUTS_DIR / "runs" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    run_dir = batch_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    whitebox_dir = run_dir / "whitebox"
    whitebox_dir.mkdir(parents=True, exist_ok=True)

    seed_copy = run_dir / "seed_input.txt"
    shutil.copyfile(seed_file, seed_copy)

    outputs = {
        "entities": run_dir / "entities_and_relations.json",
        "social_graph": run_dir / "social_graph.json",
        "tick_logs": run_dir / "tick_logs.json",
        "simulation_dataset": run_dir / "simulation_dataset.json",
        "bypass_result": run_dir / "bypass_comparison.json",
        "final_report_json": run_dir / "final_report.json",
        "final_report_md": run_dir / "final_report.md",
        "whitebox_summary": run_dir / "whitebox_summary.json",
        "whitebox_dir": whitebox_dir,
        "run_log": run_dir / "run.log",
        "timing_summary": run_dir / "timing_summary.json",
        "run_meta": run_dir / "run_meta.json",
    }

    return {
        "batch_id": batch_id,
        "batch_dir": batch_dir,
        "run_id": run_id,
        "run_dir": run_dir,
        "seed_copy": seed_copy,
        "outputs": outputs,
    }


def write_run_meta(run_context: dict, seed_file: Path, status: str, started_at: str, **extra) -> None:
    outputs = run_context["outputs"]
    payload = {
        "batch_id": run_context.get("batch_id"),
        "batch_dir": str(run_context.get("batch_dir")) if run_context.get("batch_dir") else None,
        "run_id": run_context["run_id"],
        "seed_file": str(seed_file),
        "seed_copy": str(run_context["seed_copy"]),
        "run_dir": str(run_context["run_dir"]),
        "started_at": started_at,
        "provider": config.LLM_PROVIDER,
        "model": config.get_model_name(),
        "status": status,
        "outputs": {key: str(path) for key, path in outputs.items()},
    }
    payload.update(extra)
    with open(outputs["run_meta"], "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_whitebox_summary(
    run_context: dict,
    report_completeness: dict,
    artifact_check: dict,
) -> dict:
    outputs = run_context["outputs"]
    checks = {
        "report_completeness": {
            "status": report_completeness["status"],
            "path": report_completeness["path"],
        },
        "artifact_check": {
            "status": artifact_check["status"],
            "path": artifact_check["path"],
        },
    }
    if artifact_check["status"] != "pass":
        status = "fail"
    elif report_completeness["status"] != "pass":
        status = "pass_with_warnings"
    else:
        status = "pass"
    payload = {
        "whitebox_version": "v2.0",
        "status": status,
        "checks": checks,
        "raw_sources": artifact_check["raw_sources"],
    }
    with open(outputs["whitebox_summary"], "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def write_whitebox_artifacts(run_context: dict) -> dict:
    from src.whitebox import check_run_artifacts, write_artifact_check, write_report_completeness_summary
    run_dir = run_context["run_dir"]
    outputs = run_context["outputs"]
    report_completeness = write_report_completeness_summary(run_dir, outputs["final_report_md"])
    artifact_check = check_run_artifacts(run_dir)
    summary = write_whitebox_summary(run_context, report_completeness, artifact_check)
    artifact_check = write_artifact_check(run_dir)
    summary = write_whitebox_summary(run_context, report_completeness, artifact_check)
    return {
        "report_completeness": report_completeness,
        "artifact_check": artifact_check,
        "summary": summary,
    }


def main():
    """主函数"""
    print_banner()

    ensure_dirs()
    if not config.LLM_API_KEY:
        console.print("[bold red]错误：[/bold red] 未配置 LLM API Key")
        console.print("请创建 .env 文件或设置环境变量 LLM_API_KEY")
        sys.exit(1)

    init_llm_client()
    console.print(f"[green]OK[/green] LLM: {config.LLM_PROVIDER} / {config.get_model_name()}\n")

    if len(sys.argv) > 1:
        seed_file = Path(sys.argv[1])
    else:
        seed_file = config.SEEDS_DIR / "example_event.txt"

    if not seed_file.exists():
        console.print(f"[bold red]错误：[/bold red] 种子文件不存在: {seed_file}")
        sys.exit(1)

    seed_file = seed_file.resolve()
    run_context = build_run_paths(seed_file)
    run_dir = run_context["run_dir"]
    outputs = run_context["outputs"]
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_run_meta(run_context, seed_file, status="running", started_at=started_at)

    logger = get_runtime_logger()
    logger.configure(run_dir)
    logger.log_run_start("normal", str(seed_file), str(run_dir))

    console.print(f"种子文件: {seed_file.name}\n")
    console.print(f"运行目录: {run_dir}\n")

    with open(seed_file, "r", encoding="utf-8") as f:
        seed_text = f.read()

    start_time = time.time()

    try:
        # Phase 1
        logger.log_phase_start("phase1_entity_extraction")
        phase1_start = time.time()
        extraction_output, entities_file = run_phase1(str(seed_file), output_path=outputs["entities"])
        phase1_time = time.time() - phase1_start
        logger.log_phase_end("phase1_entity_extraction", phase1_time)

        # Phase 2
        logger.log_phase_start("phase2_topology_builder")
        phase2_start = time.time()
        phase2_output = run_phase2(extraction_output, output_path=outputs["social_graph"])
        phase2_time = time.time() - phase2_start
        logger.log_phase_end("phase2_topology_builder", phase2_time)

        # Phase 3 tick simulation
        logger.log_phase_start("phase3_tick_simulation")
        phase3_start = time.time()
        tick_logs, x_t_sequence = run_phase3(
            extraction_output,
            phase2_output,
            seed_text,
            output_path=outputs["tick_logs"],
        )
        phase3_time = time.time() - phase3_start
        logger.log_phase_end("phase3_tick_simulation", phase3_time)

        # Phase 3 Parser Aggregation（新路径核心）
        logger.log_phase_start("phase3_parser_aggregation")
        phase3p_start = time.time()
        dataset = run_phase3_parser(
            extraction_output, phase2_output, tick_logs, x_t_sequence,
        )
        # 保存 simulation_dataset
        with open(outputs["simulation_dataset"], "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        phase3p_time = time.time() - phase3p_start
        logger.log_phase_end("phase3_parser_aggregation", phase3p_time)

        # Bypass 对比
        logger.log_phase_start("bypass_comparison")
        bypass_result = _run_bypass_comparison(
            extraction_output, phase2_output, tick_logs, x_t_sequence, dataset,
        )
        with open(outputs["bypass_result"], "w", encoding="utf-8") as f:
            json.dump(bypass_result, f, ensure_ascii=False, indent=2)
        logger.log_phase_end("bypass_comparison", 0)

        # Phase 4（消费 Phase3 输出）
        logger.log_phase_start("phase4_report_agent")
        phase4_start = time.time()
        phase4_output = run_phase4(
            extraction_output,
            phase2_output,
            tick_logs,
            x_t_sequence,
            dataset,
            json_output_path=outputs["final_report_json"],
            markdown_output_path=outputs["final_report_md"],
        )
        phase4_time = time.time() - phase4_start
        logger.log_phase_end("phase4_report_agent", phase4_time)

        # 总耗时
        total_time = time.time() - start_time
        logger.log_run_end("success", total_time)
        write_run_meta(
            run_context,
            seed_file,
            status="success",
            started_at=started_at,
            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            elapsed_seconds=round(total_time, 2),
            x_t_sequence=x_t_sequence,
            final_polarization_index=tick_logs[-1].global_metrics.polarization_index,
            risk_level=phase4_output.risk_level.value,
            bypass_all_match=bypass_result["all_match"],
        )
        whitebox_artifacts = write_whitebox_artifacts(run_context)
        report_completeness = whitebox_artifacts["report_completeness"]["result"]

        console.print("\n" + "=" * 60)
        console.print("[bold green]舆情预判完成！（新路径）[/bold green]")
        console.print("=" * 60)

        console.print(f"""
[bold]执行时间：[/bold]
  Phase 1 (实体提取): {phase1_time:.1f}s
  Phase 2 (拓扑构建): {phase2_time:.1f}s
  Phase 3 (模拟推演): {phase3_time:.1f}s
  Phase 3 Parser: {phase3p_time:.1f}s
  Phase 4 (报告生成): {phase4_time:.1f}s
  总计: {total_time:.1f}s

[bold]舆情指标：[/bold]
  x(t) 序列: {' -> '.join([f'{x:.2f}' for x in x_t_sequence])}
  最终极化指数: {tick_logs[-1].global_metrics.polarization_index:.2f}
  风险等级: {phase4_output.risk_level.value.upper()}

[bold]输出文件：[/bold]
  运行目录: {run_dir}
  实体提取: {entities_file}
  社交拓扑: {outputs["social_graph"]}
  交互日志: {outputs["tick_logs"]}
  Simulation Dataset: {outputs["simulation_dataset"]}
  Bypass 对比: {outputs["bypass_result"]}
  JSON 报告: {outputs["final_report_json"]}
  Markdown 报告: {outputs["final_report_md"]}
  Whitebox 摘要: {outputs["whitebox_summary"]}
  Whitebox 目录: {outputs["whitebox_dir"]}
  运行日志: {outputs["run_log"]}
  时间摘要: {outputs["timing_summary"]}
  运行元数据: {outputs["run_meta"]}

[bold]白盒报告完整性：[/bold]
  截断: {str(report_completeness["report_truncated"]).lower()}
  完整性评分: {report_completeness["report_completeness_score"]}
  字数: {report_completeness["report_char_count"]}
""")

    except KeyboardInterrupt:
        total_time = time.time() - start_time
        logger.log_error("keyboard_interrupt", "用户中断")
        logger.log_run_end("interrupted", total_time)
        write_run_meta(
            run_context,
            seed_file,
            status="interrupted",
            started_at=started_at,
            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            elapsed_seconds=round(total_time, 2),
        )
        console.print("\n[yellow]用户中断[/yellow]")
        sys.exit(1)
    except Exception as e:
        total_time = time.time() - start_time
        logger.log_error("main", str(e))
        logger.log_run_end("failed", total_time)
        write_run_meta(
            run_context,
            seed_file,
            status="failed",
            started_at=started_at,
            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            elapsed_seconds=round(total_time, 2),
            error=str(e),
        )
        console.print(f"\n[bold red]错误：[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
