---
name: batch_allocate
description: "Allocate multiple resources in one request"
---

# Batch Allocate

## Trigger

User says "allocate GPUs and a dataset", "I need 4 A100s and 2 licenses", "set up my training environment", "batch allocation".

## Flow

1. Gather the list of resources the user needs:
   - Each item: resource (kind/name), amount, duration, purpose
2. For each resource, run estimate_cost logic to show total budget:
   - Item-by-item breakdown
   - Grand total
3. Ask user to confirm the batch
4. Execute allocations sequentially:
   - `one alloc create --resource <kind/name> --amount <n> [--duration <d>]` for each
   - If any fails (409 capacity / 403 quota), report which failed and which succeeded
   - Do NOT rollback succeeded allocations automatically — let user decide
5. Present summary:
   - Succeeded: allocation names, amounts, costs
   - Failed: resource, reason, suggested action

## API

```bash
# Each allocation is a separate CLI call
one alloc create --resource bms/gpu-farm-01 --amount 4 --unit A100-hour --duration 2h --purpose "training"
one alloc create --resource ds/imagenet-2024 --amount 1 --unit access-license --purpose "training"
one alloc create --resource lic/jetbrains-team-2026 --amount 1 --unit seat --purpose "dev tools"
```

## Notes

- OneSystem has no batch API — each allocation is an independent request
- Partial failure is expected (some resources may have capacity, others not)
- User should be informed clearly which allocations succeeded vs failed
- For rollback, user can manually release succeeded allocations
