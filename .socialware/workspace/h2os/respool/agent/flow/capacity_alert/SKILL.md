---
name: capacity_alert
description: "Alert when resource pool capacity drops below threshold"
---

# Capacity Alert

## Trigger

- User says "check capacity", "any pools running low", "capacity status"
- Evolver triggers periodically to monitor pool health
- On_violation from commitment C1 (allocation response slow may indicate capacity pressure)

## Flow

1. Run `one pool list -o json` to get all pools
2. For each pool, get resources: `one pool get <pool-namespace> -o json`
3. For each resource with `spec.capacity`, check:
   - `available / total < 0.2` → CRITICAL (less than 20% remaining)
   - `available / total < 0.5` → WARNING (less than 50% remaining)
   - `available == 0` → EXHAUSTED (no capacity left)
4. Present alert summary:
   - Pool name, resource name, available/total, utilization %
   - Highlight CRITICAL and EXHAUSTED resources
5. If all pools healthy, report "All pools have sufficient capacity"

## API

```bash
# List all pools
one pool list -o json

# Get resources in a pool
one pool get <pool-namespace> -o json

# Direct query for low-capacity resources
one get bms -q "spec.capacity.available<=2" -A -o json
one get lic -q "spec.capacity.available<=1" -A -o json
```

## Notes

- Thresholds (20%/50%) are initial defaults; adjust based on actual usage patterns
- This skill is read-only — it alerts, does not take action
- For automated monitoring, evolver can run this periodically via evolve_auto
