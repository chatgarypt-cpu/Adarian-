"""Long-running subprocess relay for DS Team Governance Assets Review.
Launches Claude Code with agent team (5 reviewers) + MCP.
Timeout: 1500s. Max turns: 60. Team mode REQUIRED.
"""
import subprocess, json, sys, threading, time, os
from pathlib import Path
from datetime import datetime

TASK_ID = "control-agent-governance/assets-review"
project_dir = "/Users/gary/项目开发/AdarianMigration/adarian mvp"
dispatch_path = f"audit/tasks/active/{TASK_ID}/dispatch/ds_dispatch.md"
system_prompt_path = f"audit/tasks/active/{TASK_ID}/dispatch/ds_system_prompt.md"
output_dir = Path(project_dir) / "audit/tasks/active" / TASK_ID

HEARTBEAT = output_dir / "relay_logs/relay_heartbeat.txt"
PROGRESS = output_dir / "relay_logs/relay_progress.md"
STDOUT = output_dir / "relay_logs/subprocess_relay_stdout.json"
RESULT = output_dir / "relay_logs/subprocess_relay_result.json"

start_time = time.time()
last_progress_time = start_time
stage = "init"
last_output = ""

def write_heartbeat():
    elapsed = int(time.time() - start_time)
    HEARTBEAT.write_text(f"{datetime.now().isoformat()} | elapsed={elapsed}s | stage={stage}", encoding="utf-8")

def write_progress():
    global last_progress_time
    elapsed = int(time.time() - start_time)
    last_progress_time = time.time()
    ds_report = (output_dir / "ds/ds_governance_assets_review.md").exists()
    ds_receipt = (output_dir / "ds/ds_receipt.yaml").exists()
    stdout_exists = STDOUT.exists()
    PROGRESS.write_text(
        f"## Relay Progress\n\n"
        f"- **current_time**: {datetime.now().isoformat()}\n"
        f"- **elapsed_seconds**: {elapsed}\n"
        f"- **current_stage**: {stage}\n"
        f"- **last_observed_output**: {last_output[:200]}\n"
        f"- **stdout_exists**: {stdout_exists} ({STDOUT.stat().st_size if stdout_exists else 0} bytes)\n"
        f"- **ds_report_exists**: {ds_report}\n"
        f"- **ds_receipt_exists**: {ds_receipt}\n"
        f"- **possible_blocker**: none observed\n"
        f"- **next_expected_event**: Claude Code completion or timeout\n",
        encoding="utf-8"
    )

def heartbeat_loop():
    while not done_flag[0]:
        write_heartbeat()
        time.sleep(30)

def progress_loop():
    while not done_flag[0]:
        time.sleep(120)
        if not done_flag[0]:
            write_progress()

done_flag = [False]

# Start monitoring threads
hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
pg_thread = threading.Thread(target=progress_loop, daemon=True)
hb_thread.start()
pg_thread.start()

# Initial state
write_heartbeat()
write_progress()

# Read dispatch
dispatch_text = (Path(project_dir) / dispatch_path).read_text(encoding="utf-8")

prompt = (
    "下面是完整任务书（通过stdin传入）。严格按任务书执行：Control Agent Governance Assets 一致性审查 + System Prompt 瘦身审查。"
    "必须开启Agent Team（≥5 reviewer subagent：Authority Alignment / System Prompt Minimalism / "
    "Control Agent Behavior / Hermes-first Workflow / Template & Asset Mode）。"
    "必须使用MCP filesystem工具读取 4 个治理资产文件。只读审计，不修改任何文件。"
    "因为只能使用Read工具，请将所有审计结果以完整JSON格式返回在你的result中。"
    "JSON结构：{report_markdown: 完整的中文Markdown审查报告文本, "
    "receipt_yaml: {task_id, review_id, team_mode_used, mcp_used, "
    "reviewed_files: [], authority_alignment, compact_alignment, role_card_alignment, "
    "system_prompt_readiness, system_prompt_slimming_assessment, hermes_first_alignment, "
    "template_asset_mode_alignment, format_issues: [], "
    "findings: [{id, severity, location, issue, recommendation}], "
    "recommended_layering: {system_prompt_should_keep: [], move_to_compact: [], "
    "move_to_control_agent_role_card: [], move_to_workflow_core: [], delete_or_merge: []}, "
    "recommended_system_prompt_target: {target_length, required_sections: [], optional_sections_to_remove: []}, "
    "process_issues: [], blockers: [], known_issues: [], acceptance_verdict, report_path}}"
)

cmd = [
    "claude", "-p", prompt,
    "--allowedTools", "Read",
    "--append-system-prompt-file", system_prompt_path,
    "--max-turns", "60",
    "--output-format", "json",
]

stage = "launching_claude"
write_heartbeat()
last_output = f"cmd: {' '.join(cmd[:3])}..."

try:
    stage = "claude_running"
    write_heartbeat()
    
    result = subprocess.run(
        cmd,
        input=dispatch_text,
        capture_output=True,
        text=True,
        cwd=project_dir,
        timeout=1500,
    )
    
    done_flag[0] = True
    stage = "claude_completed"
    elapsed = int(time.time() - start_time)
    last_output = f"exit={result.returncode} stdout_len={len(result.stdout)}"

    # Save stdout
    STDOUT.write_text(result.stdout, encoding="utf-8")
    
    if result.returncode == 0:
        claude_result = json.loads(result.stdout)
        stage = "parsing_result"
        
        summary = {
            "exit_code": 0, "subtype": claude_result.get("subtype"),
            "session_id": claude_result.get("session_id"),
            "num_turns": claude_result.get("num_turns"),
            "stop_reason": claude_result.get("stop_reason"),
            "permission_denials_count": len(claude_result.get("permission_denials", [])),
            "total_cost_usd": claude_result.get("total_cost_usd"),
            "duration_ms": claude_result.get("duration_ms"),
            "elapsed_seconds": elapsed,
        }
        RESULT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        
        inner = claude_result.get("result", "")
        try:
            # Extract JSON from ```json code block if present
            import re
            match = re.search(r'```json\s*\n(.*?)\n```', inner, re.DOTALL)
            json_str = match.group(1) if match else inner[inner.find('{'):]
            inner_json = json.loads(json_str)
            if "report_markdown" in inner_json:
                (output_dir / "ds/ds_governance_assets_review.md").write_text(inner_json["report_markdown"], encoding="utf-8")
                stage = "ds_report_written"
            if "receipt_yaml" in inner_json:
                import yaml
                (output_dir / "ds/ds_receipt.yaml").write_text(
                    yaml.dump(inner_json["receipt_yaml"], allow_unicode=True, default_flow_style=False),
                    encoding="utf-8")
                stage = "ds_receipt_written"
        except Exception as e:
            (output_dir / "relay_logs/ds_raw_inner.txt").write_text(inner, encoding="utf-8")
            last_output += f" | parse_err: {e}"
        
        stage = "pass"
    else:
        stage = "fail"
        RESULT.write_text(json.dumps({"exit_code": result.returncode, "stderr_tail": result.stderr[-500:]}, ensure_ascii=False), encoding="utf-8")
        last_output += f" | stderr: {result.stderr[-200:]}"

except subprocess.TimeoutExpired:
    done_flag[0] = True
    stage = "timeout"
    last_output = "subprocess timeout after 1500s"
    RESULT.write_text(json.dumps({"error": "timeout", "timeout_seconds": 1500}, ensure_ascii=False), encoding="utf-8")
except Exception as e:
    done_flag[0] = True
    stage = "error"
    last_output = f"{type(e).__name__}: {e}"
    RESULT.write_text(json.dumps({"error": str(e), "type": type(e).__name__}, ensure_ascii=False), encoding="utf-8")

write_heartbeat()
write_progress()
print(f"DONE stage={stage} elapsed={int(time.time()-start_time)}s output={last_output[:200]}", flush=True)
