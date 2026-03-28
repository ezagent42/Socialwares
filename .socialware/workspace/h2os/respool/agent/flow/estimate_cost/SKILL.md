---
name: estimate_cost
description: "Estimate cost for a potential allocation"
---

# Estimate Cost

## Trigger

User says "how much would it cost", "estimate price", "what's the cost for 4 GPUs", "pricing for this resource", "budget estimate".

## Flow

1. Get parameters from the user:
   - Resource (kind/name)
   - Amount
   - Duration (optional, for per_unit calculation)
2. Fetch the resource's pricing info: `one get <kind> <name> -o json`
3. Extract `spec.pricing` and calculate:
   - **fixed**: cost = unit_price (one-time)
   - **per_unit**: cost = amount × unit_price
   - **tiered**: walk through tiers array:
     - Each tier: `{ up_to: N, unit_price: P }`
     - `up_to <= 0` means unlimited (last tier)
     - Accumulate: min(amount_remaining, up_to) × unit_price per tier
4. Present breakdown:
   - Resource name
   - Pricing model
   - Unit price + currency
   - Amount requested
   - **Total estimated cost**
5. If resource has no pricing info, tell the user pricing is not configured for this resource

## API

```bash
# Fetch resource to read pricing
one get bms gpu-farm-01 -o json

# Example: extract pricing with jq
one get bms gpu-farm-01 -o json | jq '.spec.pricing'

# For tiered pricing, the tiers array looks like:
# [{"up_to": 10, "unit_price": 8}, {"up_to": 50, "unit_price": 6}, {"up_to": 0, "unit_price": 4}]
```

## Notes

- This skill does NOT create an allocation — it only estimates
- For per_unit with duration: estimate = amount × unit_price × duration_hours
- Currency comes from spec.pricing.currency (e.g. USDT, USD)
- If the user wants to proceed after seeing the estimate, suggest using request_allocation
