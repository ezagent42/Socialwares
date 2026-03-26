# Diagnose — Violation to Primitive Mapping

| Violation pattern | Likely primitive | Fix |
|-------------------|-----------------|-----|
| `to` action never happens | Flow | Add/fix the SKILL.md for the `to` action |
| `to` action happens but too late | Commitment | Adjust the time condition, or fix the workflow bottleneck |
| Wrong role performs action | Role | Fix role permissions in role/*.md and flow.yaml |
| Action produces wrong output | Flow | Fix the SKILL.md instructions |
| Condition is unrealistic | Commitment | Adjust commitment.yaml to a realistic standard |
| Action not recognized | Scope | Check if capability is declared in scope.md |
