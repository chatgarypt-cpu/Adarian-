"""
Adarian: 主入口
---
串联 Phase 1-4，执行完整的舆情预判流程。

v1.1.4 架构变化：
- Phase 0 → Phase 1：LLM1/2/3 协作架构
- 实体分类：事件实体 vs 意见传播实体
- Tick 0：事件实体发言
- Tick 1+：意见传播实体发言

用法：
    python main.py [seed_file]

参数：
    seed_file: 种子文本文件路径，默认使用 seeds/example_event.txt

修改历史：
- v1.1.0: 初始实现，Phase 1-4 串联
- v1.1.1: 增加 Phase 0 调用，增加实体提取步骤
- v1.1.4: Phase 0 → Phase 1 重构，LLM1/2/3 协作架构
"""

import sys
import time
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

import config
from config import ensure_dirs
from src.llm_client import init_llm_client, get_llm_client

console = Console()


def print_banner():
    """打印横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║              Adarian 多智能体舆情预判系统                   ║
║                    MVP V1.1.4 - 端到端演示                 ║
╚══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def run_phase1(seed_file: str):
    """执行 Phase 1：实体提取与分类（LLM1/2/3 协作）

    Args:
        seed_file: 种子文件路径

    Returns:
        extraction_output: Phase 1 实体提取结果
        entities_file: 保存的文件路径
    """
    from src.phase1_entity_extraction import extract_entities_from_file, save_entities_output

    console.print(Panel("[bold]Phase 1: 实体提取与分类（LLM1/2/3 协作）[/bold]", border_style="cyan"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]LLM1/2/3 协作提取实体...", total=1)
        extraction_output = extract_entities_from_file(seed_file)
        progress.update(task, completed=1)

    # 保存 Phase 1 输出
    entities_file = save_entities_output(extraction_output)

    console.print(f"  事件实体数量: {len(extraction_output.event_entities)}")
    console.print(f"  意见传播者数量: {len(extraction_output.opinion_spreaders)}")
    console.print(f"  事件类型: {extraction_output.event_type}")
    console.print(f"  事件温度: {extraction_output.event_temperature:.2f}")
    console.print(f"  事件烈度: {extraction_output.event_intensity:.2f}\n")

    return extraction_output, entities_file


def run_phase2(extraction_output):
    """执行 Phase 2：社交拓扑构建

    Args:
        extraction_output: Phase 1 实体提取结果

    Returns:
        Phase2Output
    """
    from src.phase2_topology_builder import (
        build_topology_from_extraction,
        validate_topology,
        save_social_graph
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
    save_social_graph(phase2_output)

    event_entity_count = sum(1 for n in phase2_output.nodes if n.entity_category == "event_entity")
    spreader_count = sum(1 for n in phase2_output.nodes if n.entity_category == "opinion_spreader")
    edge_count = len(phase2_output.edges)

    console.print(f"  事件实体（Core）: {event_entity_count}")
    console.print(f"  意见传播者（Periphery）: {spreader_count}")
    console.print(f"  总边数: {edge_count}\n")

    return phase2_output


def run_phase3(extraction_output, phase2_output, seed_text):
    """执行 Phase 3：多轮涌现推演

    Args:
        extraction_output: Phase 1 输出
        phase2_output: Phase 2 输出
        seed_text: 种子文本

    Returns:
        (tick_logs, x_t_sequence) tuple
    """
    from src.phase3_tick_simulation import (
        SimulationEngine, save_tick_logs, print_simulation_summary
    )

    console.print(Panel("[bold]Phase 3: 多轮涌现推演[/bold]", border_style="cyan"))

    engine = SimulationEngine(extraction_output, phase2_output, seed_text)

    tick_logs = engine.run_simulation(max_ticks=config.MAX_TICKS)

    save_tick_logs(tick_logs)
    print_simulation_summary(tick_logs)

    x_t_sequence = engine.get_x_t_sequence()
    console.print(f"\n  x(t) 序列: {' -> '.join([f'{x:.2f}' for x in x_t_sequence])}\n")

    return tick_logs, x_t_sequence


def run_phase4(extraction_output, tick_logs, x_t_sequence):
    """执行 Phase 4：宏观洞察生成

    Args:
        extraction_output: Phase 1 输出
        tick_logs: TickLog 列表
        x_t_sequence: x(t) 序列

    Returns:
        Phase4Output
    """
    from src.phase4_report_agent import (
        generate_report_with_llm, save_report, save_markdown_report
    )

    console.print(Panel("[bold]Phase 4: 宏观洞察生成[/bold]", border_style="cyan"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]生成报告...", total=1)
        phase4_output = generate_report_with_llm(extraction_output, tick_logs, x_t_sequence)
        progress.update(task, completed=1)

    save_report(phase4_output)
    save_markdown_report(phase4_output, extraction_output)

    return phase4_output


def main():
    """主函数"""
    print_banner()

    # 初始化
    ensure_dirs()

    # 检查 API 配置
    if not config.LLM_API_KEY:
        console.print("[bold red]错误：[/bold red] 未配置 LLM API Key")
        console.print("请创建 .env 文件或设置环境变量 LLM_API_KEY")
        sys.exit(1)

    # 初始化 LLM 客户端
    init_llm_client()
    console.print(f"[green]OK[/green] LLM: {config.LLM_PROVIDER} / {config.get_model_name()}\n")

    # 加载种子文本
    if len(sys.argv) > 1:
        seed_file = Path(sys.argv[1])
    else:
        seed_file = config.SEEDS_DIR / "example_event.txt"

    if not seed_file.exists():
        console.print(f"[bold red]错误：[/bold red] 种子文件不存在: {seed_file}")
        sys.exit(1)

    console.print(f"种子文件: {seed_file.name}\n")

    with open(seed_file, "r", encoding="utf-8") as f:
        seed_text = f.read()

    # 计时
    start_time = time.time()

    try:
        # Phase 1: 实体提取与分类（LLM1/2/3 协作）
        phase1_start = time.time()
        extraction_output, entities_file = run_phase1(str(seed_file))
        phase1_time = time.time() - phase1_start

        # Phase 2: 社交拓扑构建
        phase2_start = time.time()
        phase2_output = run_phase2(extraction_output)
        phase2_time = time.time() - phase2_start

        # Phase 3: 多轮涌现推演
        phase3_start = time.time()
        tick_logs, x_t_sequence = run_phase3(extraction_output, phase2_output, seed_text)
        phase3_time = time.time() - phase3_start

        # Phase 4: 宏观洞察生成
        phase4_start = time.time()
        phase4_output = run_phase4(extraction_output, tick_logs, x_t_sequence)
        phase4_time = time.time() - phase4_start

        # 总耗时
        total_time = time.time() - start_time

        # 打印最终结果
        console.print("\n" + "=" * 60)
        console.print("[bold green]舆情预判完成！[/bold green]")
        console.print("=" * 60)

        console.print(f"""
[bold]执行时间：[/bold]
  Phase 1 (实体提取): {phase1_time:.1f}s
  Phase 2 (拓扑构建): {phase2_time:.1f}s
  Phase 3 (模拟推演): {phase3_time:.1f}s
  Phase 4 (报告生成): {phase4_time:.1f}s
  总计: {total_time:.1f}s

[bold]舆情指标：[/bold]
  x(t) 序列: {' -> '.join([f'{x:.2f}' for x in x_t_sequence])}
  最终极化指数: {tick_logs[-1].global_metrics.polarization_index:.2f}
  风险等级: {phase4_output.risk_level.value.upper()}

[bold]输出文件：[/bold]
  实体提取: {entities_file}
  社交拓扑: {config.SOCIAL_GRAPH_PATH}
  交互日志: {config.TICK_LOGS_DIR}/
  最终报告: {config.FINAL_REPORT_PATH.with_suffix('.md')}
""")

    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]错误：[/bold red] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def get_risk_color(risk: str) -> str:
    """获取风险等级对应的颜色"""
    colors = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
        "critical": "bold red",
    }
    return colors.get(risk, "white")


if __name__ == "__main__":
    main()
