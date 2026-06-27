"""Tests for Phase 3 tick text length handling."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_src = str(PROJECT_ROOT / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from adarian.phase3.tick_simulation import SimulationEngine
from adarian.schemas import AgentEntry


def test_agent_response_parser_keeps_useful_long_text():
    engine = SimulationEngine.__new__(SimulationEngine)
    comment = "这是一段完整的模拟发言，强调不同群体在同一事件中的判断依据和情绪变化。" * 12
    reasoning = "理由说明需要保留上下文，方便后续报告追溯立场变化原因。" * 10
    response = json.dumps({
        "comment": comment,
        "new_stance": 4.2,
        "reasoning": reasoning,
    }, ensure_ascii=False)

    parsed_comment, parsed_stance, parsed_reasoning = engine._parse_agent_response(response)

    assert parsed_comment == comment
    assert parsed_stance == 4.2
    assert parsed_reasoning == reasoning


def test_agent_entry_schema_accepts_text_above_old_limits():
    comment = "评论内容" * 80
    reasoning = "理由内容" * 40

    entry = AgentEntry(
        agent_id=1,
        group_name="测试群体",
        saw_posts_from=[],
        previous_stance=5.0,
        current_stance=4.2,
        stance_delta=-0.8,
        susceptibility=0.5,
        change_reason="within_effective_delta",
        comment=comment,
        reasoning=reasoning,
    )

    assert entry.comment == comment
    assert entry.reasoning == reasoning
