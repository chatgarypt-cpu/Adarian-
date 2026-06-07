"""
Adarian v1.3.1 — Phase4 Pure Consumer Pipeline
---
主入口：串联 Phase 1-4 + Phase 3 Parser Aggregation。
Phase 4 消费 Phase3 parser 输出的 risk_verdict / inflection_points /
agent_stance_matrix，不调 report_agent 内联函数。

用法：
    python main.py [seed_file]

参数：
    seed_file: 种子文本文件路径，默认使用 seeds/example_event.txt

修改历史：
- v1.1.0: 初始实现，Phase 1-4 串联
- v1.1.1: 增加 Phase 0 调用，增加实体提取步骤
- v1.1.4: Phase 0 → Phase 1 重构，Analyzer/Generator/Validator 协作架构
- v1.1.10: LLM1/2/3 → Analyzer/Generator/Validator
- v1.3.0: Phase 3 Parser Aggregation + reality review + LLM fallback
- v1.3.1: Entrypoint Unification & Function Extraction
          - build_run_paths -> src/phase4/paths.py
          - write_run_meta / write_whitebox_* -> src/whitebox/run_meta.py
          - _build_report_context_new -> src/phase4/report_narrative.build_report_context_new
          - 移除 _run_bypass_comparison
          - 移除 legacy 导入
"""

import sys
import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

import config
from config import ensure_dirs
from src.llm_client import init_llm_client, get_llm_client
from src.schemas import EntityExtractionOutput, Phase2Output, Phase4Output, TickLog
from src.utils.runtime_logger import get_runtime_logger
from src.phase4.paths import build_run_paths
from src.whitebox.run_meta import write_run_meta, write_whitebox_artifacts

console = Console()


def print_banner():
    """打印横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║         Adarian v1.3.1 — Phase4 Pure Consumer Pipeline      ║
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


def run_phase3_parser(
    extraction_output: EntityExtractionOutput,
    phase2_output: Phase2Output,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
) -> dict:
    """执行 Phase 3 Parser Aggregation — 消费所有 Phase3 模块。"""
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


def run_phase4(
    extraction_output: EntityExtractionOutput,
    phase2_output: Phase2Output,
    tick_logs: List[TickLog],
    x_t_sequence: List[float],
    dataset: dict,
    json_output_path: Optional[Path] = None,
    markdown_output_path: Optional[Path] = None,
) -> Phase4Output:
    """执行 Phase 4：宏观洞察生成（Phase3 驱动版）

    消费 Phase3 parser 输出的 risk_verdict / inflection_points /
    agent_stance_matrix，不调 report_agent 内联函数。
    """
    from src.phase4.report_narrative import generate_report_with_llm_narrative, build_report_context_new
    from src.phase4.report_agent import (
        _build_code_owned_report_contract_block,
        parse_llm_report_response,
        save_report,
        save_markdown_report,
    )

    console.print(Panel("[bold]Phase 4: 宏观洞察生成（Phase3 驱动）[/bold]", border_style="cyan"))

    report_context = build_report_context_new(
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

        # Phase 3 Parser Aggregation
        logger.log_phase_start("phase3_parser_aggregation")
        phase3p_start = time.time()
        dataset = run_phase3_parser(
            extraction_output, phase2_output, tick_logs, x_t_sequence,
        )
        with open(outputs["simulation_dataset"], "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        phase3p_time = time.time() - phase3p_start
        logger.log_phase_end("phase3_parser_aggregation", phase3p_time)

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
        )
        whitebox_artifacts = write_whitebox_artifacts(run_context)
        report_completeness = whitebox_artifacts["report_completeness"]["result"]

        console.print("\n" + "=" * 60)
        console.print("[bold green]舆情预判完成！[/bold green]")
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
