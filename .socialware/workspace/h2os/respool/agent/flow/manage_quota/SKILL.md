---
name: manage_quota
description: "View and manage resource allocation quotas"
---

# Manage Quota

## Trigger

User (admin) says "manage quotas", "set quota for alice", "show quota limits", "increase quota", "who has quota".

## Flow

### View quotas
1. Search quota configs: `one get cfg -q "label.respool.type:quota" -A -o json`
2. Present table: entity, max_active_allocations, namespace

### Set/update quota
1. Gather parameters:
   - Entity (consumer name, e.g. `alice`)
   - Max active allocations (number)
   - Namespace
2. Create or update quota Config:
   ```yaml
   apiVersion: v1
   kind: Config
   metadata:
     name: respool-quota-<entity>
     namespace: <namespace>
     labels:
       respool.type: quota
       respool.entity: <entity>
   spec:
     max_active_allocations: <number>
   ```
3. Apply: `one apply -f /tmp/quota.yaml -n <namespace>`
4. Confirm quota is set

### Remove quota
1. Delete the quota Config: `one delete cfg respool-quota-<entity>`
2. Confirm removal (entity now has unlimited allocations)

## API

```bash
# List all quotas
one get cfg -q "label.respool.type:quota" -A -o json

# Get specific entity's quota
one get cfg respool-quota-alice -o json

# Apply quota (from YAML file)
one apply -f quota.yaml -n team-ops

# Delete quota
one delete cfg respool-quota-alice
```

## Notes

- Quota is enforced server-side at allocation creation time (403 if exceeded)
- Quota = Config resource with label `respool.type: quota`
- `spec.max_active_allocations` = maximum concurrent active allocations for that entity
- No quota Config = unlimited allocations for that entity
