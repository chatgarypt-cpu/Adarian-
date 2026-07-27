"""Report skill discovery, validation, and user Markdown imports."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


BUILTIN_SKILLS_DIR = Path(__file__).resolve().parent / "skills"
SKILLS_DIR = BUILTIN_SKILLS_DIR  # Backward-compatible name for existing imports.
SKILL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
ALLOWED_SKILL_FILES = {"skill.md", "quality_checklist.yaml", "appendix.md"}
MAX_SKILL_FILE_BYTES = 512 * 1024


@dataclass(frozen=True)
class ResolvedReportSkill:
    id: str
    label: str
    description: str
    version: str
    source: str
    directory: Path
    body: str
    checklist: dict[str, Any]
    appendix: str
    checksum: str
    files: tuple[str, ...]

    def public_metadata(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "version": self.version,
            "source": self.source,
            "dir": self.directory.name,
            "directory": str(self.directory),
            "checksum": self.checksum,
            "files": list(self.files),
            "deletable": self.source == "user",
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            **self.public_metadata(),
            "body": self.body,
            "checklist": self.checklist,
            "appendix": self.appendix,
        }


def user_skills_dir() -> Path:
    configured = os.getenv("ADARIAN_REPORT_SKILLS_DIR", "").strip()
    return Path(configured).expanduser() if configured else Path.home() / ".adarian" / "report_skills"


def skill_locations() -> dict[str, str]:
    user_dir = user_skills_dir()
    user_dir.mkdir(parents=True, exist_ok=True)
    return {"builtin": str(BUILTIN_SKILLS_DIR), "user": str(user_dir)}


def list_report_skills() -> list[dict[str, Any]]:
    skills: list[dict[str, Any]] = []
    for source, root in (("builtin", BUILTIN_SKILLS_DIR), ("user", user_skills_dir())):
        if not root.exists():
            continue
        for item in sorted(root.iterdir()):
            if not item.is_dir() or not (item / "skill.md").is_file():
                continue
            try:
                skills.append(_load_skill_directory(item, source).public_metadata())
            except (OSError, TypeError, ValueError, yaml.YAMLError):
                continue
    return sorted(skills, key=lambda item: (item["source"] != "builtin", item["label"], item["id"]))


def resolve_report_skill(skill_id: str) -> ResolvedReportSkill:
    _validate_skill_id(skill_id)
    builtin = BUILTIN_SKILLS_DIR / skill_id
    if (builtin / "skill.md").is_file():
        return _load_skill_directory(builtin, "builtin")
    user = user_skills_dir() / skill_id
    if (user / "skill.md").is_file():
        return _load_skill_directory(user, "user")
    raise FileNotFoundError(f"report skill not found: {skill_id}")


def read_skill(skill_id: str) -> tuple[dict[str, str], str]:
    skill = resolve_report_skill(skill_id)
    return {
        "id": skill.id,
        "label": skill.label,
        "description": skill.description,
        "version": skill.version,
    }, skill.body


def import_report_skill(content: bytes, *, replace: bool = False) -> dict[str, Any]:
    if not content:
        raise ValueError("Skill Markdown 为空")
    if len(content) > MAX_SKILL_FILE_BYTES:
        raise ValueError("Skill Markdown 超过 512 KB")
    text = content.decode("utf-8")
    meta, _body = split_frontmatter(text)
    skill_id = str(meta.get("id") or "").strip()
    _validate_skill_id(skill_id)
    if (BUILTIN_SKILLS_DIR / skill_id / "skill.md").exists():
        raise ValueError("用户 Skill 不能覆盖内置 Skill")

    root = user_skills_dir()
    root.mkdir(parents=True, exist_ok=True)
    target = root / skill_id
    if target.exists() and not replace:
        raise FileExistsError(f"用户 Skill 已存在：{skill_id}")

    with tempfile.TemporaryDirectory(prefix=".skill-import-", dir=root) as temp_name:
        temp_dir = Path(temp_name)
        (temp_dir / "skill.md").write_bytes(content)
        _load_skill_directory(temp_dir, "user", expected_id=skill_id)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(temp_dir, target)
    return _load_skill_directory(target, "user").public_metadata()


def delete_report_skill(skill_id: str) -> None:
    _validate_skill_id(skill_id)
    if (BUILTIN_SKILLS_DIR / skill_id / "skill.md").exists():
        raise PermissionError("内置 Skill 不可删除")
    target = user_skills_dir() / skill_id
    if not target.exists():
        raise FileNotFoundError(f"用户 Skill 不存在：{skill_id}")
    shutil.rmtree(target)


def split_frontmatter(text: str, fallback_id: str = "") -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {"id": fallback_id, "label": fallback_id, "description": "", "version": "1"}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {"id": fallback_id, "label": fallback_id, "description": "", "version": "1"}, text
    raw_meta = text[4:end].strip().splitlines()
    body = text[end + 4 :].lstrip("\n")
    meta: dict[str, str] = {"id": fallback_id, "label": fallback_id, "description": "", "version": "1"}
    for line in raw_meta:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, body


def _load_skill_directory(directory: Path, source: str, expected_id: str = "") -> ResolvedReportSkill:
    skill_path = directory / "skill.md"
    text = skill_path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(text, fallback_id=directory.name)
    skill_id = str(meta.get("id") or directory.name).strip()
    _validate_skill_id(skill_id)
    if expected_id and skill_id != expected_id:
        raise ValueError("Skill ID 与导入内容不一致")
    label = str(meta.get("label") or skill_id).strip()
    if not label or not body.strip():
        raise ValueError("Skill 必须包含名称和写作规则")

    checklist = _default_checklist()
    checklist_path = directory / "quality_checklist.yaml"
    if checklist_path.exists():
        parsed = yaml.safe_load(checklist_path.read_text(encoding="utf-8")) or {}
        if not isinstance(parsed, dict):
            raise TypeError("quality_checklist.yaml 必须是对象")
        checklist = parsed
    appendix_path = directory / "appendix.md"
    appendix = appendix_path.read_text(encoding="utf-8").strip() if appendix_path.exists() else _default_appendix()
    names = tuple(name for name in sorted(ALLOWED_SKILL_FILES) if (directory / name).is_file())
    digest = hashlib.sha256()
    for name in names:
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update((directory / name).read_bytes())
    return ResolvedReportSkill(
        id=skill_id,
        label=label,
        description=str(meta.get("description") or "").strip(),
        version=str(meta.get("version") or "1").strip(),
        source=source,
        directory=directory.resolve(),
        body=body.strip(),
        checklist=checklist,
        appendix=appendix,
        checksum=digest.hexdigest(),
        files=names,
    )


def _validate_skill_id(skill_id: str) -> None:
    if not SKILL_ID_PATTERN.fullmatch(skill_id or ""):
        raise ValueError("Skill ID 需使用小写字母、数字、下划线或连字符")


def _default_checklist() -> dict[str, Any]:
    path = BUILTIN_SKILLS_DIR / "default_government" / "quality_checklist.yaml"
    if not path.exists():
        return {}
    parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return parsed if isinstance(parsed, dict) else {}


def _default_appendix() -> str:
    path = BUILTIN_SKILLS_DIR / "default_government" / "appendix.md"
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""
