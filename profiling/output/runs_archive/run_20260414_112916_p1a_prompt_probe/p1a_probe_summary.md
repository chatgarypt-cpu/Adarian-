# P1-A Prompt Probe Summary

- generated_at: 2026-04-14T11:39:56+08:00
- baseline_path: `profiling/output/baseline/v1.2.0_baseline`
- run_dir: `profiling/output/runs/run_20260414_112916_p1a_prompt_probe`

## Model x Level

| model | level | status | parse_fail_rate | timeout_rate | validator_fail_rate | completeness | scale_range | scale_stddev |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen3-80b-tke | L1 | stable | 0.000 | 0.000 | 0.000 | 1.000 | 0.200 | 0.082 |
| qwen3-80b-tke | L2 | stable | 0.000 | 0.000 | 0.000 | 1.000 | 0.100 | 0.047 |
| qwen3-80b-tke | L3 | stable | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 |
| qwen35-122b-a10b | L1 | stable | 0.000 | 0.000 | 0.000 | 1.000 | 0.150 | 0.071 |
| qwen35-122b-a10b | L2 | stable | 0.000 | 0.000 | 0.000 | 1.000 | 0.200 | 0.082 |
| qwen35-122b-a10b | L3 | stable | 0.000 | 0.000 | 0.000 | 1.000 | 0.250 | 0.103 |
| qwen3-32b-tke | L1 | stable | 0.000 | 0.000 | 0.000 | 1.000 | 0.100 | 0.047 |
| qwen3-32b-tke | L2 | stable | 0.000 | 0.000 | 0.000 | 1.000 | 0.100 | 0.041 |
| qwen3-32b-tke | L3 | stable | 0.000 | 0.000 | 0.000 | 1.000 | 0.100 | 0.047 |
| minimax | L1 | stable | 0.000 | 0.000 | 0.000 | 1.000 | 0.150 | 0.062 |
| minimax | L2 | stable | 0.000 | 0.000 | 0.000 | 1.000 | 0.300 | 0.131 |
| minimax | L3 | stable | 0.000 | 0.000 | 0.000 | 1.000 | 0.050 | 0.024 |

## Findings

- qwen3-80b-tke 在 L1/L2/L3 下都稳定。
- qwen35-122b-a10b 在 L1/L2/L3 下都稳定。
- qwen3-32b-tke 在 L1/L2/L3 下都稳定。
- minimax 在 L1/L2/L3 下都稳定。
