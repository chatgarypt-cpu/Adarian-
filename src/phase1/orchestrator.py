"""Phase 1 Orchestrator — Analyzer → Generator → Compiler → Repair → Pydantic."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console

import config
from src.schemas import EntityExtractionOutput
from src.display import get_bar
from .analyzer import analyzer_set_parameters
from .compiler import _post_process_entities
from .generator import generator_create_event_entities
from .generator import generator_create_spreaders_concurrent
from .utils import console

# 主函数：带迭代校验的实体提取
# =============================================================================

MAX_RETRIES = 3

def extract_entities_with_validation(seed_text: str) -> EntityExtractionOutput:
    """
    Phase 1 Orchestrator: Analyzer → Entity Generator → Concurrent Spreader Generator → Validator

    Args:
        seed_text: 种子文本内容

    Returns:
        EntityExtractionOutput: 包含 event_entities, opinion_spreaders 等
    """
    params = analyzer_set_parameters(seed_text)
    last_validation: Optional[Dict[str, Any]] = None
    error_feedback = ""

    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            console.print(f"[yellow]重试第 {attempt + 1}/{MAX_RETRIES} 轮...[/yellow]")

        try:
            # Step 1: 提取事件实体 + 规划传播者框架
            entities_data = generator_create_event_entities(
                seed_text=seed_text,
                event_scale=params["event_scale"],
                event_controversy=params["event_controversy"],
                event_type=params["event_type"],
                event_summary=params["event_summary"],
                error_feedback=error_feedback,
            )
        except ValueError as e:
            last_validation = {
                "pass": False,
                "message": "Generator 输出解析失败",
                "errors": [str(e)],
            }
            error_feedback = (
                "上一轮输出未能解析为合法 JSON。"
                "请严格输出单个 JSON object，不要附带解释、不要使用双大括号模板。"
                f"\n- {e}"
            )
            continue

        # Step 2: 并发生成每个传播者的完整人设
        try:
            spreader_plan = entities_data.get("opinion_spreaders", [])
            event_entities = entities_data.get("event_entities", [])
            spreaders = generator_create_spreaders_concurrent(
                spreaders_plan=spreader_plan,
                event_summary=params["event_summary"],
                event_type=params["event_type"],
                event_entities=event_entities,
            )
            entities_data["opinion_spreaders"] = spreaders
        except ValueError as e:
            last_validation = {
                "pass": False,
                "message": "传播者人设生成失败",
                "errors": [str(e)],
            }
            error_feedback = (
                f"传播者人设生成失败: {e}"
            )
            continue

        # Step 3: 校验 + Repair Loop（确定性 Pydantic 校验 + 定向修复）
        from pydantic import ValidationError
        merged_output = {
            "event_summary": params["event_summary"],
            "event_scale": params["event_scale"],
            "event_controversy": params["event_controversy"],
            "event_type": params["event_type"],
            "event_entities": entities_data.get("event_entities", []),
            "opinion_spreaders": entities_data.get("opinion_spreaders", []),
            "relations": entities_data.get("relations", []),
        }
        try:
            return EntityExtractionOutput(**merged_output)
        except ValidationError as e:
            errors_str = "; ".join(
                f"{err['loc']}: {err['msg']}" for err in e.errors()
            )
            console.print(f"  [yellow]⚠[/yellow] Pydantic 校验失败，尝试 Repair Loop...")

            # Repair: 修正 related_event_entity 不匹配
            spreaders = merged_output.get("opinion_spreaders", [])
            entities = merged_output.get("event_entities", [])
            entity_names = {e["name"] for e in entities}
            import difflib
            repaired = False
            for s in spreaders:
                ref = s.get("related_event_entity", "")
                if ref not in entity_names:
                    match = difflib.get_close_matches(ref, entity_names, n=1, cutoff=0.6)
                    if match:
                        console.print(f"  [cyan]  Repair: {s.get('group_name', '?')} related_event_entity '{ref}' -> '{match[0]}'[/cyan]")
                        s["related_event_entity"] = match[0]
                        repaired = True
            # Repair: 修正 missing P=+1 / P=-1
            if not any(s.get("P") == +1 for s in spreaders) and spreaders:
                spreaders[0]["P"] = +1
                console.print(f"  [cyan]  Repair: {spreaders[0].get('group_name', '?')} P 设为 +1（补充支持阵营）[/cyan]")
                repaired = True
            elif not any(s.get("P") == -1 for s in spreaders) and spreaders:
                spreaders[0]["P"] = -1
                console.print(f"  [cyan]  Repair: {spreaders[0].get('group_name', '?')} P 设为 -1（补充反对阵营）[/cyan]")
                repaired = True

            if repaired:
                try:
                    return EntityExtractionOutput(**merged_output)
                except ValidationError as e2:
                    errors_str = "; ".join(
                        f"{err['loc']}: {err['msg']}" for err in e2.errors()
                    )

            console.print(f"  [yellow]✗[/yellow] Repair 未能修复，全量重试: {e.errors()[0].get('msg', str(e))}")
            last_validation = {
                "pass": False,
                "message": "Pydantic / Repair 校验失败",
                "errors": [errors_str],
            }
            error_feedback = errors_str
            continue

    raise ValueError(
        "Phase 1 校验失败，超过最大重试次数。"
        f" 最后一次校验结果: {last_validation}"
    )


# =============================================================================
# 兼容函数
# =============================================================================

def extract_entities(seed_text: str) -> EntityExtractionOutput:
    """
    兼容函数：直接调用 orchestrator 入口

    Args:
        seed_text: 种子文本内容

    Returns:
        EntityExtractionOutput
    """
    return extract_entities_with_validation(seed_text)


def extract_entities_from_file(seed_file: str) -> EntityExtractionOutput:
    """
    从种子文件提取实体

    Args:
        seed_file: 种子文件路径

    Returns:
        EntityExtractionOutput 对象
    """
    seed_text = Path(seed_file).read_text(encoding="utf-8")
    return extract_entities_with_validation(seed_text)


def save_entities_output(
    entities_output: EntityExtractionOutput,
    output_path: Optional[str] = None
) -> str:
    """
    保存实体提取结果到 JSON 文件

    Args:
        entities_output: 实体提取结果
        output_path: 输出路径

    Returns:
        保存的文件路径
    """
    if output_path is None:
        output_path = config.ENTITIES_OUTPUT_PATH
    else:
        output_path = Path(output_path)

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(entities_output.model_dump(), f, ensure_ascii=False, indent=2)

    console.print(f"[green]✓[/green] 实体提取结果已保存至: {output_path}")

    return str(output_path)


# =============================================================================
# 主入口（可独立运行）
# =============================================================================

if __name__ == "__main__":
    import sys
    from pathlib import Path

    # 检查是否提供了种子文件路径
    if len(sys.argv) < 2:
        seed_file = Path(__file__).parent.parent / "seeds" / "example_event.txt"
        if not seed_file.exists():
            console.print("[bold red]错误：[/bold red] 未提供种子文件路径，且默认文件不存在")
            console.print(f"请将种子文本文件放入: seeds/")
            sys.exit(1)
    else:
        seed_file = Path(sys.argv[1])

    console.print(f"[bold]读取种子文本：[/bold] {seed_file}")

    # 提取实体
    entities_output = extract_entities_from_file(str(seed_file))

    # 保存结果
    output_path = save_entities_output(entities_output)

    # 打印摘要
    console.print("\n[bold]事件实体：[/bold]")
    for entity in entities_output.event_entities:
        console.print(f"  - {entity.name} ({entity.type}): {entity.role}")

    console.print(f"\n[bold]意见传播者：[/bold]")
    for spreader in entities_output.opinion_spreaders:
        console.print(f"  - {spreader.group_name} (关联: {spreader.related_event_entity})")
        console.print(f"    I={spreader.I}, P={spreader.P}, susceptibility={spreader.susceptibility}")

    console.print(f"\n[bold]关系：[/bold]")
    for relation in entities_output.relations:
        console.print(f"  - {relation.source} --[{relation.type}]--> {relation.target}")
