# SM-S908B / S908BXXSMGZB2 artifact

`cve-2026-43499-app.so` is the current hardware-validated S908B/GZB2 payload for PR #272.

| Revision | Bytes | SHA-256 |
| --- | ---: | --- |
| current | 1757752 | `d2b52dc52a69571a145a64f0f57ae53884383a996661066ca84b52a45eb691bf` |
| original hardware reference | 1757688 | `19a219a94660a60c06a4c34f9a873b5c9ccacda7129d409ba8486ffe61453235` |

The current binary adds one lifecycle/cleanup change: `reset_pipe_attempt()` is called before the CFI-fail retry `return 70`. The S908B offsets, physical KASLR scan, embedded ARM32 stage, CFI/PhysRW path, root path and KernelSU candidate are unchanged.

The embedded ARM32 stage is still byte-identical to the original validation build:

`023190461719fc4cc11a7d114ff8da5132f1afa0eba32c907053e83682914152`

This rebuilt payload was tested again on physical SM-S908B/GZB2 hardware through the official Root My Galaxy execution path with a reboot between each run: **7/7 full-path successes**, with no kernel panic observed. The raw logs and run notes live under `docs/validation/SM-S908B-S908BXXSMGZB2-2026-09-04/`.

The previous payload/hash is kept above as the original hardware reference rather than being silently replaced.
