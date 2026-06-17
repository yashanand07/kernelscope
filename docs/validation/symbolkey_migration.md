| Profile    | Graph Build | Runtime Trace | Dispatch | Synthetic | Ambiguity | Mermaid | Notes                     |
| ---------- | ----------- | ------------- | -------- | --------- | --------- | ------- | ------------------------- |
| Scheduler  | ✓           | ✓             | 19       | 2         | None      | ✓       | Stable                    |
| MM         | ✓           | ✓             | 2        | 2         | MMU/NOMMU | ✓       | Expected config ambiguity |
| IRQ        | ✓           | ✓             | 1        | 1         | None      | ✓       | Dispatch validated        |
| Workqueue  | ✓           | ✓             | 0        | 0         | None      | ✓       | Queue path validated      |
| Block I/O  | ✓           | ✓             | 0        | 0         | None      | ✓       | Deep direct-call spine    |
| Network RX | ✓           | ✓             | 2        | 0         | None      | ✓       | Dispatch validated        |
| TCP RX     | Same as NET | Same as NET   | Same     | Same      | Same      | Same    | Profile alias             |

Date - 17th June 2026