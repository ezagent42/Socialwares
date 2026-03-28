---
name: list_allocations
description: "List allocations with optional phase/consumer filter"
---

# List Allocations

## Trigger

User says "show my allocations", "what am I using", "list active allocations", "show all pending", "what's allocated".

## Flow

1. Determine filters from context:
   - Phase: pending, active, released, settled, disputed (default: show all)
   - Consumer: specific user or current user
2. Run `one alloc list [--phase <phase>] [--consumer <name>] -o json`
3. Present a summary table:
   - Allocation name
   - Resource (kind/name)
   - Amount + unit
   - Phase
   - Lease period (start → end, or "no expiry")
   - Cost so far (usage_reported × unit_price for per_unit, or fixed price)
4. Highlight any allocations nearing lease expiration

## API

```bash
# List all allocations
one alloc list -o json

# Filter by phase
one alloc list --phase active -o json
one alloc list --phase pending -o json

# Filter by consumer
one alloc list --consumer alice -o json

# Combine filters
one alloc list --phase active --consumer alice -o json
```

## Notes

- Phases: pending → active → released → settled ⇌ disputed
- `active` allocations are consuming capacity and may be incurring cost
- `pending` allocations need admin approval (if resource has require_manual_confirm)
