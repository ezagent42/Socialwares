---
name: approve_allocation
description: "Approve a pending resource allocation"
---

# Approve Allocation

## Trigger

User (admin) says "approve allocation", "approve alloc-483689", "accept pending request".

## Flow

1. If no specific allocation named, list pending allocations: `one alloc list --phase pending -o json`
2. Show pending allocations with details:
   - Requester (consumer), resource, amount, purpose, time waiting
3. For the selected allocation, show full details: `one alloc get <name> -o json`
4. Confirm with admin before approving
5. Run `one alloc approve <name>`
6. Parse response:
   - Success: show allocation now active, capacity deducted
   - Error: explain (e.g. capacity insufficient since request was made)

## API

```bash
# List pending allocations
one alloc list --phase pending -o json

# Approve specific allocation
one alloc approve alloc-483689
```

## Notes

- Only allocations in `pending` phase can be approved (400 otherwise)
- Approving atomically deducts capacity from the resource (409 if insufficient)
- Allocations only enter `pending` if the resource has `require_manual_confirm=true`
- This is an F1 state machine transition: pending → active
