# Frontend Runtime QA - 2026-06-26

## Scope

- Target: `http://127.0.0.1:9789`
- Build: v1.5.0b frontend served by Flask static dist.
- Method: browser interaction plus API smoke tests.

## Fixed In This Pass

1. Model discovery for the `.env` gateway now supports internal network URL variants.
   - The API tries internal portless discovery URLs and configured URLs in parallel.
   - Verified `/api/model-gateways/env-default/discover-models` returns 27 models.

2. Direct route opening no longer gets overwritten by the last saved route.
   - `/models` remains `/models` instead of being replaced by `/history`.

3. Mobile/narrow viewport sidebar no longer overlays model page actions.
   - The sidebar is no longer sticky under the mobile breakpoint.
   - Verified clicking `识别服务模型` stays on `/models`.

4. Model page all-select control was restyled.
   - Replaced the pill-like checkbox with a compact square check control.
   - Verified click updates from 2 selected models to 27 selected models.

5. Run and review empty states no longer hide actionable content.
   - `/run` now still shows `启动真实推演`, `刷新状态`, and the empty hint.
   - `/review` now still shows `读取审查结果` and empty evidence hints.

## Verified

- `GET /api/ping` returns `{"status":"ok","version":"1.5.0b"}`.
- `POST /api/model-gateways/env-default/discover-models` returns 27 models, first observed model `qwen3-32b-tke`.
- Model page renders `已加载 27 个模型`, default selects 2 models, and enables model health detection.
- Health check for the default 2 selected models completes and reports `2 可用 / 0 失败 / 0 超时`.
- Seed page `保存事件材料` succeeds and shows `事件材料已保存`.
- Config page `保存配置` succeeds and keeps the configuration preview visible.
- Settings page loads and `保存设置` succeeds without an error state.
- Run/review/report/history/settings routes open at the requested URL.

## Deferred / Next Iteration

- Full `启动真实推演` E2E was not auto-triggered because it starts real batch execution and consumes model/runtime resources.
- Report generation remains disabled until an active batch exists; this is expected for v1.5.0b.
- History task reuse, file material upload, cancel/retry, and report download/detail flows remain future capabilities.
- Health-checking all 27 discovered models was not run automatically; the UI supports it, but it can generate a burst of real model requests.
