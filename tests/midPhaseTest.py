#!/usr/bin/env python3
"""
Phase 1→3 Pipeline Smoke — 跑 Phase1-3 完整管线到 parser 输出 simulation_dataset.json。

用途：
  - 单独验证 Phase 3 parser 产出是否完整
  - 不调 Phase 4，不生成 final_report
  - 产出的 simulation_dataset.json 可直接给产品端验证

用法：
    .venv/bin/python tests/midPhaseTest.py seeds/test8.txt

与 main.py 的区别：
  - Phase 1-2-3 tick simulation 逻辑相同
  - 不调 Phase 4 report_agent
  - 输出: parser.py → simulation_dataset.json（含风险判定/拐点/立场矩阵/实体/传播者信息）
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

_proj = Path(__file__).resolve().parent.parent
if str(_proj) not in sys.path:
    sys.path.insert(0, str(_proj))


def _ensure_visible_window():
    """如 stdout 非 TTY（后台/Hermes 调用），自动通过 osascript 开可见窗口。"""
    if sys.stdout.isatty():
        return  # 前台终端，正常运行
    py = shlex.quote(sys.executable)
    script = shlex.quote(sys.argv[0])
    script_args = " ".join(shlex.quote(a) for a in sys.argv[1:])
    cmd = (
        f'tell application "Terminal" to do script '
        f'"cd {shlex.quote(str(_proj))} && {py} {script} {script_args}"'
    )
    subprocess.run(["osascript", "-e", cmd])
    sys.exit(0)

import config
from src.llm_client import init_llm_client, register_observer
from src.phase4.paths import build_run_paths
from src.whitebox.run_meta import write_run_meta
from src.whitebox.token_tracker import TokenTracker
from src.display.run_log_writer import append_run_summary
from src.whitebox.dataset_spec_writer import generate_spec_yaml_from_files
from src.utils.runtime_logger import get_runtime_logger
from src.display import StatusBar


def run_phase1(seed_file: str, report_path=None):
    """Phase 1 实体提取（LLM）。"""
    from src.phase1 import extract_entities_from_file
    return extract_entities_from_file(seed_file, report_path=report_path)


def run_phase2(extraction_output):
    """Phase 2 社交拓扑构建。"""
    from src.phase2 import build_topology_from_extraction
    return build_topology_from_extraction(extraction_output)


def run_phase3_tick_simulation(extraction_output, phase2_output, seed_text):
    """Phase 3 tick 模拟。"""
    from src.phase3 import SimulationEngine
    engine = SimulationEngine(extraction_output, phase2_output, seed_text)
    tick_logs = engine.run_simulation(max_ticks=config.MAX_TICKS)
    x_t_sequence = engine.get_x_t_sequence()
    return tick_logs, x_t_sequence


def run_phase3_parser(extraction_output, phase2_output, tick_logs, x_t_sequence):
    """
    Phase 3 Parser Aggregation — 新路径的核心。

    调用 SimulationDatasetParser.parse()，其内部消费所有 Phase3 模块:
      - parser.py              → 编排
      - risk_analyzer.py       → 受众模式 / 风险判定 / 信号 / 风险类型
      - inflection_detector.py → 拐点检测
      - stance_analyzer.py     → 立场矩阵 + 最大负向迁移

    返回结构化 simulation_dataset（含 risk_verdict、inflection_points、agent_stance_matrix）。
    """
    from src.parser import SimulationDatasetParser
    parser = SimulationDatasetParser()
    dataset = parser.parse(
        extraction_output,
        phase2_output,
        tick_logs,
        x_t_sequence,
    )
    return dataset


def main():
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} <seed-file>")
        sys.exit(1)

    # 自动开可见 Terminal 窗口（后台调用时）
    _ensure_visible_window()

    seed_file = Path(sys.argv[1]).resolve()
    if not seed_file.exists():
        print(f"错误: {seed_file} 不存在")
        sys.exit(1)

    seed_text = seed_file.read_text(encoding="utf-8")
    logger = get_runtime_logger()

    _token_tracker = TokenTracker()
    register_observer(_token_tracker.on_llm_response)

    with StatusBar() as bar:
        run_context = build_run_paths(seed_file)
        run_dir = run_context["run_dir"]
        outputs = run_context["outputs"]
        logger.configure(run_dir=run_dir)
        started_at = datetime.now().isoformat()
        write_run_meta(run_context, seed_file=seed_file, status="running", started_at=started_at)

        logger.info("[新路径] 种子: %s (%d chars)", seed_file.name, len(seed_text))
        init_llm_client()

        start_time = time.time()
        try:
            # Phase 1
            logger.log_phase_start("phase1_extraction")
            logger.info("[Phase 1] 实体提取...")
            bar.set_phase("Phase 1 实体提取")
            t1 = time.time()
            extraction_output = run_phase1(str(seed_file), report_path=run_dir / "phase1_report.json")
            t1 = time.time() - t1
            logger.log_phase_end("phase1_extraction", elapsed=t1)
            logger.info("  √ %.1fs", t1)

            # Phase 2
            logger.log_phase_start("phase2_topology")
            logger.info("[Phase 2] 社交拓扑构建...")
            bar.set_phase("Phase 2 拓扑构建")
            t2 = time.time()
            phase2_output = run_phase2(extraction_output)
            t2 = time.time() - t2
            logger.log_phase_end("phase2_topology", elapsed=t2)
            logger.info("  √ %.1fs", t2)

            # Phase 3 tick simulation
            logger.log_phase_start("phase3_tick_simulation")
            logger.info("[Phase 3] 多轮涌现推演...")
            bar.set_phase("Phase 3 推演")
            t3 = time.time()
            tick_logs, x_t_sequence = run_phase3_tick_simulation(
                extraction_output, phase2_output, seed_text,
            )
            t3 = time.time() - t3
            logger.log_phase_end("phase3_tick_simulation", elapsed=t3)
            x_str = ", ".join(f"{x:.2f}" for x in x_t_sequence)
            logger.info("  √ %.1fs | %d ticks | x(t): [%s]", t3, len(tick_logs), x_str)

            # Phase 3 parser aggregation
            logger.log_phase_start("phase3_parser")
            logger.info("[Phase 3 Parser] 聚合分析...")
            t4 = time.time()
            dataset = run_phase3_parser(
                extraction_output, phase2_output, tick_logs, x_t_sequence,
            )
            t4 = time.time() - t4
            logger.log_phase_end("phase3_parser", elapsed=t4)
            logger.info("  √ %.2fs", t4)

            # 输出摘要
            sim = dataset["simulation_result"]
            rv = sim["risk_verdict"]
            rt = sim["risk_type_classification"]
            logger.info("")
            logger.info("  风险等级: %s (%s)", rv["level"], rv["label"])
            logger.info("  风险类型: %s", rt["primary_types"])
            logger.info("  拐点数量: %d", len(sim["inflection_points"]))
            logger.info("  最终 x(t): %s", sim["final_x"])
            logger.info("  极化指数: %.4f", sim["final_polarization_index"])

            # 保存 simulation_dataset
            dataset_path = run_dir / "simulation_dataset.json"
            dataset_path.write_text(
                json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info("")
            logger.info("✅ simulation_dataset 已保存: %s", dataset_path)
            # 生成带规格说明的 YAML 版（给人读）
            try:
                generate_spec_yaml_from_files(
                    dataset_path,
                    config.PROJECT_ROOT / "spec" / "dataset_fields.yaml",
                    run_dir / "simulation_dataset_spec.yaml",
                )
            except Exception:
                pass

            # 写入运行成功状态
            total = t1 + t2 + t3 + t4
            logger.log_run_end("success", total)
            write_run_meta(run_context, seed_file=seed_file, status="success",
                           started_at=started_at, elapsed_seconds=round(total, 2))

            logger.info("")
            logger.info("总耗时: %.1fs", total)

        except Exception as e:
            total = time.time() - start_time
            logger.log_error("main", str(e))
            logger.log_run_end("failed", total)
            write_run_meta(run_context, seed_file=seed_file, status="failed",
                           started_at=started_at, elapsed_seconds=round(total, 2),
                           error=str(e))
            sys.exit(1)
        finally:
            try:
                _run_status = logger.summary.get("run", {}).get("status", "unknown")
                _elapsed = time.time() - start_time if 'start_time' in dir() else None
                append_run_summary(
                    outputs["run_log"],
                    run_status=_run_status,
                    run_started_at=started_at,
                    run_elapsed=_elapsed,
                    seed_name=seed_file.name,
                    model_name=config.get_model_name(),
                    runtime_summary=logger.get_summary(),
                    token_summary=_token_tracker.get_summary(),
                )
            except Exception:
                pass  # 摘要写入失败不影响主流程


if __name__ == "__main__":
    main()
