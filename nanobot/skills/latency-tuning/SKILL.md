---
name: latency-tuning
description: Keep responses fast with local-first command routing.
---

# Latency Tuning

Use this skill when user requests low response times.

## Principles

- Route command-like requests to deterministic local handlers.
- Use short outputs first, then optional deep response.
- Keep model tokens and temperature low for operational tasks.
- Prefer local providers for lower network overhead.

## Fast Patterns

- Status/health/time/file-list should avoid full LLM call.
- Use direct command mode for shell-safe quick tasks.
- Send immediate UI ack over WebSocket to improve perceived latency.

## Verification

- Measure endpoint latency with `Measure-Command`.
- Track p50/p95 for fast path and LLM path separately.
