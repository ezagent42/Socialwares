# Diagnose — Judgment Examples

## Example 1: Time condition

```yaml
C1:
  from: { role: default, action: submit_task }
  to: { role: reviewer, action: review_task }
  condition: "within 24h"
```

Script output:
```
from events: 1
  2026-03-25T02:33:39 [default] submit_task
to events: 0
```

Your judgment: "C1 VIOLATED — submit_task happened but review_task never occurred. Reviewer needs to act."

## Example 2: Sequence condition

```yaml
C2:
  from: { role: default, action: create_task }
  to: { role: default, action: submit_task }
  condition: "within 10 seconds"
```

Script output:
```
from events: 1
  2026-03-25T02:31:43 [default] create_task
to events: 1
  2026-03-25T02:33:39 [default] submit_task
```

Your judgment: "C2 VIOLATED — create_task at 02:31:43, submit_task at 02:33:39, difference = 116 seconds > 10 seconds."

## Example 3: Both actions happen but partial

```yaml
C3:
  from: { role: pm, action: create_task }
  to: { role: pm, action: close_task }
  condition: "within 48h"
```

Script output:
```
from events: 3
  2026-03-23T10:00:00 [pm] create_task
  2026-03-24T09:00:00 [pm] create_task
  2026-03-25T14:00:00 [pm] create_task
to events: 2
  2026-03-24T08:00:00 [pm] close_task
  2026-03-25T10:00:00 [pm] close_task
```

Your judgment: "C3 PARTIALLY FULFILLED — 3 tasks created, 2 closed. First task (03-23 10:00) closed at 03-24 08:00 (22h, within 48h ✓). Second task (03-24 09:00) closed at 03-25 10:00 (25h, within 48h ✓). Third task (03-25 14:00) not yet closed. Rate: 2/3 = 67%."

## Example 4: Insufficient data

Script output:
```
from events: 0
to events: 0
```

Your judgment: "C1 INSUFFICIENT DATA — no events found for either action. The workflow hasn't been exercised yet. This is not a violation, but the commitment is untested."
