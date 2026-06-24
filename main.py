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
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

from adarian import config
from adarian.config import ensure_dirs
from adarian.llm_client import init_llm_client, get_llm_client, register_observer
from adarian.schemas import Phase4Output
from adarian.utils.runtime_logger import get_runtime_logger
from adarian.phase4.paths import build_run_paths
from adarian.output_paths import create_run_paths
from adarian.phase4.report_narrative import generate_report_with_llm_narrative
from adarian.phase4.report_agent import save_report, save_markdown_report
from adarian.whitebox.run_meta import write_run_meta
from adarian.whitebox.token_tracker import TokenTracker
from adarian.whitebox.dataset_spec_writer import generate_spec_yaml_from_files
from adarian.whitebox.classifier_reporter import write_classification_summary
from adarian.display.run_log_writer import append_run_summary, log_token_summary
from adarian.display import StatusBar


def run_phase4(
    dataset: dict,
    json_output_path: Path = None,
    markdown_output_path: Path = None,
) -> Phase4Output:
    """Phase 4：宏观洞察生成（纯消费 simulation_dataset）"""
    phase4_output, markdown = generate_report_with_llm_narrative(
        dataset,
        get_llm_client_func=get_llm_client,
    )
    save_report(phase4_output, output_path=json_output_path)
    save_markdown_report(
        phase4_output,
        output_path=markdown_output_path,
        markdown=markdown,
    )
    return phase4_output


def main(seed_path: str | Path | None = None):
    if seed_path:
        seed_file = Path(seed_path).resolve()
    elif len(sys.argv) > 1:
        seed_file = Path(sys.argv[1])
    else:
        seed_file = config.SEEDS_DIR / "example_event.txt"

    ensure_dirs()
    if not config.LLM_API_KEY:
        print("错误：未配置 LLM API Key")
        sys.exit(1)

    if not seed_file.exists():
        print(f"错误：种子文件不存在: {seed_file}")
        sys.exit(1)

    seed_file = seed_file.resolve()
    seed_text = seed_file.read_text(encoding="utf-8")

    init_llm_client()

    # Token 追踪
    _token_tracker = TokenTracker()
    register_observer(_token_tracker.on_llm_response)

    logger = get_runtime_logger()
    run_context = create_run_paths(seed_file).build()
    run_dir = run_context["run_dir"]
    outputs = run_context["outputs"]
    logger.configure(run_dir=run_dir)
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_run_meta(run_context, seed_file, status="running", started_at=started_at)
    logger.log_run_start("normal", str(seed_file), str(run_dir))

    start_time = time.time()

    try:
        with StatusBar() as bar:
            # Phase 1
            logger.log_phase_start("phase1_entity_extraction")
            bar.set_phase("Phase 1 实体提取")
            t1 = time.time()
            from adarian.phase1 import extract_entities_from_file, save_entities_output
            extraction_output = extract_entities_from_file(str(seed_file))
            entities_file = save_entities_output(extraction_output, output_path=outputs["entities"])
            t1 = time.time() - t1
            logger.log_phase_end("phase1_entity_extraction", t1)
            logger.info("  √ %.1fs", t1)

            # Phase 2
            logger.log_phase_start("phase2_topology_builder")
            bar.set_phase("Phase 2 拓扑构建")
            t2 = time.time()
            from adarian.phase2 import build_topology_from_extraction
            phase2_output = build_topology_from_extraction(extraction_output)
            t2 = time.time() - t2
            logger.log_phase_end("phase2_topology_builder", t2)
            logger.info("  √ %.1fs", t2)

            # Phase 3 tick simulation
            logger.log_phase_start("phase3_tick_simulation")
            bar.set_phase("Phase 3 推演")
            t3 = time.time()
            from adarian.phase3 import SimulationEngine, save_tick_logs, print_simulation_summary
            engine = SimulationEngine(extraction_output, phase2_output, seed_text)
            tick_logs = engine.run_simulation(max_ticks=config.MAX_TICKS)
            save_tick_logs(tick_logs, output_path=outputs["tick_logs"])
            x_t_sequence = engine.get_x_t_sequence()
            t3 = time.time() - t3
            logger.log_phase_end("phase3_tick_simulation", t3)
            x_str = ", ".join(f"{x:.2f}" for x in x_t_sequence)
            logger.info("  √ %.1fs | %d ticks | x(t): [%s]", t3, len(tick_logs), x_str)

            # 分析聚合（analysis → parser 编排）
            logger.log_phase_start("analysis_aggregation")
            bar.set_phase("分析聚合")
            t4 = time.time()
            from adarian.parser import SimulationDatasetParser
            parser = SimulationDatasetParser()
            dataset = parser.parse(extraction_output, phase2_output, tick_logs, x_t_sequence, seed_text=seed_text)
            with open(outputs["simulation_dataset"], "w", encoding="utf-8") as f:
                json.dump(dataset, f, ensure_ascii=False, indent=2)
            # 白盒：分类摘要
            rtc = dataset.get("simulation_result", {}).get("risk_type_classification", {})
            write_classification_summary(
                run_dir / "whitebox",
                primary_types=rtc.get("primary_types", []),
                type_labels=rtc.get("type_labels", []),
                primary_domain=rtc.get("primary_domain"),
                primary_domain_label=rtc.get("primary_domain_label"),
            )
            try:
                generate_spec_yaml_from_files(
                    outputs["simulation_dataset"],
                    config.PROJECT_ROOT / "spec" / "dataset_fields.yaml",
                    run_dir / "simulation_dataset_spec.yaml",
                )
            except Exception:
                pass
            t4 = time.time() - t4
            logger.log_phase_end("analysis_aggregation", t4)
            # 捕获分析层行为：风险类型和域
            rtc = dataset.get("simulation_result", {}).get("risk_type_classification", {})
            pts = rtc.get("primary_types", [])
            labels = rtc.get("type_labels", [])
            domain = rtc.get("primary_domain_label", "")
            types_str = "、".join(labels) if labels else "（无）"
            logger.info("  √ %.2fs | 风险类型: %s | 一级域: %s", t4, types_str, domain if domain else "（无）")

            # Phase 4
            logger.log_phase_start("phase4_report_agent")
            bar.set_phase("Phase 4 报告生成")
            t5 = time.time()
            phase4_output = run_phase4(
                dataset,
                json_output_path=outputs["final_report_json"],
                markdown_output_path=outputs["final_report_md"],
            )
            t5 = time.time() - t5
            logger.log_phase_end("phase4_report_agent", t5)
            logger.info("  √ %.1fs", t5)

        # StatusBar 已退出，logger 仍在 → 汇总输出（同时进终端和 run.log）
        total_time = time.time() - start_time
        logger.log_run_end("success", total_time)
        write_run_meta(
            run_context, seed_file, status="success", started_at=started_at,
            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            elapsed_seconds=round(total_time, 2),
            x_t_sequence=list(x_t_sequence),
            final_polarization_index=tick_logs[-1].global_metrics.polarization_index,
            risk_level=phase4_output.risk_level.value,
        )
        logger.info("")
        logger.info("===== 执行完成 =====")
        logger.info("Phase 1 (实体提取):  %.1fs", t1)
        logger.info("Phase 2 (拓扑构建):  %.1fs", t2)
        logger.info("Phase 3 (模拟推演):  %.1fs", t3)
        logger.info("分析层:              %.1fs", t4)
        logger.info("Phase 4 (报告生成):  %.1fs", t5)
        logger.info("总计:                %.1fs", total_time)
        logger.info("")
        logger.info("模拟指标:")
        logger.info("  x(t) 最终: %.2f", x_t_sequence[-1])
        logger.info("  极化指数: %.4f", tick_logs[-1].global_metrics.polarization_index)
        logger.info("  风险等级: %s", phase4_output.risk_level.value.upper())
        logger.info("")
        logger.info("输出文件: %s", run_dir)
        log_token_summary(logger, _token_tracker.get_summary())

    except KeyboardInterrupt:
        total_time = time.time() - start_time
        logger.log_error("keyboard_interrupt", "用户中断")
        logger.log_run_end("interrupted", total_time)
        write_run_meta(run_context, seed_file, status="interrupted",
                       started_at=started_at,
                       completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                       elapsed_seconds=round(total_time, 2))
        sys.exit(1)
    except Exception as e:
        total_time = time.time() - start_time
        logger.log_error("main", str(e))
        logger.log_run_end("failed", total_time)
        write_run_meta(run_context, seed_file, status="failed",
                       started_at=started_at,
                       completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                       elapsed_seconds=round(total_time, 2), error=str(e))
        sys.exit(1)
    finally:
        if 'run_context' in dir() and 'logger' in dir():
            try:
                append_run_summary(
                    outputs["run_log"],
                    run_status=logger.summary.get("run", {}).get("status", "unknown"),
                    run_started_at=started_at,
                    run_elapsed=time.time() - start_time if 'start_time' in dir() else None,
                    seed_name=seed_file.name,
                    model_name=config.get_model_name(),
                    runtime_summary=logger.get_summary(),
                    token_summary=_token_tracker.get_summary(),
                )
            except Exception:
                pass


if __name__ == "__main__":
    main()
