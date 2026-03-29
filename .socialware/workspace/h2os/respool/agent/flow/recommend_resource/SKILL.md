---
name: recommend_resource
description: "Recommend optimal resources based on user requirements"
---

# Recommend Resource

## Trigger

User says "what should I use for training", "recommend a GPU server", "cheapest option for 8 GPUs", "best resource for my budget", "help me choose".

## Flow

1. Understand user requirements:
   - **Workload type**: training, inference, data processing, development
   - **Compute needs**: GPU count, CPU, memory
   - **Budget constraint**: max cost per hour/day
   - **Duration**: how long they need it
   - **Priority**: cost vs performance vs availability
2. Search available resources: `one get <kind> -q "spec.capacity.available>=<needed>" -o json`
3. Score and rank candidates:
   - **Availability**: capacity.available >= requested amount
   - **Cost efficiency**: unit_price / capacity unit
   - **Fit**: does the resource type match the workload
4. Present top 3 recommendations:
   - Resource name, type, location (namespace)
   - Available capacity
   - Pricing (model + unit_price + currency)
   - Estimated total cost for requested duration
   - Why this resource fits (brief justification)
5. Ask user which one to allocate (or refine search)

## API

```bash
# Search by capacity and sort by price
one get bms -q "spec.capacity.available>=4 --sort spec.pricing.unit_price:asc" -o json

# Search across types
one get "*" -q "label.role:gpu-compute spec.capacity.available>=1" -o json

# Check specific resource details
one get bms gpu-farm-01 -o json
```

## Notes

- This skill does NOT create allocations — only recommends
- If user wants to proceed, hand off to request_allocation or batch_allocate
- Consider tiered pricing: higher volumes may be cheaper per unit
- If no resources match requirements, suggest alternatives (smaller amount, different type, wait for capacity)
