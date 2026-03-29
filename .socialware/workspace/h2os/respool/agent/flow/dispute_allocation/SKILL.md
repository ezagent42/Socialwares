---
name: dispute_allocation
description: "Dispute a settled allocation's billing"
---

# Dispute Allocation

## Trigger

User says "dispute this allocation", "I was overcharged", "billing is wrong for alloc-483689", "challenge invoice".

## Flow

1. Get the allocation details: `one alloc get <name> -o json`
2. Verify it's in `settled` phase (only settled allocations can be disputed)
3. Ask user for dispute reason:
   - Overcharged (usage was less than reported)
   - Wrong pricing (unit_price doesn't match agreement)
   - Service issue (resource was unavailable during lease)
   - Other (free text)
4. Run `one alloc dispute <name> --reason "<reason>"`
5. Confirm phase is now `disputed`
6. Inform user that an admin will review and re-settle

## API

```bash
# Dispute with reason
one alloc dispute alloc-483689 --reason "overcharged — actual usage was 1.5 not 4"

# Check dispute status
one alloc get alloc-483689 -o json
```

## Notes

- Only `settled` allocations can be disputed (400 otherwise)
- F1 transition: settled → disputed
- Disputed allocations can be re-settled by admin after review (disputed → settled)
- Dispute reason is recorded for admin review
