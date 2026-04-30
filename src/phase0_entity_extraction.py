"""
Phase 0: 实体提取模块
---
从种子文本中提取核心实体、实体关系和事件热度参数。

为什么需要这个模块（Why）：
- v1.1.0 版本直接让 LLM 凭空想象人群，导致生成的 Agent 与事件脱节
- 通过先提取实体，可以确保生成的 Agent 与事件核心利益相关方对齐
- 为后续的确认偏差模拟提供 event_temperature 参数

新增于：v1.1.1
"""

import json
from pathlib import Path
from typing import Optional
from rich.console import Console

from src.llm_client import get_llm_client
from src.schemas import EntityExtractionOutput

console = Console()


# =============================================================================
# Prompt 模板
# =============================================================================

PHASE0_SYSTEM_PROMPT = """你是一位资深的事件分析专家。你的任务是从一段新闻/事件材料中提取核心信息。

你必须严格按照以下 JSON 格式输出，不要输出任何其他内容：
{{
  "event_summary": "一句话概括事件（50字以内）",
  "core_entities": [
    {{
      "name": "实体名称",
      "type": "individual | organization | group",
      "role": "在事件中的角色"
    }}
  ],
  "relations": [
    {{
      "source": "实体A的名称",
      "target": "实体B的名称",
      "type": "关系类型（如：雇佣、监管、销售）"
    }}
  ],
  "event_temperature": 0.0到1.0之间的浮点数,
  "event_type": "事件类型（如：产品质量危机、校园冲突、政策争议）"
}}

约束条件：
1. core_entities 数量必须在 3-5 个之间（只提取最核心的实体）
2. 实体类型说明：
   - individual: 具体的个人（如"肖同学"）
   - organization: 组织机构（如"武汉大学""某品牌"）
   - group: 群体（如"消费者""学生群体"）
3. event_temperature 的判断标准：
   - 涉及范围：个人事件(0.2) < 群体事件(0.5) < 全社会事件(0.8)
   - 争议性：事实清晰(0.3) < 存在争议(0.6) < 高度对立(0.9)
   - 社会影响：局部(0.2) < 行业(0.5) < 全国(0.8)
   - 综合三个维度取平均值
4. relations 必须基于 core_entities 中的实体，source 和 target 必须是已提取的实体名称
"""

PHASE0_USER_PROMPT = """请分析以下事件材料：

{seed_text}
"""


# =============================================================================
# 核心函数
# =============================================================================

def extract_entities(seed_text: str) -> EntityExtractionOutput:
    """
    从种子文本中提取核心实体和关系

    为什么需要这个模块（Why）：
    - 当前 Phase 1 直接生成 Agent，缺少事件结构化信息作为锚点
    - 通过先提取实体，可以确保生成的 Agent 与事件核心利益相关方对齐
    - 为后续的确认偏差模拟提供 event_temperature 参数

    新增于：v1.1.1

    Args:
        seed_text: 种子文本内容

    Returns:
        EntityExtractionOutput: 包含核心实体、关系、事件热度等
    """
    llm = get_llm_client()

    user_prompt = PHASE0_USER_PROMPT.format(seed_text=seed_text)

    console.print("[bold cyan]Phase 0:[/bold cyan] 正在提取实体...")

    result = llm.generate(
        system=PHASE0_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=EntityExtractionOutput,
    )

    console.print(f"[green]✓[/green] 实体提取完成：识别出 {len(result.core_entities)} 个核心实体")
    console.print(f"  事件类型：{result.event_type}")
    console.print(f"  事件热度：{result.event_temperature:.2f}")

    return result


def extract_entities_from_file(seed_file: str) -> EntityExtractionOutput:
    """
    从种子文件提取实体

    Args:
        seed_file: 种子文件路径

    Returns:
        EntityExtractionOutput 对象
    """
    seed_path = Path(seed_file)

    if not seed_path.exists():
        raise FileNotFoundError(f"种子文件不存在: {seed_file}")

    with open(seed_path, "r", encoding="utf-8") as f:
        seed_text = f.read()

    return extract_entities(seed_text)


def save_entities_output(
    entities_output: EntityExtractionOutput,
    output_path: Optional[str] = None
) -> str:
    """
    保存实体提取结果到 JSON 文件

    Args:
        entities_output: 实体提取结果
        output_path: 输出路径，默认使用 config.OUTPUTS_DIR / "entities_and_relations.json"

    Returns:
        保存的文件路径
    """
    if output_path is None:
        output_path = Path(__file__).parent.parent / "outputs" / "entities_and_relations.json"
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
        # 默认使用 example_event.txt
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
    console.print("\n[bold]实体提取摘要：[/bold]")
    for entity in entities_output.core_entities:
        console.print(f"  - {entity.name} ({entity.type}): {entity.role}")

    console.print(f"\n[bold]关系：[/bold]")
    for relation in entities_output.relations:
        console.print(f"  - {relation.source} --[{relation.type}]--> {relation.target}")
