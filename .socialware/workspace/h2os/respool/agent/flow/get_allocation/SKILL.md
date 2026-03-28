---
name: get_allocation
description: "Get allocation details by name"
---

# Get Allocation Details

## Trigger

User says "show allocation details", "what's in alloc-483689", "allocation info", "check my allocation".

## Flow

1. Get the allocation name from the user (e.g. `alloc-483689`)
2. Run `one alloc get <name> -o json`
3. Present full details:
   - **Resource**: kind, name, namespace
   - **Amount**: value + unit
   - **Lease**: start → end (or "no expiry"), remaining time
   - **Pricing**: model, unit_price, currency
   - **Status**: phase, usage_reported, invoice_amount
   - **Purpose**: if set
   - **Release info**: released_at, release_reason (if released)
4. If the allocation is active, calculate current estimated cost:
   - per_unit: usage_reported × unit_price
   - fixed: unit_price
   - tiered: calculate based on tiers

## API

```bash
# Get allocation details
one alloc get alloc-483689 -o json

# Can also use generic get
one get alloc alloc-483689 -o json
```

## Notes

- invoice_amount is only calculated after release
- usage_reported can be updated during active phase via `one alloc usage`
