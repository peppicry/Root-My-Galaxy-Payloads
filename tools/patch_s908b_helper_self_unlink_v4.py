#!/usr/bin/env python3
import sys
from pathlib import Path

repo = Path(sys.argv[1])
source = repo / "src/su_daemon.c"
text = source.read_text()

old = '''  int status = is_kernelsu_late_load
                   ? run_kernelsu_late_load(&request, conn)
                   : request.header.interactive
                         ? run_interactive(&request, conn)
                         : run_direct(&request, conn);
  send_response(conn, status);
  free_request(&request);
}'''

new = '''  int status = is_kernelsu_late_load
                   ? run_kernelsu_late_load(&request, conn)
                   : request.header.interactive
                         ? run_interactive(&request, conn)
                         : run_direct(&request, conn);

  /* The late-load request is the final operation that needs the bootstrap
   * pathname.  This process is already the root-owned UMH daemon child, so it
   * is the correct privilege/domain to remove the socket inode.  Unlinking the
   * pathname does not break the accepted connection used to send this response
   * and avoids asking shell/Shizuku to delete a root-owned socket later. */
  if (is_kernelsu_late_load && status == 0) {
    unlink(BOOTSTRAP_SOCK_PATH);
  }

  send_response(conn, status);
  free_request(&request);
}'''

if old not in text:
    raise SystemExit("serve_one late-load dispatch block not found")
source.write_text(text.replace(old, new, 1))
print("bootstrap_socket_self_unlink=after-successful-late-load")
