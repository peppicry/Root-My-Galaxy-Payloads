#!/system/bin/sh
# DIVA v0.7 ENV-LAB out-of-band snapshot.
#
# IMPORTANT: do not run this while the payload is inside its sensitive race.
# Use LIGHT for low-noise PRE/POST metadata. Use FULL after a run/root when
# deeper allocator and lifecycle evidence is desired.

set -u

TAG="${1:-UNLABELED}"
CONDITION="${2:-OTHER}"
MODE="${3:-light}"
PKG="dev.busung.s25uroot.s25u.next.payloadlab"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/sdcard/RMG-V07-ENV-${TAG}-${STAMP}.txt"

case "$MODE" in
  light|LIGHT) MODE="light" ;;
  full|FULL|postroot|POSTROOT) MODE="full" ;;
  *) echo "usage: $0 TAG CONDITION [light|full]" >&2; exit 2 ;;
esac

UID_NOW="$(id -u 2>/dev/null || echo unknown)"
if [ "$UID_NOW" != "0" ]; then
  echo "warning: v0.7 snapshot is most complete from Shizuku-root; current uid=$UID_NOW" >&2
fi

first_pid() {
  pidof "$1" 2>/dev/null | awk '{print $1}'
}

proc_starttime() {
  [ -n "${1:-}" ] && [ -r "/proc/$1/stat" ] && awk '{print $22}' "/proc/$1/stat" 2>/dev/null
}

ns_value() {
  [ -n "${1:-}" ] && readlink "/proc/$1/ns/mnt" 2>/dev/null
}

cache_snapshot() {
  ROOT="$1"
  echo "data_root=$ROOT"
  for D in "$ROOT" "$ROOT/cache" "$ROOT/code_cache"; do
    if [ -e "$D" ]; then
      stat -c 'inode=%i size=%s mtime=%Y mode=%a uid=%u gid=%g path=%n' "$D" 2>/dev/null
    else
      echo "missing=$D"
    fi
  done
  for D in "$ROOT/cache" "$ROOT/code_cache"; do
    if [ -d "$D" ]; then
      N="$(find "$D" -xdev -type f 2>/dev/null | wc -l)"
      K="$(du -sk "$D" 2>/dev/null | awk '{print $1}')"
      echo "dir=$D files=$N kib=${K:-unknown}"
    fi
  done
}

PID="$(first_pid "$PKG")"
SPID="$(first_pid shizuku_server)"

DATA_ROOT=""
for CAND in \
  "/data/user/0/$PKG" \
  "/proc/1/root/data/user/0/$PKG" \
  "/data_mirror/data_ce/null/0/$PKG"
do
  if [ -d "$CAND" ]; then
    DATA_ROOT="$CAND"
    break
  fi
done

{
  echo "========== V0.7 SESSION CAPSULE =========="
  echo "schema=diva-v0.7-env-lab/1"
  echo "tag=$TAG"
  echo "condition=$CONDITION"
  echo "mode=$MODE"
  date
  echo "epoch=$(date +%s)"
  echo "executor=$(id 2>/dev/null)"
  printf 'executor_selinux='; cat /proc/self/attr/current 2>/dev/null; echo
  printf 'boot_id='; cat /proc/sys/kernel/random/boot_id 2>/dev/null
  printf 'uptime='; cat /proc/uptime 2>/dev/null
  uname -a 2>/dev/null

  echo
  echo "========== MOUNT NAMESPACES =========="
  echo "self_ns=$(readlink /proc/self/ns/mnt 2>/dev/null)"
  echo "init_ns=$(readlink /proc/1/ns/mnt 2>/dev/null)"
  echo "app_ns=$(ns_value "$PID")"
  echo "shizuku_ns=$(ns_value "$SPID")"

  echo
  echo "========== SHIZUKU =========="
  echo "pid=$SPID"
  echo "starttime=$(proc_starttime "$SPID")"
  if [ -n "$SPID" ]; then
    grep -E '^(Name|Pid|PPid|Uid|Gid|State|Threads|Cpus_allowed_list|voluntary_ctxt_switches|nonvoluntary_ctxt_switches):' "/proc/$SPID/status" 2>/dev/null
    printf 'selinux='; cat "/proc/$SPID/attr/current" 2>/dev/null; echo
    echo "cgroup:"
    cat "/proc/$SPID/cgroup" 2>/dev/null
  fi

  echo
  echo "========== PAYLOAD LAB PROCESS =========="
  echo "package=$PKG"
  echo "pid=$PID"
  echo "starttime=$(proc_starttime "$PID")"
  if [ -n "$PID" ]; then
    grep -E '^(Name|Pid|PPid|Uid|Gid|State|Threads|VmRSS|VmSize|Cpus_allowed_list|voluntary_ctxt_switches|nonvoluntary_ctxt_switches):' "/proc/$PID/status" 2>/dev/null
    printf 'selinux='; cat "/proc/$PID/attr/current" 2>/dev/null; echo
    echo "cgroup:"
    cat "/proc/$PID/cgroup" 2>/dev/null
    printf 'oom_score_adj='; cat "/proc/$PID/oom_score_adj" 2>/dev/null
  fi

  echo
  echo "========== CACHE / CODE CACHE =========="
  if [ -n "$DATA_ROOT" ]; then
    cache_snapshot "$DATA_ROOT"
  else
    echo "data_root=UNRESOLVED"
  fi

  echo
  echo "========== STAGING METADATA =========="
  for F in /data/local/tmp/ksu-payload /data/local/tmp/ksu-helper /data/local/tmp/ksud-s25unext /data/local/tmp/ksunext-stage.log /data/local/tmp/temp_su.sock; do
    [ -e "$F" ] && stat -c 'inode=%i size=%s mtime=%Y mode=%a uid=%u gid=%g path=%n' "$F" 2>/dev/null
  done

  if [ "$MODE" = "full" ]; then
    echo
    echo "========== STAGING SHA256 =========="
    for F in /data/local/tmp/ksu-payload /data/local/tmp/ksu-helper /data/local/tmp/ksud-s25unext; do
      [ -f "$F" ] && sha256sum "$F" 2>/dev/null
    done

    echo
    echo "========== SELECTED SLAB RUNTIME =========="
    grep -E '^(mm_struct|skbuff_head_cache|skbuff_fclone_cache|task_struct|files_cache|filp|kmalloc-256|kmalloc-512|kmalloc-1k|kmalloc-2k) ' /proc/slabinfo 2>/dev/null

    echo
    echo "========== SLAB GEOMETRY =========="
    for C in mm_struct skbuff_head_cache kmalloc-256 kmalloc-512 kmalloc-1k kmalloc-2k; do
      D="/sys/kernel/slab/$C"
      [ -d "$D" ] || continue
      echo "--- $C ---"
      for F in object_size slab_size align objs_per_slab order cpu_partial min_partial objects objects_partial partial slabs; do
        [ -r "$D/$F" ] && printf '%s=' "$F" && cat "$D/$F"
      done
    done

    echo
    echo "========== VMSTAT =========="
    grep -E '^(nr_free_pages|nr_slab_reclaimable|nr_slab_unreclaimable|pgfree|pgfault|pgmajfault|pgalloc_|allocstall|compact_)' /proc/vmstat 2>/dev/null

    echo
    echo "========== BUDDY =========="
    cat /proc/buddyinfo 2>/dev/null

    echo
    echo "========== RECENT LIFECYCLE / FREECESS =========="
    logcat -b all -d -v threadtime 2>/dev/null | \
      grep -Ei "$PKG|10773|Freecess|am_freeze|am_unfreeze|am_compact" | \
      tail -n 250
  fi

  echo
  echo "========== END =========="
} > "$OUT" 2>&1

echo "$OUT"
