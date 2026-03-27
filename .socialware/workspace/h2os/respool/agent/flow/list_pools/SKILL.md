---
name: list_pools
description: "List available resource pools and their capacity status"
---

# List Resource Pools

## Trigger

User says "show pools", "list pools", "what resources are available", "available capacity", "resource pools", "show me what I can use".

## Flow

1. Run `one pool list -o json` to get all resource pools
2. If the command fails with "not logged in", tell the user to run `one login` first
3. Parse the JSON output — each pool is a Config resource with label `respool.type: pool-config`
4. For each pool, extract:
   - Pool name (from the namespace)
   - Pool configuration (from spec)
5. For pools that have resources, optionally run `one pool get <pool-namespace> -o json` to show resources in that pool
6. Present a summary table to the user:
   - Pool name
   - Number of resources
   - Key resource types available
7. If no pools found, tell the user no resource pools are configured

## API

This skill uses the `one` CLI directly (not HTTP API endpoints):

```bash
# List all pools
one pool list -o json

# Get pool details (resources in a specific pool)
one pool get <pool-namespace> -o json

# Search for resources with capacity in a pool namespace
one get bms -n <pool-namespace> -q "spec.capacity.available>=1" -o json
```

## Notes

- The `one` CLI must be installed and authenticated (`one login`)
- Pool = namespace with auto-discovery + Config resource labeled `respool.type: pool-config`
- Resources within a pool may have `spec.capacity` (total/available) and `spec.pricing` fields
