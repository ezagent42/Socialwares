---
name: search_resources
description: "Search resources by type, labels, capacity, or pricing"
---

# Search Resources

## Trigger

User says "search for GPUs", "find servers with capacity", "show available machines", "what servers have 4+ GPUs", "find cheap resources".

## Flow

1. Determine what the user is looking for:
   - Resource type (bms, vm, dataset, license, etc.)
   - Filters: labels, capacity, pricing, namespace
2. Build a OneQL query from the user's request:
   - Capacity: `spec.capacity.available>=N`
   - Pricing: `spec.pricing.unit_price<=N`
   - Labels: `label.key:value`
3. Run `one get <kind> -q "<query>" -o json`
4. Parse results and present a table:
   - Name, namespace, capacity (available/total), pricing (model + unit_price + currency)
5. If no results, suggest broadening the search (different kind, relaxed filters)

## API

```bash
# Search BareMetalServers with available capacity
one get bms -q "spec.capacity.available>=1" -o json

# Search by label + capacity
one get bms -q "label.env:prod spec.capacity.available>=4" -o json

# Search by pricing
one get bms -q "spec.pricing.unit_price<=10" -o json

# Sort by price
one get bms -q "spec.capacity.available>=1 --sort spec.pricing.unit_price:asc" -o json

# Search datasets
one get ds -q "spec.format:tar.gz" -o json

# Search licenses with available seats
one get lic -q "spec.capacity.available>=1" -o json

# Cross-type wildcard search
one get "*" -q "label.role:gpu-compute" -o json
```

## Notes

- OneQL supports: `:` (equals), `!=`, `>`, `>=`, `<`, `<=`, `~` (contains)
- Spec fields support nested paths: `spec.pricing.unit_price`, `spec.capacity.available`
- Resource types: bms, vm, ds (dataset), lic (license), container, ecs, machine
