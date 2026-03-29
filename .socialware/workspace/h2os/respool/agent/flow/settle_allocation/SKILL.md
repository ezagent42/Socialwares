---
name: settle_allocation
description: "Mark a released allocation as settled (billing complete)"
---

# Settle Allocation

## Trigger

User (admin) says "settle allocation", "mark as paid", "complete billing for alloc-483689", "settle released allocations".

## Flow

1. If no specific allocation named, list released allocations: `one alloc list --phase released -o json`
2. Show released allocations:
   - Allocation name, resource, invoice_amount, currency, released_at
3. For selected allocation, confirm settlement:
   - Show final invoice_amount and currency
   - Confirm with admin
4. Run `one alloc settle <name>`
5. Confirm phase is now `settled`

## API

```bash
# List released (awaiting settlement)
one alloc list --phase released -o json

# Settle specific allocation
one alloc settle alloc-483689
```

## Notes

- Only `released` or `disputed` allocations can be settled (400 otherwise)
- F1 transitions: released → settled, disputed → settled
- Settlement is a bookkeeping action — it does not trigger additional billing
