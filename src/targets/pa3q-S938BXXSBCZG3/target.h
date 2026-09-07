#ifndef CZG3_TARGET_WRAPPER_H
#define CZG3_TARGET_WRAPPER_H

/*
 * SM-S938B / S938BXXSBCZG3 laboratory target.
 *
 * Static validation performed against:
 *   - exact runtime kallsyms
 *   - exact kernel BTF
 *   - exact boot.img raw ARM64 Image
 *
 * The 6.6.98 PA3Q symbol/layout constants were independently checked against
 * CZG3 before this wrapper was created. Build identity and P0 fingerprints
 * are CZG3-specific and MUST NOT be relaxed.
 */

#ifndef BUILD_FINGERPRINT
#define BUILD_FINGERPRINT \
  "samsung/pa3qxeea/pa3q:16/BP4A.251205.006/S938BXXSBCZG3_OXMBCZG3:user/release-keys"
#endif

#include "../pa3q-S938NKSUACZF1/target.h"

#undef BUILD_VARIANT_LABEL
#if defined(APP_PAYLOAD) && APP_PAYLOAD
#define BUILD_VARIANT_LABEL "pa3q-S938BXXSBCZG3-app-physical-p0-oracle"
#else
#define BUILD_VARIANT_LABEL "pa3q-S938BXXSBCZG3-root-umh"
#endif

#if defined(APP_PAYLOAD) && APP_PAYLOAD
#undef P0_FINGERPRINT_HEADER
#define P0_FINGERPRINT_HEADER \
  "targets/pa3q-S938BXXSBCZG3/p0_fingerprint.h"
#endif

#define CZG3_EXPECTED_MODEL "SM-S938B"
#define CZG3_EXPECTED_DEVICE "pa3q"
#define CZG3_EXPECTED_BUILD_DISPLAY "BP4A.251205.006.S938BXXSBCZG3"
#define CZG3_EXPECTED_KERNEL_RELEASE \
  "6.6.98-android15-8-pd6ff1cd-abogkiS938BXXSBCZG3-4k"
#define CZG3_EXPECTED_SECURITY_PATCH "2026-07-05"
#define CZG3_EXPECTED_PAGE_SIZE 4096

#endif
