"""Report skill discovery helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


SKILLS_DIR = Path(__file__).resolve().parent / "skills"


def list_report_skills() -> list[dict[str, str]]:
    skills = []
    if not SKILLS_DIR.exists():
        return skills
    for item in sorted(SKILLS_DIR.iterdir()):
        if not item.is_dir():
            continue
        skill_file = item / "skill.md"
        if not skill_file.exists():
            continue
        meta, _body = read_skill(item.name)
        skills.append({
            "id": str(meta.get("id") or item.name),
            "label": str(meta.get("label") or item.name),
            "description": str(meta.get("description") or ""),
            "dir": item.name,
        })
    return skills


def read_skill(skill_id: str) -> tuple[dict[str, str], str]:
    path = SKILLS_DIR / skill_id / "skill.md"
    text = path.read_text(encoding="utf-8")
    return split_frontmatter(text, fallback_id=skill_id)


def split_frontmatter(text: str, fallback_id: str = "") -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {"id": fallback_id, "label": fallback_id, "description": ""}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {"id": fallback_id, "label": fallback_id, "description": ""}, text
    raw_meta = text[4:end].strip().splitlines()
    body = text[end + 4 :].lstrip("\n")
    meta: dict[str, str] = {"id": fallback_id, "label": fallback_id, "description": ""}
    for line in raw_meta:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, body

