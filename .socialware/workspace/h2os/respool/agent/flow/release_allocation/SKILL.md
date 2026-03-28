---
name: release_allocation
description: "Release an active allocation (triggers billing)"
---

# Release Allocation

## Trigger

User says "release my allocation", "I'm done with the GPUs", "free up resources", "stop using alloc-483689", "cancel allocation".

## Flow

1. Get the allocation name from the user
2. Confirm with the user before releasing:
   - Show current usage and estimated final cost
   - Warn that release is irreversible (allocation moves to `released` phase)
3. Determine release reason:
   - `completed` — normal completion (default)
   - `cancelled` — user wants to cancel early
4. Run `one alloc release <name> --reason <reason>`
5. Parse response:
   - Show final invoice_amount (auto-calculated by server)
   - Show capacity recovered
   - Confirm phase is now `released`
6. If error (e.g. allocation not in `active` phase), explain the current phase and what actions are available

## API

```bash
# Release with default reason (completed)
one alloc release alloc-483689

# Release with specific reason
one alloc release alloc-483689 --reason completed
one alloc release alloc-483689 --reason cancelled
```

## Notes

- Server auto-recovers `capacity.available` on the source resource
- Server auto-calculates `invoice_amount`:
  - per_unit: usage_reported × unit_price
  - fixed: unit_price
  - tiered: stepped calculation based on tiers array
- Only `active` allocations can be released (400 if wrong phase)
- Allocations with lease.end auto-release when expired (no manual action needed)
