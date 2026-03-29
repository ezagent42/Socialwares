---
name: lease_reminder
description: "Remind about allocations nearing lease expiration or pending approval"
---

# Lease Reminder

## Trigger

- User says "any expiring allocations", "check lease status", "what's about to expire"
- On_violation from commitment C4 (pending allocation not approved within 24h)
- On_violation from commitment C5 (active allocation nearing lease.end)

## Flow

1. Get active allocations: `one alloc list --phase active -o json`
2. For each allocation with `spec.lease.end`:
   - Parse lease end time
   - Calculate remaining time
   - If remaining < 30 minutes → URGENT
   - If remaining < 2 hours → WARNING
   - If expired (should have auto-released) → CHECK (may indicate system issue)
3. Get pending allocations: `one alloc list --phase pending -o json`
4. For each pending allocation:
   - Calculate time since creation
   - If pending > 24 hours → OVERDUE (commitment C4 violation)
   - If pending > 12 hours → WARNING
5. Present summary:
   - Expiring soon: allocation name, resource, remaining time
   - Overdue pending: allocation name, resource, waiting time
6. If nothing urgent, report "No lease or approval alerts"

## API

```bash
# Active allocations (check lease.end)
one alloc list --phase active -o json

# Pending allocations (check creation time)
one alloc list --phase pending -o json

# Get specific allocation details
one alloc get <name> -o json
```

## Notes

- OneSystem auto-releases expired allocations every 2 minutes via background job
- This skill provides proactive warnings before auto-release happens
- Useful for users who want to extend or release manually before timeout
