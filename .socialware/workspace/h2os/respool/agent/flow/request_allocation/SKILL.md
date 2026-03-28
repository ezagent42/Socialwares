---
name: request_allocation
description: "Create a resource allocation (amount, duration, purpose)"
---

# Request Allocation

## Trigger

User says "allocate 4 GPUs", "request resources", "I need 2 A100s for 3 hours", "book a server", "reserve capacity".

## Flow

1. Gather allocation parameters from the user:
   - **Resource**: which resource to allocate (kind/name, e.g. `bms/gpu-farm-01`)
   - **Amount**: how many units (e.g. 4)
   - **Duration** (optional): lease time (e.g. `2h`, `30m`, `1d`)
   - **Purpose** (optional): what it's for
2. If the user doesn't specify a resource name, help them search first (suggest using search_resources)
3. Show the estimated cost before creating:
   - Read the resource's `spec.pricing` to calculate: amount × unit_price (per_unit) or fixed price
   - Ask user to confirm
4. Run `one alloc create --resource <kind/name> --amount <n> [--duration <d>] [--purpose "<p>"]`
5. Parse response:
   - Success: show allocation name, amount, pricing, lease end time
   - 409 (capacity insufficient): tell user how much is available, suggest reducing amount
   - 403 (quota exceeded): tell user their quota is full, suggest releasing existing allocations

## API

```bash
# Basic allocation
one alloc create --resource bms/gpu-farm-01 --amount 4 --unit A100-hour --duration 2h

# With purpose and consumer
one alloc create --resource bms/gpu-farm-01 --amount 4 --unit A100-hour --duration 2h --consumer alice --purpose "LLM training"

# Allocate a dataset access license
one alloc create --resource ds/imagenet-2024 --amount 1 --unit access-license

# Allocate a software license seat
one alloc create --resource lic/jetbrains-team-2026 --amount 1 --unit seat
```

## Notes

- Pricing is auto-copied from the resource's `spec.pricing` to the Allocation
- Server-side atomically deducts `capacity.available` (409 if insufficient)
- Server-side checks quota (403 if exceeded)
- If `require_manual_confirm=true` on the resource, phase starts as `pending` (needs admin approve)
- Otherwise phase starts as `active` immediately
- Allocations with `--duration` auto-expire when lease ends (background job every 2 min)
