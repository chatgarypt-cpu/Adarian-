"""Codex implementation relay for PM Runtime Communication Substrate MVP.
Launches Codex with sandbox workspace-write. Timeout: 1800s.
"""
import subprocess, json, os, time, threading
from pathlib import Path
from datetime import datetime

TASK_ID = "pm-runtime-governance/communication-substrate-mvp"
project_dir = "/Users/gary/项目开发/AdarianMigration/adarian mvp"
taskbook_path = "docs/iterations/v0.1.0-pm-runtime-communication-substrate-mvp.md"
output_dir = Path(project_dir) / "audit/tasks/active" / TASK_ID

HEARTBEAT = output_dir / "relay_logs/relay_heartbeat_codex.txt"
PROGRESS = output_dir / "relay_logs/relay_progress_codex.md"
STDOUT = output_dir / "relay_logs/codex_stdout.jsonl"
RESULT = output_dir / "relay_logs/codex_result.json"
STDERR = output_dir / "relay_logs/codex_stderr.log"

start_time = time.time()
stage = "init"

def write_heartbeat():
    elapsed = int(time.time() - start_time)
    HEARTBEAT.write_text(f"{datetime.now().isoformat()} | elapsed={elapsed}s | stage={stage}", encoding="utf-8")

def write_progress():
    elapsed = int(time.time() - start_time)
    stdout_exists = STDOUT.exists()
    PROGRESS.write_text(
        f"## Codex Relay Progress\n\n"
        f"- **elapsed_seconds**: {elapsed}\n"
        f"- **current_stage**: {stage}\n"
        f"- **stdout_exists**: {stdout_exists} ({STDOUT.stat().st_size if stdout_exists else 0} bytes)\n",
        encoding="utf-8"
    )

done_flag = [False]
hb_thread = threading.Thread(target=lambda: [write_heartbeat(), time.sleep(30)][0] if not done_flag[0] else None, daemon=True)

# Actually let's do a proper heartbeat loop
def heartbeat_loop():
    while not done_flag[0]:
        write_heartbeat()
        time.sleep(30)

def progress_loop():
    while not done_flag[0]:
        time.sleep(120)
        if not done_flag[0]:
            write_progress()

hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
pg_thread = threading.Thread(target=progress_loop, daemon=True)
hb_thread.start()
pg_thread.start()
write_heartbeat()
write_progress()

# Read taskbook
taskbook_text = (Path(project_dir) / taskbook_path).read_text(encoding="utf-8")

prompt = (
    "你是 Codex，Claude Code 的代码实现 Agent。下面是你的实现任务书。"
    "严格按任务书执行 PM Runtime Communication Substrate MVP 实现。"
    "先通读完整任务书，然后按 §8 Required Modules and Behavior 实现所有模块。"
    "实现完成后运行 §19 Required Checks。"
    "将 receipt 写入 codex/codex_receipt.yaml，将 handoff 写入 codex/codex_handoff.md。"
    "输出路径：audit/tasks/active/pm-runtime-governance/communication-substrate-mvp/codex/"
    "不要修改 forbidden files。不要 git commit。不要 claim closeout。"
)

cmd = [
    "codex", "exec",
    "--sandbox", "workspace-write",
    "--skip-git-repo-check",
    "--add-dir", project_dir,
    "--json",
    prompt,
]

stage = "launching_codex"
write_heartbeat()

try:
    stage = "codex_running"
    write_heartbeat()

    result = subprocess.run(cmd, capture_output=True,
                            text=True, cwd=project_dir, timeout=1800)
    done_flag[0] = True
    stage = "codex_completed"
    elapsed = int(time.time() - start_time)

    STDOUT.write_text(result.stdout, encoding="utf-8")
    if result.stderr:
        STDERR.write_text(result.stderr, encoding="utf-8")

    RESULT.write_text(json.dumps({
        "exit_code": result.returncode,
        "elapsed_seconds": elapsed,
        "stdout_len": len(result.stdout),
        "stderr_len": len(result.stderr),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    stage = "completed" if result.returncode == 0 else "failed"

except subprocess.TimeoutExpired:
    done_flag[0] = True; stage = "timeout"
    RESULT.write_text(json.dumps({"error": "timeout", "elapsed_seconds": int(time.time() - start_time)}, ensure_ascii=False), encoding="utf-8")
except Exception as e:
    done_flag[0] = True; stage = "error"
    RESULT.write_text(json.dumps({"error": str(e)}, ensure_ascii=False), encoding="utf-8")

write_heartbeat()
write_progress()
print(f"DONE stage={stage} elapsed={int(time.time()-start_time)}s", flush=True)
