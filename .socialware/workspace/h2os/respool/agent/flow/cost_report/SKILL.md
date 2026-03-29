---
name: cost_report
description: "Generate cost report for allocations"
---

# Cost Report

## Trigger

User says "show my costs", "billing report", "how much have I spent", "cost summary", "expense report".

## Flow

1. Get all allocations for the user: `one alloc list -o json`
2. Group by phase:
   - **Active**: currently incurring cost (show estimated running total)
   - **Released**: cost finalized (show invoice_amount)
   - **Settled**: paid (show invoice_amount)
3. Calculate totals:
   - Active estimated: sum of (usage_reported × unit_price) for per_unit, or unit_price for fixed
   - Released unpaid: sum of invoice_amount where phase=released
   - Settled paid: sum of invoice_amount where phase=settled
   - Grand total: all of the above
4. Group by currency (USDT, USD, etc.)
5. Present breakdown:
   - By resource type (BMS, Dataset, License)
   - By time period (this week / this month) if possible from timestamps
   - By purpose (if set on allocations)
6. Highlight top cost drivers

## API

```bash
# All allocations
one alloc list -o json

# Filter by phase for specific views
one alloc list --phase active -o json
one alloc list --phase released -o json
one alloc list --phase settled -o json

# Get details for specific allocation
one alloc get <name> -o json
```

## Notes

- invoice_amount is only set after release (server auto-calculates)
- For active allocations, cost is estimated from usage_reported × unit_price
- Tiered pricing calculation: walk tiers array, accumulate per-tier cost
- Currency may vary per resource — report totals per currency
