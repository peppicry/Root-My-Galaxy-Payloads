#!/usr/bin/env python3
import sys
from pathlib import Path

app = Path(sys.argv[1])
vm_path = app / "app/src/main/java/dev/busung/s25uroot/InstallViewModel.kt"
text = vm_path.read_text()
old = '''                installKernelSu(payloads)
                cleanupBootstrapSocketAfterInstall()

                setPhase(InstallPhase.Installed, app.getString(R.string.status_ksu_active))'''
new = '''                installKernelSu(payloads)

                setPhase(InstallPhase.Installed, app.getString(R.string.status_ksu_active))'''
if old not in text:
    raise SystemExit("post-install socket cleanup call not found")
vm_path.write_text(text.replace(old, new, 1))
print("external_socket_cleanup=disabled")
print("socket_cleanup=performed_by_root_helper_late_load")
