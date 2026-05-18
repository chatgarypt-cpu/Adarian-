# DS Team Dispatch — Workflow Governance Path Inventory R0

**task_id**: workflow-governance-path-inventory-r0
**task_type**: Path Inventory (READ-ONLY)
**dispatched_by**: Hermes-PM
**date**: 2026-05-18

---

## 0. Objective

Perform a READ-ONLY path inventory of all workflow / skill / hook / template / protocol / agent instruction files in the Adarian MVP repository. Output ONLY path facts. No governance judgments, no patch plans, no v3.1 text.

**The sole purpose**: give Owner-Control a complete path map for section-by-section workflow_core.md v3.1 revision.

---

## 1. Scope — 13 File Categories

For each category, scan the repository and list every matching file.

### Category 1 — workflow_core.md
- Find the exact path of `workflow_core.md`
- Note any backup copies or historical versions

### Category 2 — Workflow Authority Files
- Any file claiming "primary workflow authority" or "workflow constitution" status
- Any file defining role division, pipeline, gates

### Category 3 — docs/skills/ All Files
- List every file under `docs/skills/`
- For each, note if it's workflow-related

### Category 4 — DS Team Audit / Review Files
- DS pre-audit / verify / accept skill files
- DS review scope or agent team configuration files
- `.claude/SKILLS.md`

### Category 5 — Codex Execution / Handoff / Receipt Files
- Codex execution guard / delivery / handoff files
- Any receipt template files

### Category 6 — Iteration Document Templates
- All `_template*.md` files under `docs/iterations/`
- Note any older versions

### Category 7 — TASK_LOG / CHANGELOG
- `docs/iterations/TASK_LOG.md`
- `docs/iterations/CHANGELOG.md`

### Category 8 — Hook Config / Hook Policy Files
- `.claude/settings.json`
- `.claude/settings.local.json`
- Check for standalone hook policy documents

### Category 9 — Hermes / Relay / Dispatch Files
- Search entire repo for files containing "hermes", "agentops", "relay", "dispatch", "handoff"
- Check `audit/hermes_tasks/` directory
- Check for files outside project tree if referenced (e.g., `~/.hermes/skills/adarian/`)

### Category 10 — Product-side Protocol Files
- `audit/product_side_structured_delivery_protocol_v0.1_revised.md`
- Any other product-side protocol or template files

### Category 11 — Closeout / Acceptance / Handoff Templates
- Closeout record templates
- Acceptance report templates
- Handoff receipt format definitions

### Category 12 — Agent Instruction Files
- `CLAUDE.md` (project root)
- `.claude/SKILLS.md`
- Check for `AGENTS.md` or Codex-specific instructions
- Check `.codex/` directory if it exists

### Category 13 — Missing Referenced Files
- Scan workflow_core.md, CLAUDE.md, ds_*.md for file paths they reference
- Report any that do NOT actually exist on disk
- Example: if `workflow_core.md §8.3` says "报告存放 audit/phase1大版本审计/" but no example exists

---

## 2. Output Format Per File

For EACH file found, output:

```
| path | exists | tracked_status | file_type | likely_role | notes |
```

Fields:
- **path**: relative path from project root
- **exists**: `true` / `false` (false only for Category 13 missing files)
- **tracked_status**: `tracked` (in git) / `untracked` / `unknown` (check with `git ls-files`)
- **file_type**: one of `constitution`, `skill`, `hook`, `template`, `protocol`, `log`, `audit`, `agent_instruction`, `historical`, `unknown`
- **likely_role**: one-sentence description of what this file does
- **notes**: mark suspicions (e.g., "疑似过时", "与 X 内容重复", "命名不一致") but do NOT make decisions

---

## 3. Subagent Division (MANDATORY)

**Reviewer A — docs/skills/ + templates + hooks + agent instructions:**
- Categories 2, 3, 6, 8, 12
- Scan `docs/skills/`, `docs/iterations/_template*.md`, `.claude/`, `CLAUDE.md`

**Reviewer B — audit + protocol + dispatch + missing files:**
- Categories 4, 5, 9, 10, 11, 13
- Scan `audit/`, search for hermes/relay/dispatch/handoff references, cross-reference file paths

**Lead Reviewer (you) — synthesis + Category 1 + Category 7:**
- Locate `workflow_core.md`, `TASK_LOG.md`, `CHANGELOG.md`
- Merge Reviewer A + B results
- Produce final `ds_audit.md` and `ds_receipt.yaml`

If subagent spawning fails: HALT immediately. Do NOT proceed solo.

---

## 4. Output Files

### ds_audit.md (Chinese Markdown)

Structure:
```markdown
# DS Team 工作流治理路径摸底报告

## 1. 扫描摘要
- 扫描时间
- 文件总数
- MCP 使用情况
- Agent Team 使用情况

## 2. 路径清单
### 2.1 workflow_core.md
| path | exists | tracked | type | role | notes |
|------|--------|---------|------|------|-------|

### 2.2 Workflow Authority 文件
...

### 2.3 docs/skills/ 全部文件
...

(repeat for all 13 categories)

## 3. 缺失引用文件
...

## 4. 审查元数据
- review_id
- team_mode_used
- mcp_used
```

### ds_receipt.yaml

```yaml
task_id: workflow-governance-path-inventory-r0
review_id: audit-path-inventory-2026-05-18-01
team_mode_used: true/false
mcp_used: true/false
verdict: PATH_INVENTORY_COMPLETE | NEEDS_MORE_EVIDENCE | HOLD | FAIL
report_path: audit/hermes_tasks/workflow-governance-path-inventory-r0/ds_audit.md
workflow_core_path: <path>
assets_found_count: <number>
missing_referenced_files: []
constitution_files: []
skill_files: []
hook_files: []
template_files: []
protocol_files: []
agent_instruction_files: []
log_files: []
historical_files: []
unknown_files: []
blockers: []
recommended_next_action: "将路径清单交给 Owner-Control，用于 workflow_core.md v3.1 分节修订。"
```

**recommended_next_action must be exactly the string above. Do not suggest Codex execution, file modification, or v3.1 text writing.**

---

## 5. Boundaries

**DO:**
- List file paths and basic facts
- Use MCP filesystem tools
- Use multi-reviewer subagents
- Report missing referenced files

**DO NOT:**
- Make governance judgments ("this should be archived")
- Suggest patch plans
- Write workflow_core.md v3.1 text
- Call Codex
- Modify any file
- Auto-promote findings to tasks
