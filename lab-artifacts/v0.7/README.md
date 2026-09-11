# FULL DIVA v0.7.0 — Environment & Lifecycle Lab

Target: Samsung Galaxy S25 Ultra SM-S938B / `pa3q` / `S938BXXSBCZG3`.

## Status

This branch is the **provenance / observability scaffold** for v0.7.0. It intentionally does **not** claim to contain a newly tuned exploit payload yet.

The hardware-verified reference remains:

- `cve-2026-43499-app.FULL-DIVA-v0.3-HARDWARE-VERIFIED-BASE.so`
- size: `116108`
- SHA-256: `fe00f7d4680752ccdbd3470f2808630a7f3f0306f490d11f5e81f5c2c92a0e86`

The frozen v0.3 reference must never be edited or silently rebuilt under the same name.

## v0.7 mission

Explain why the same v0.3 can produce a 24/24 failure and later reach ROOT in the same boot after a userspace/lifecycle transition, without changing exploit tuning to chase the result.

The current evidence makes these environmental variables worth measuring:

- foreground/background transitions;
- Samsung Freecess freeze/unfreeze;
- process compaction;
- cgroup/cpuset placement and allowed CPUs;
- process identity/start time and mount namespace;
- cache/code-cache state and inode identity;
- boot/session identity;
- staged payload/helper/KernelSU provenance;
- post-run allocator geometry snapshots when privileges permit.

## Scientific rules

1. Start from the v0.3 hardware-verified behavior, not the v0.6 sensitive-lab branch.
2. Do not modify the frozen v0.3 binary.
3. No heavy telemetry in the WRITE -> GATE / reclaim-sensitive window.
4. Heavy observation is PRE or POST only.
5. Do not automatically force Freecess, process compaction, affinity, cache clearing, or lifecycle transitions in v0.7.0.
6. Experimental condition is metadata only: `BASELINE`, `LIFECYCLE_ONLY`, `CLEAR_CACHE_MANUAL`, `FORCE_STOP_RELAUNCH_MANUAL`, or `OTHER`.
7. P0/KASLR provenance must remain explicit: `UNKNOWN`, `EXTERNAL`, or `PHYSICAL_CONFIRMED`.
8. A v0.7 build must not be called parity-valid until the v0.3 source transformation is reconstructed and checked against the frozen binary.

## Phase 0 deliverables

- golden binary manifest;
- parity/provenance guard;
- out-of-band PRE/POST environment snapshot utility;
- session schema and experiment labels;
- no primitive tuning changes.

## Known live-kernel facts used by this lab

On the tested CZG3 device, runtime SLUB reports `mm_struct` with `object_size=1224` (`0x4c8`) and `slab_size=1280` (`0x500`), while `skbuff_head_cache` reports `object_size=240` (`0xf0`) and `slab_size=256` (`0x100`). CPU-partial is active. These are observations for provenance/analysis, not new tuning inputs.

The Shizuku-root executor has also been observed in the init mount namespace while the Payload Lab app remains in a separate app mount namespace. The app has been observed in background cgroups/cpuset and Samsung Freecess has been observed freezing/unfreezing the same app PID.

## Next gate

Before any v0.7 payload binary is published, recover/reconstruct the exact source delta that produced v0.3, reproduce the frozen v0.3 hash, then add only out-of-band observability with one change at a time.
