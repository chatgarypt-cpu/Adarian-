# Snapshot

- 生成时间: 2026-04-14T11:46:14+08:00
- 当前焦点: Analyzer eliminated; focus shifting to Generator and chain schema complexity
- 当前状态: baseline_locked_with_reduced_schema_probe_conclusion
- Baseline 路径: `profiling/output/baseline/v1.2.0_baseline`
- 最新 Run 路径: `profiling/output/baseline/v1.2.0_baseline/runs/run_20260413_184207_613785_27236`

## 状态总览

- 当前 profiling 决策只认 baseline。
- `runs` 是实验记录，不替代 baseline。
- `logs` 是诊断噪声，只有排障时才进入主视图。

## 进展

- 已建立最小控制层：`state.json -> inbox.md -> snapshot.md`
- 已锁定当前可信 baseline：`profiling/output/baseline/v1.2.0_baseline`
- 已完成 80b / 122b 的简版 failure matrix 收口
- P1-A Analyzer probe 已确认：Analyzer 不是当前瓶颈

## 风险提示

- `qwen3-80b-tke` 与 `qwen35-122b-a10b` 当前主要表现为 parse fail，而不是 timeout。
- baseline 仍是 incomplete_profile=True。
- execution_hygiene: timeout_count=2, killed_count=2。

## 最新反馈

- [2026-04-14] Human 本轮控制层保持 MVP，不引入复杂 orchestration framework
- [2026-04-14] Human 当前 profiling 决策只认 `profiling/output/baseline/v1.2.0_baseline`
- [2026-04-14] Codex reduced-schema chain probe 主结论采用 `profiling\output\probes\reduced_schema_chain_probe_20260414_110103`：两模型使用相同 case 集、相同 reduced schema、相同 prompt 模板、相同采样与重试参数；`qwen3-80b-tke` 与 `qwen35-122b-a10b` 均为 `parse_fail_rate=0.000`、`timeout_rate=0.000`、`validator_fail_rate=0.000`。相对 baseline 的 `parse_fail_rate=1.0`，当前唯一可信结论是：两模型本质可用，原始 chain 的主要问题更接近 schema 复杂度触发的输出格式失稳，而非模型能力不足。

## 已确认事实

- P1-A Analyzer probe 状态: confirmed
- P1-A run: `profiling/output/runs/run_20260414_112916_p1a_prompt_probe`
- Analyzer stable across L1/L2/L3
- parse_fail_rate = 0.0
- timeout_rate = 0.0
- validator_fail_rate = 0.0
- no complexity-induced failure observed
- implication: Analyzer is not the bottleneck; shift focus to Generator and chain schema complexity

## Profiling 口径

- baseline: `profiling/output/baseline/*`
- runs: `profiling/output/runs/*`, `profiling/output/final_profile/*/runs/*`
- logs: `profiling/output/concurrent_logs*`, `profiling/output/raw_logs/_worker_tmp*`, `profiling/output/small_profile_run_output.txt`

## Baseline 概览

- 生成时间: 2026-04-13T19:10:50+08:00
- 模型数: 5
- 记录数: 200
- incomplete_profile: True

## Failure Matrix

| 模型 | parse_fail_rate | timeout_rate | validator_fail_rate |
| --- | --- | --- | --- |
| qwen3_80b_tke | 1.000 | 0.000 | 0.000 |
| qwen35_122b_a10b | 1.000 | 0.000 | 0.000 |

## 待决策问题

- 是否在 baseline-only 评审通过后，再提升 final_profile 为下一层决策入口。

## 建议下一步

- P1-A Analyzer profiling 已确认稳定，下一步优先定位 Generator prompt 与 chain schema 复杂度边界。
- 当前 reduced-schema probe 主结论采用 profiling/output/probes/reduced_schema_chain_probe_20260414_110103，不再使用 20260414_105124 作为主证据。
- 将 reduced-schema 结论作为阶段性判断：qwen3-80b-tke 与 qwen35-122b-a10b 本质可用，原始 chain 主要受 schema 复杂度影响。
- 当前决策只认 baseline 目录，不把其他 profiling 产物当主入口。
- 将 profiling/output/runs 和 profiling/output/final_profile/*/runs 视为实验历史，而不是 baseline。
- 将 concurrent_logs、_worker_tmp 和 small_profile_run_output.txt 视为诊断噪声，只有排障时才启用。

## Baseline 摘要附录

```md
# Profiling Summary

- generated_at: 2026-04-13T19:10:50+08:00
- fallback_target: None
- record_count: 200
- model_count: 5

## Overview
- generated_at: 2026-04-13T19:10:50+08:00
- manifest_models: 5
- observed_models: 5
- raw_records: 200
- failed_records: 32
- fallback_target: None

## Stability Counts
- high: 0
- medium: 0
- low: 5

## Execution Hygiene
- subprocess_execution_count: 35
- timeout_count: 2
- killed_count: 2
- kill_failed_count: 0
- worker_exit_abnormal_count: 0

## Model Table

| model_name | simple_latency | generator_latency | review_latency | end_to_end_latency | first_pass_rate | final_pass_rate | avg_retry_count | concurrency_limit | timeout_rate | stability | safe_concurrency | recommended_pool | fallback_target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen3-30b-tke | 1.1258192151506206 | 50.48680900000001 | 5.9589416 | 85.53226120000001 | 0.6666666666666666 | 0.6666666666666666 | 0.6666666666666666 | 5 | 0.0 | low |  |  |  |
| qwen3-32b-tke | 17.037166815152336 | 142.22798033333333 | 4.515460666666667 | 146.74536066666667 | 0.3333333333333333 | 0.3333333333333333 | 0.0 | 5 | 0.05555555555555555 | low |  |  |  |
| qwen3-80b-tke | 0.7280675090944648 | 13.191911222222224 | 0.0 | 26.544248777777778 | 0.0 | 0.0 | 2.0 | 5 | 0.0 | low |  |  |  |
| qwen35-122b-a10b | 2.808091209093673 | 18.405743444444443 | 0.0 | 37.02604733333333 | 0.0 | 0.0 | 2.0 | 5 | 0.0 | low |  |  |  |
| minimax | 4.970025612120728 | 32.573698444444446 | 3.4465693333333336 | 74.25630733333334 | 0.0 | 0.0 | 2.0 | 5 | 0.0 | low |  |  |  |

## Warnings
- none
```

