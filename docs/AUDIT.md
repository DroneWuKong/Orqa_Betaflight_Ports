# Audit and provenance

Initial upstream: betaflight/betaflight tag 2026.6.2, commit
e0b7bb01b17b21351057e9ead2d1ab39dd44fa16. Its config submodule pin is retained.

The parallel compatibility line pins betaflight/betaflight tag 2025.12.5,
commit 7348054f268f0058574719c134e9f149565bb8ea. It uses that tag's own config
submodule pin. Unlike 2026.6, this source line has no DroneCAN libcanard
submodule, so preparation hydrates only submodules declared by that release.
The same reviewed board overlays are compiled independently for each line and
the 2025.12 artifacts carry a version prefix. A successful build on either line
does not transfer hardware qualification from the other.

Board configurations derive from DroneWuKong/Orqa_H7_PX4_Ports's prior
codex/orqa-f405-bf-2026.6 work (reference/betaflight/2026.6/configs/ORQA).
The imported Windows checkout was not reset or modified. CRLF was normalized
in the new files; previous build receipts remain historical, not evidence
for these new binaries.

Reviewed changes:
- H743 USB detection PA9 -> PE2, corroborated by the PX4 H743 board map.
- Remove UART8 TX declaration on H743/APB; reviewed wiring establishes RX-only.
- APB PD14 is TIM4_CH3, sharing the DShot motor timer; do not expose it as an
  independent conventional servo while TIM4 motors are active.
- Preserve APB UART4 PC10/PC11 and never assign these pins to SDMMC.
- Keep explicit sensor rotations by build variant. H743 inherited alignments
  remain an open physical-validation item, not a rotation automatically copied
  across firmware conventions.

No flight-controller hardware was flashed. See CI for actual build outcomes.
Pin assertions and artifact tests protect against regression but do not prove
electrical wiring, DMA behavior under load, or correct body-frame axes.

The APB companion package implements MSP disarmed Blackbox offload. UART4 MSP
is enabled for fresh defaults at upstream's 115200 baud; saved configurations
are preserved. The reader uses the pinned firmware's variable-length,
uncompressed DATAFLASH_READ replies and BOXIDS-derived ARM flag. Two full reads,
equal SHA256, stable flash inventory and unchanged device UID gate publication.
It neither erases flash nor issues configuration/arming commands. The shared
SD guard/mount repair derives from this account's PX4 companion work; the
Blackbox wire protocol and runtime are separate. See companion/apb/README.md.
