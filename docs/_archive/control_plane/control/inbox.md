# Inbox - 反馈入口

本目录是本轮最小控制层。机器可读入口是 `control/state.json`，人类决策视图由 `scripts/generate_snapshot.py` 生成到 `control/snapshot.md`。

## 当前 Baseline

- 唯一可信入口：`profiling/output/baseline/v1.2.0_baseline`
- 当前对应 run：`profiling/output/baseline/v1.2.0_baseline/runs/run_20260413_184207_613785_27236`
- 不要把 `profiling/output/profile_summary.md` 或 `profiling/output/model_profiles.json` 当成主决策入口

## 当前风险

- `qwen3-80b-tke`：`parse_fail_rate=1.0`，`timeout_rate=0.0`，`validator_fail_rate=0.0`
- `qwen35-122b-a10b`：`parse_fail_rate=1.0`，`timeout_rate=0.0`，`validator_fail_rate=0.0`
- 当前证据更支持“chain 输出格式不稳定”，而不是 timeout 或 validator 过严

## 待处理

- [2026-04-14] Codex P1-A prompt-aware profiling 完成；qwen3-80b-tke 在 L1/L2/L3 下都稳定。；qwen35-122b-a10b 在 L1/L2/L3 下都稳定。；qwen3-32b-tke 在 L1/L2/L3 下都稳定。；minimax 在 L1/L2/L3 下都稳定。；产物目录：`profiling/output/runs/run_20260414_112916_p1a_prompt_probe`

- [2026-04-14] Human 是否在 baseline 评审通过后再提升 `final_profile` 为下一层决策入口

## 已采纳

- [2026-04-14] Human 本轮控制层保持 MVP，不引入复杂 orchestration framework
- [2026-04-14] Human 当前 profiling 决策只认 `profiling/output/baseline/v1.2.0_baseline`
- [2026-04-14] Codex reduced-schema chain probe 主结论采用 `profiling\output\probes\reduced_schema_chain_probe_20260414_110103`：两模型使用相同 case 集、相同 reduced schema、相同 prompt 模板、相同采样与重试参数；`qwen3-80b-tke` 与 `qwen35-122b-a10b` 均为 `parse_fail_rate=0.000`、`timeout_rate=0.000`、`validator_fail_rate=0.000`。相对 baseline 的 `parse_fail_rate=1.0`，当前唯一可信结论是：两模型本质可用，原始 chain 的主要问题更接近 schema 复杂度触发的输出格式失稳，而非模型能力不足。

## 丢弃

- [2026-04-14] Codex 本轮不做 repo 全量清理或核心 phase1-4 改造
- [2026-04-14] Codex `profiling\output\probes\reduced_schema_chain_probe_20260414_105124` 标记为 superseded / diagnostics：输入配置与主结论 run 一致，但该次产物包含重试记录，`qwen3-80b-tke` 在 `case_1_mid_scale_mid_controversy` 上出现两次 `RuntimeError: LLM 调用失败，已重试 3 次: Request timed out.`，`qwen35-122b-a10b` 在同 case 上出现一次首轮 JSON parse failure 后重试成功；因此该目录反映的是瞬时运行波动，不应作为 reduced-schema 可用性的主结论。
