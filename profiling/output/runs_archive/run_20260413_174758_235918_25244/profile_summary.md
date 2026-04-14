# Profiling Summary

- generated_at: 2026-04-13T17:48:39+08:00
- fallback_target: qwen3-30b-tke
- record_count: 34
- model_count: 1

## Overview
- generated_at: 2026-04-13T17:48:39+08:00
- manifest_models: 1
- observed_models: 1
- raw_records: 34
- failed_records: 1
- fallback_target: qwen3-30b-tke

## Pool Counts
- fast: 0
- heavy: 0
- fragile: 1

## Stability Counts
- high: 0
- medium: 0
- low: 1

## Execution Hygiene
- subprocess_execution_count: 1
- timeout_count: 1
- killed_count: 1
- kill_failed_count: 0
- worker_exit_abnormal_count: 0

## Model Table

| model_name | simple_latency | generator_latency | review_latency | end_to_end_latency | first_pass_rate | final_pass_rate | avg_retry_count | concurrency_limit | timeout_rate | stability | recommended_pool | fallback_target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen3-30b-tke | 1.818812409093053 | 15.0 | 0.0 | 15.0 | 0.0 | 0.0 | 0.0 | 5 | 0.029411764705882353 | low | fragile | qwen3-30b-tke |

## Warnings
- none
