#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLIDE = ROOT / "src" / "slide_app.c"
MAIN = ROOT / "src" / "main.c"
PRELOAD = ROOT / "src" / "preload.c"
TARGET = ROOT / "src" / "targets" / "pa3q-S938BXXSBCZG3" / "target.h"


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} occurrences, found {count}")
    path.write_text(text.replace(old, new))


def patch_slide() -> None:
    text = SLIDE.read_text()
    needle = """  if (!forced_delay && !delay) {\n    delay = delays[delay_index % (sizeof(delays) / sizeof(delays[0]))];\n  }\n"""
    injected = """#if defined(DIVA_V06_SENSITIVE_LAB) && DIVA_V06_SENSITIVE_LAB\n  if (!forced_delay) {\n    const char *v06_fops_delay = getenv(\"DIVA_V06_FOPS_DELAY_USEC\");\n    if (v06_fops_delay && *v06_fops_delay) {\n      char *v06_end = NULL;\n      errno = 0;\n      long v06_value = strtol(v06_fops_delay, &v06_end, 0);\n      if (!errno && v06_end != v06_fops_delay && !*v06_end &&\n          v06_value >= 0 && v06_value <= 1000000) {\n        delay = (int)v06_value;\n      } else {\n        pr_warning(\"v0.6 invalid DIVA_V06_FOPS_DELAY_USEC=%s; using baseline\\n\",\n                   v06_fops_delay);\n      }\n    }\n  }\n#endif\n""" + needle
    count = text.count(needle)
    if count != 2:
        raise SystemExit(f"{SLIDE}: expected 2 FOPS fallback sites, found {count}")
    SLIDE.write_text(text.replace(needle, injected))


def patch_main() -> None:
    old = '  durable_log_checkpoint("fops-page-held");\n'
    new = """#if !defined(DIVA_V06_QUIET_SENSITIVE_IO) || !DIVA_V06_QUIET_SENSITIVE_IO\n  durable_log_checkpoint(\"fops-page-held\");\n#endif\n"""
    replace_exact(MAIN, old, new, 1)


def patch_preload() -> None:
    text = PRELOAD.read_text()

    old = """  set_unbuffer();\n  wait_for_boot_quiet_window();\n\n  int max_attempts = env_int(\n"""
    new = """  set_unbuffer();\n  wait_for_boot_quiet_window();\n\n#if defined(DIVA_V06_DISCARD_EXTERNAL_P0_STATE) && DIVA_V06_DISCARD_EXTERNAL_P0_STATE\n  const char *v06_allow_external_p0 = getenv(\"DIVA_V06_ALLOW_EXTERNAL_P0\");\n  if (!v06_allow_external_p0 || strcmp(v06_allow_external_p0, \"1\") != 0) {\n    unsetenv(\"SLIDE_P0_OFFSET\");\n    unsetenv(\"P0_GATE_PAGE_STRUCT\");\n    unsetenv(\"P0_PROBE_PAGE_STRUCT\");\n    pr_info(\"v0.6 external P0/KASLR state discarded before session\\n\");\n  }\n#endif\n\n  int max_attempts = env_int(\n"""
    if text.count(old) != 1:
        raise SystemExit(f"{PRELOAD}: constructor insertion point changed")
    text = text.replace(old, new)

    old_guard = """#if defined(APP_REQUIRE_FRESH_P0_SESSION) && APP_REQUIRE_FRESH_P0_SESSION\n      pr_error(\"fresh P0 session was consumed by the failed child; \"\n               \"refusing cross-process retry, reboot required\\n\");\n      break;\n#else\n"""
    new_guard = """#if defined(APP_REQUIRE_FRESH_P0_SESSION) && APP_REQUIRE_FRESH_P0_SESSION && \\\n    !(defined(DIVA_V06_RETAIN_CONFIRMED_P0) && DIVA_V06_RETAIN_CONFIRMED_P0)\n      pr_error(\"fresh P0 session was consumed by the failed child; \"\n               \"refusing cross-process retry, reboot required\\n\");\n      break;\n#else\n"""
    if text.count(old_guard) != 1:
        raise SystemExit(f"{PRELOAD}: confirmed-P0 retention guard changed")
    text = text.replace(old_guard, new_guard)

    old_log = """      pr_success(\"supervisor retained p0_offset=%s gate=%s probe=%s\\n\",\n                 offset_arg, gate_page_arg, probe_page_arg);\n"""
    new_log = """#if defined(DIVA_V06_SENSITIVE_LAB) && DIVA_V06_SENSITIVE_LAB\n      pr_success(\"v0.6 post-FOPS policy=retain-confirmed p0_offset=%s gate=%s probe=%s\\n\",\n                 offset_arg, gate_page_arg, probe_page_arg);\n#else\n      pr_success(\"supervisor retained p0_offset=%s gate=%s probe=%s\\n\",\n                 offset_arg, gate_page_arg, probe_page_arg);\n#endif\n"""
    if text.count(old_log) != 1:
        raise SystemExit(f"{PRELOAD}: retention log site changed")
    text = text.replace(old_log, new_log)
    PRELOAD.write_text(text)


def patch_target() -> None:
    old = '#define BUILD_VARIANT_LABEL "pa3q-S938BXXSBCZG3-app-physical-p0-oracle"\n'
    new = '#define BUILD_VARIANT_LABEL "pa3q-S938BXXSBCZG3-app-diva-v0.6-sensitive-lab"\n'
    replace_exact(TARGET, old, new, 1)


if __name__ == "__main__":
    patch_slide()
    patch_main()
    patch_preload()
    patch_target()
    print("DIVA v0.6 sensitive-lab patch applied")
