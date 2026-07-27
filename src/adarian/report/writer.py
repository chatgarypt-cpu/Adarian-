"""LLM writer for Markdown reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adarian.llm_client import LLMClient

from .config import ReportModelConfig
from .skills_registry import resolve_report_skill


VERSION_GOALS = {
    "A": "自由生成，通读润色，建议保留 2-3 条核心对策。",
    "B": "便捷速览，正文 1400-1500 字，语言凝练。",
    "C": "详细阅读，正文 3800-4000 字，展开风险链条和对策。",
}
REPORT_TITLE_SUFFIX = "舆情风险研判"
REPORT_TITLE_MAX_CHARS = 30


def load_skill(skill_id: str) -> str:
    return resolve_report_skill(skill_id).body


def write_body(
    *,
    appendix_b: dict[str, Any],
    version: str,
    skill_id: str,
    model_config: ReportModelConfig,
    skill_snapshot: dict[str, Any] | None = None,
) -> str:
    skill = str((skill_snapshot or {}).get("body") or load_skill(skill_id))
    skill_label = str((skill_snapshot or {}).get("label") or skill_id)
    event_name = appendix_b.get("meta", {}).get("event_name") or "舆情事件"
    body_context = _body_context(appendix_b)
    system = f"""你是结构化数据报告写作器。当前写作 Skill 为“{skill_label}”。必须只使用用户提供的报告数据与写作规则，不得联网，不得使用模型对现实事件的额外知识补充事实。

{skill}
"""
    user = f"""请按照当前 Skill 生成 {version} 版无附录 Markdown 正文。

版本要求：{VERSION_GOALS.get(version, VERSION_GOALS['B'])}

硬性要求：
- 根据事件“{event_name}”提炼“核心主体 + 核心争议”的短标题，不得原样复制长事件摘要。
- 标题格式为 `# [简短事件名称]舆情风险研判`，简短事件名称不超过 20 字，标题总长度不超过 {REPORT_TITLE_MAX_CHARS} 字。
- 必须包含四章标题：
  `## 一、舆情概要`
  `## 二、演化分析`
  `## 三、风险研判`
  `## 四、对策意见`
- 第一章只能根据报告数据中的事件和主体概括，不得出现“模拟/推演/AI/模型”等系统机制词。
- 正文不得出现 appendix_b、simulation_dataset、completed world、world 编号、tick 或任何内部字段。
- 风险和对策必须可追溯到所提供的风险与对策数据，不得补写现实处置进展、具体日期或传播量。
- 写完后逐章核对当前 Skill 的结构、编号、篇幅和禁用语要求。
- 正文必须完整写完第四章，最后一句用句号结束。
- 只输出 Markdown 正文，不输出解释。

报告数据：
```json
{json.dumps(body_context, ensure_ascii=False)}
```
"""
    client = LLMClient(
        api_key=model_config.api_key,
        base_url=model_config.base_url,
        model=model_config.model,
        temperature=model_config.temperature,
        max_tokens=model_config.max_tokens,
        task_type="report_generation",
    )
    result = client.generate(system=system, user=user, response_model=None)
    return _normalize_report_title(str(result).strip())


def write_debug_body(body: str, output_dir: Path, version: str) -> Path:
    path = output_dir / f"debug_{version}_body.md"
    path.write_text(body, encoding="utf-8")
    return path


def _normalize_report_title(body: str, max_chars: int = REPORT_TITLE_MAX_CHARS) -> str:
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("# "):
            continue
        title = line[2:].strip()
        if len(title) <= max_chars:
            break
        event_title = title.removesuffix(REPORT_TITLE_SUFFIX).strip()
        available = max_chars - len(REPORT_TITLE_SUFFIX) - 1
        compact = event_title[:available].rstrip("，。；、：:—-的与及并")
        lines[index] = f"# {compact}…{REPORT_TITLE_SUFFIX}"
        break
    return "\n".join(lines).strip()


def _body_context(appendix_b: dict[str, Any]) -> dict[str, Any]:
    evolution = appendix_b.get("evolution_analysis") or {}
    return {
        "meta": appendix_b.get("meta") or {},
        "evolution_analysis": {
            "worlds_count": evolution.get("worlds_count"),
            "risk_level_distribution": evolution.get("risk_level_distribution"),
            "risk_type_frequency": evolution.get("risk_type_frequency"),
            "worst_reasonable_level": evolution.get("worst_reasonable_level"),
            "worst_reasonable_level_label": evolution.get("worst_reasonable_level_label"),
            "entities": evolution.get("entities") or [],
            "opinion_spreaders": evolution.get("opinion_spreaders") or [],
        },
        "risk_assessment": appendix_b.get("risk_assessment") or {},
        "countermeasures": appendix_b.get("countermeasures") or {},
    }
