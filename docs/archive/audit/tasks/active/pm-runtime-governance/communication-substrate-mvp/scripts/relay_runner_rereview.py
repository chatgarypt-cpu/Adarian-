"""Long-running subprocess relay for DS Team Codex Taskbook v0.2 Re-Review.
Quick re-review. Timeout: 900s. Max turns: 40.
"""
import subprocess, json, sys, threading, time, os
from pathlib import Path
from datetime import datetime

TASK_ID = "pm-runtime-governance/communication-substrate-mvp"
project_dir = "/Users/gary/项目开发/AdarianMigration/adarian mvp"
dispatch_path = f"audit/tasks/active/{TASK_ID}/dispatch/ds_rereview_dispatch.md"
system_prompt_path = f"audit/tasks/active/{TASK_ID}/dispatch/ds_rereview_system_prompt.md"
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
    ds_report = (output_dir / "ds/ds_codex_taskbook_rereview.md").exists()
    ds_receipt = (output_dir / "ds/ds_rereview_receipt.yaml").exists()
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
    "下面是完整任务书（通过stdin传入）。严格按任务书执行：PM Runtime Communication Substrate MVP Codex Taskbook v0.2 快速复审。"
    "这是复审，不是重新审计。重点：验证 9 P0 和 8 P1 是否全部修复。"
    "必须开启Agent Team（≥2 reviewer：P0-Repair-Verification / P1-Repair-Verification）。"
    "必须使用MCP filesystem工具读取全部输入文件。只读审查，不修改任何文件。"
    "将所有审查结果以完整JSON格式返回在你的result中（不要尝试Write到文件，result必须包含完整报告文本）。"
    "JSON结构：{report_markdown: 完整的中文Markdown复审报告, "
    "receipt_yaml: {task_id, review_type, team_mode_used, mcp_used, "
    "scope_compliance, acceptance_verdict, codex_readiness, "
    "p0_status: {all_addressed, unaddressed: [], details: []}, "
    "p1_status: {all_addressed, unaddressed: [], details: []}, "
    "remaining_issues: {P0: [], P1: [], P2: [], P3: []}, "
    "p3_concurrency_assessment: {acceptable_for_mvp, recommendation}, "
    "p3_task_config_path_assessment: {acceptable_for_mvp, needs_clarification, recommendation}, "
    "process_issues: [], blockers: [], recommended_next_action: [], "
    "report_path, receipt_path}}"
)

cmd = [
    "claude", "-p", prompt,
    "--allowedTools", "Read",
    "--append-system-prompt-file", system_prompt_path,
    "--max-turns", "40",
    "--output-format", "json",
]

stage = "launching_claude"
write_heartbeat()

try:
    stage = "claude_running"
    write_heartbeat()

    result = subprocess.run(cmd, input=dispatch_text, capture_output=True,
                            text=True, cwd=project_dir, timeout=900)
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

        inner = claude_result.get("result", "")
        report_written = False
        receipt_written = False

        denial_candidates = []
        for pd in claude_result.get("permission_denials", []):
            if pd["tool_name"] == "mcp__filesystem__write_file":
                content = pd.get("tool_input", {}).get("content", "")
                if content and len(content) > 500:
                    denial_candidates.append(content)
        denial_candidates.sort(key=len, reverse=True)

        if len(denial_candidates) >= 1:
            (output_dir / "ds/ds_codex_taskbook_rereview.md").write_text(denial_candidates[0], encoding="utf-8")
            stage = "ds_report_written_from_denial"
            report_written = True
        if len(denial_candidates) >= 2:
            (output_dir / "ds/ds_rereview_receipt.yaml").write_text(denial_candidates[1], encoding="utf-8")
            receipt_written = True

        if not report_written and inner:
            try:
                import re
                match = re.search(r'```json\s*\n(.*?)\n```', inner, re.DOTALL)
                json_str = match.group(1) if match else inner[inner.find('{'):]
                inner_json = json.loads(json_str)
                if "report_markdown" in inner_json:
                    (output_dir / "ds/ds_codex_taskbook_rereview.md").write_text(inner_json["report_markdown"], encoding="utf-8")
                    report_written = True
                    stage = "ds_report_written"
                if "receipt_yaml" in inner_json:
                    import yaml
                    (output_dir / "ds/ds_rereview_receipt.yaml").write_text(
                        yaml.dump(inner_json["receipt_yaml"], allow_unicode=True, default_flow_style=False),
                        encoding="utf-8")
                    receipt_written = True
                    stage = "ds_receipt_written"
            except Exception as e:
                (output_dir / "relay_logs/ds_raw_inner.txt").write_text(inner, encoding="utf-8")
                last_output += f" | parse_err: {e}"

        stage = "pass" if (report_written or receipt_written) else "pass_no_files_written"
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
