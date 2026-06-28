"""LLM writer for Markdown reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adarian.llm_client import LLMClient

from .config import ReportModelConfig, skill_path
from .skills_registry import read_skill


VERSION_GOALS = {
    "A": "自由生成，通读润色，建议保留 2-3 条核心对策。",
    "B": "便捷速览，正文 1400-1500 字，语言凝练。",
    "C": "详细阅读，正文 3800-4000 字，展开风险链条和对策。",
}


def load_skill(skill_id: str) -> str:
    path = skill_path(skill_id)
    if path.exists():
        _meta, body = read_skill(skill_id)
        return body
    _meta, body = read_skill("default_government")
    return body


def write_body(*, appendix_b: dict[str, Any], version: str, skill_id: str, model_config: ReportModelConfig) -> str:
    skill = load_skill(skill_id)
    event_name = appendix_b.get("meta", {}).get("event_name") or "舆情事件"
    body_context = _body_context(appendix_b)
    system = f"""你是 Adarian 内部报告写作器。必须只使用用户提供的 appendix_b JSON 与写作规则，不得联网，不得使用你对现实事件的额外知识补事实。

{skill}
"""
    user = f"""请生成 {version} 版无附录 Markdown 正文。

版本要求：{VERSION_GOALS.get(version, VERSION_GOALS['B'])}

硬性要求：
- 标题必须是 `# {event_name}舆情风险研判`
- 必须包含四章标题：
  `## 一、舆情概要`
  `## 二、演化分析`
  `## 三、风险研判`
  `## 四、对策意见`
- 第一章只能基于 appendix_b.meta / evolution_analysis.entities 概括事件，不得出现“模拟/推演/AI/模型”等系统机制词。
- 正文不得出现 world_0、tick、stance_score、polarization_index 等内部字段。
- 风险和对策必须可追溯到 appendix_b.risk_assessment / countermeasures。
- 正文必须完整写完第四章，最后一句用句号结束。
- 只输出 Markdown 正文，不输出解释。

appendix_b JSON：
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
    return str(result).strip()


def write_debug_body(body: str, output_dir: Path, version: str) -> Path:
    path = output_dir / f"debug_{version}_body.md"
    path.write_text(body, encoding="utf-8")
    return path


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
