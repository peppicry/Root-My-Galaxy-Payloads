# SM-S908B / S908BXXSMGZB2 artifact

The file `cve-2026-43499-app.so` is the exact native payload used by the
hardware-validation build.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `cve-2026-43499-app.so` | 1757688 | `19a219a94660a60c06a4c34f9a873b5c9ccacda7129d409ba8486ffe61453235` |

It was extracted byte-for-byte from the validation APK. Private CI rebuilt the
corresponding IonStack source state and required byte-for-byte identity with
this hardware-tested payload.

The size is intentional. This is the instrumented validation binary, not a
stripped or repadded 104,128-byte release substitute. It retains the diagnostic
and retry behavior present during the successful device runs. Repacking it
would create a different artifact and would break the hardware-proven hash.

The binary also retains the embedded ARM32 stage's historical diagnostic
banner containing `b0q`. That text is inherited provenance, not the selected
device identity; the validated target label is `S908BXXSMGZB2`. The disclosure
is expanded in `src/targets/b0s-S908BXXSMGZB2/README.md`.

The public provenance copy is available at
`src/targets/b0s-S908BXXSMGZB2/ionstack-s908b-gzb2/`. It preserves all build
inputs and omits only the non-build `MEMORY.md` developer notebook.

The KernelSU package used during validation is intentionally not republished
here as an S908B-exact artifact. It originated from the existing S901B GZD7
KDP candidate; its empirical compatibility on this device is documented in
`docs/SM-S908B-S908BXXSMGZB2.md`.
