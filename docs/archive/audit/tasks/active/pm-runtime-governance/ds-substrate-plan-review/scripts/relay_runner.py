"""Long-running subprocess relay for DS Team Substrate Plan Review.
Launches Claude Code with agent team (3 reviewers: Architecture / Execution / Safety-Boundary) + MCP.
Timeout: 1500s. Max turns: 60. Full architecture plan review.
"""
import subprocess, json, sys, threading, time, os
from pathlib import Path
from datetime import datetime

TASK_ID = "pm-runtime-governance/ds-substrate-plan-review"
project_dir = "/Users/gary/项目开发/AdarianMigration/adarian mvp"
dispatch_path = f"audit/tasks/active/{TASK_ID}/dispatch/ds_dispatch.md"
system_prompt_path = f"audit/tasks/active/{TASK_ID}/dispatch/ds_system_prompt.md"
output_dir = Path(project_dir) / "audit/tasks/active" / TASK_ID

HEARTBEAT = output_dir / "relay_logs/relay_heartbeat.txt"
PROGRESS = output_dir / "relay_logs/relay_progress.md"
STDOUT = output_dir / "relay_logs/subprocess_relay_stdout.json"
RESULT = output_dir / "relay_logs/subprocess_relay_result.json"

start_time = time.time()
stage = "init"
last_output = ""

def write_heartbeat():
    elapsed = int(time.time() - start_time)
    HEARTBEAT.write_text(f"{datetime.now().isoformat()} | elapsed={elapsed}s | stage={stage}", encoding="utf-8")

def write_progress():
    elapsed = int(time.time() - start_time)
    ds_report = (output_dir / "ds/ds_substrate_plan_review.md").exists()
    ds_receipt = (output_dir / "ds/ds_receipt.yaml").exists()
    stdout_exists = STDOUT.exists()
    PROGRESS.write_text(
        f"## Relay Progress\n\n"
        f"- **elapsed_seconds**: {elapsed}\n"
        f"- **current_stage**: {stage}\n"
        f"- **stdout_exists**: {stdout_exists} ({STDOUT.stat().st_size if stdout_exists else 0} bytes)\n"
        f"- **ds_report_exists**: {ds_report}\n"
        f"- **ds_receipt_exists**: {ds_receipt}\n",
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
hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
pg_thread = threading.Thread(target=progress_loop, daemon=True)
hb_thread.start()
pg_thread.start()
write_heartbeat()
write_progress()

dispatch_text = (Path(project_dir) / dispatch_path).read_text(encoding="utf-8")

prompt = (
    "下面是完整任务书（通过stdin传入）。严格按任务书执行：PM Runtime Communication Substrate Bootstrap Plan v0.2 架构审查。"
    "必须开启Agent Team（≥3 reviewer：Architecture / Execution-Feasibility / Safety-Boundary）。"
    "必须使用MCP filesystem工具读取全部 6 个输入文件。只读审查，不修改任何文件。"
    "将所有审查结果以完整JSON格式返回在你的result中（不要尝试Write到文件，result必须包含完整报告文本）。"
    "JSON结构：{report_markdown: 完整的中文Markdown审查报告, "
    "receipt_yaml: {task_id, review_type, team_mode_used, mcp_used, scope_compliance, "
    "acceptance_verdict, findings: {P0: [], P1: [], P2: [], P3: []}, "
    "process_issues: [], blockers: [], "
    "four_failures_prevention_assessment: {role_boundary_violation, artifact_path_missing, task_domain_routing_error, mcp_tool_context_gap}, "
    "anti_drift_skill_relationship_assessment, "
    "recommended_next_action: [], "
    "report_path, receipt_path}}"
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

try:
    stage = "claude_running"
    write_heartbeat()
    
    result = subprocess.run(cmd, input=dispatch_text, capture_output=True,
                            text=True, cwd=project_dir, timeout=1500)
    done_flag[0] = True
    stage = "claude_completed"
    elapsed = int(time.time() - start_time)
    last_output = f"exit={result.returncode} stdout_len={len(result.stdout)}"
    STDOUT.write_text(result.stdout, encoding="utf-8")
    
    if result.returncode == 0:
        claude_result = json.loads(result.stdout)
        stage = "parsing_result"
        
        RESULT.write_text(json.dumps({
            "exit_code": 0, "subtype": claude_result.get("subtype"),
            "num_turns": claude_result.get("num_turns"),
            "stop_reason": claude_result.get("stop_reason"),
            "permission_denials_count": len(claude_result.get("permission_denials", [])),
            "elapsed_seconds": elapsed,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # Extract from permission_denials if write was attempted
        inner = claude_result.get("result", "")
        report_written = False
        receipt_written = False
        
        # Path 1: permission_denial payload recovery (Write tool denied)
        # Sort by content length descending — report > receipt
        denial_candidates = []
        for pd in claude_result.get("permission_denials", []):
            if pd["tool_name"] == "mcp__filesystem__write_file":
                content = pd.get("tool_input", {}).get("content", "")
                if content and len(content) > 500:
                    denial_candidates.append(content)
        denial_candidates.sort(key=len, reverse=True)
        
        if len(denial_candidates) >= 1:
            # Longest = report (>3000 chars typically)
            (output_dir / "ds/ds_substrate_plan_review.md").write_text(denial_candidates[0], encoding="utf-8")
            stage = "ds_report_written_from_denial"
            report_written = True
        if len(denial_candidates) >= 2:
            # Second longest = receipt
            (output_dir / "ds/ds_receipt.yaml").write_text(denial_candidates[1], encoding="utf-8")
            receipt_written = True
        
        # Path 2: JSON code block extraction from result field
        if not report_written and inner:
            try:
                import re
                match = re.search(r'```json\s*\n(.*?)\n```', inner, re.DOTALL)
                json_str = match.group(1) if match else inner[inner.find('{'):]
                inner_json = json.loads(json_str)
                if "report_markdown" in inner_json:
                    (output_dir / "ds/ds_substrate_plan_review.md").write_text(inner_json["report_markdown"], encoding="utf-8")
                    report_written = True
                    stage = "ds_report_written"
                if "receipt_yaml" in inner_json:
                    import yaml
                    (output_dir / "ds/ds_receipt.yaml").write_text(
                        yaml.dump(inner_json["receipt_yaml"], allow_unicode=True, default_flow_style=False),
                        encoding="utf-8")
                    receipt_written = True
                    stage = "ds_receipt_written"
            except Exception as e:
                (output_dir / "relay_logs/ds_raw_inner.txt").write_text(inner, encoding="utf-8")
                last_output += f" | parse_err: {e}"
        
        if report_written or receipt_written:
            stage = "pass"
        else:
            stage = "pass_no_files_written"
            (output_dir / "relay_logs/ds_raw_inner.txt").write_text(inner, encoding="utf-8")
    else:
        stage = "fail"
        RESULT.write_text(json.dumps({
            "exit_code": result.returncode,
            "stderr_tail": result.stderr[-500:] if result.stderr else "",
        }, ensure_ascii=False), encoding="utf-8")

except subprocess.TimeoutExpired:
    done_flag[0] = True; stage = "timeout"
    RESULT.write_text(json.dumps({"error": "timeout", "elapsed_seconds": int(time.time() - start_time)}, ensure_ascii=False), encoding="utf-8")
except Exception as e:
    done_flag[0] = True; stage = "error"
    RESULT.write_text(json.dumps({"error": str(e)}, ensure_ascii=False), encoding="utf-8")

write_heartbeat()
write_progress()
print(f"DONE stage={stage} elapsed={int(time.time()-start_time)}s", flush=True)
