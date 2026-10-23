# Orqa Betaflight Ports

Audited downstream board configurations, reproducible build instructions and
review-gated upstream updates for Orqa controllers.

[![Build and verify](https://github.com/DroneWuKong/Orqa_Betaflight_Ports/actions/workflows/build.yml/badge.svg)](https://github.com/DroneWuKong/Orqa_Betaflight_Ports/actions/workflows/build.yml)

**Status: experimental, hardware-unvalidated.** This is a focused overlay,
not an official Orqa release. Passing CI is not proof of flight safety.

## Targets

| Build ID | Hardware / sensor population |
|---|---|
| h743-icm42688 | H7 QuadCore, dual ICM42688P |
| apb-mpu6000-icm42605 | APB, MPU6000 + ICM42605 |
| apb-icm42688 | APB, dual ICM42688P |
| f405-mpu6000 | F405 Pro, MPU6000 |
| f405-icm42688 | F405 Pro, ICM42688P |

Variants have different sensor rotations. Do not choose by MCU alone.
H743's inherited Betaflight rotations differ from some ArduPilot/PX4 definitions:
they are deliberately not changed without physical evidence. Older H743 MPU6000
populations are not covered by the H743 artifact. No Wingcore fixed-wing preset
or autonomous-navigation capability is claimed. F405 keeps the recovered
four-motor/two-servo/PPM mapping; this is not the eight-motor ArduPilot layout.

## Improvements

- Correct H743 USB VBUS detect from PA9 to PE2, matching the reviewed H743 map.
- Stop advertising an unverified UART8 TX pin; ESC telemetry is RX-only.
- Remove APB's independent third-servo claim: PD14 shares TIM4 with motors 1/2.
- Keep APB STM32 SD disabled: its card belongs to the Linux companion.
- Enable APB UART4 MSP defaults and supply a disarmed-only Blackbox-to-SD
  archive service with two-pass SHA256 verification, mount guards and rollback.
- Retain explicit APB/F405 sensor-population variants and separate artifact names.
- Preserve W25 blackbox / MAX7456 bus separation; reject pin-map regressions in CI.
- Pin upstream source and compiler; check compiler archive SHA256, image vectors,
  ELF flash layout, board identity and HEX/BIN agreement.
- Weekly stable-update PRs, complete build gates, manifests/checksums, and
  manual-only prerelease publication.

See [audit/provenance](docs/AUDIT.md), [bench checks](docs/TESTING.md) and
[update/release policy](docs/MAINTENANCE.md).

## Downloads

Persistent downloads: [v0.1.0-rc2 prerelease](https://github.com/DroneWuKong/Orqa_Betaflight_Ports/releases/tag/v0.1.0-rc2).
Choose the matching `.hex`; `companion-apb.tar.gz` supplies the APB Linux archive
service. Verify downloads with `SHA256SUMS`. These are hardware-unvalidated
bench-test builds.

Alternatively use the [latest successful Actions build](https://github.com/DroneWuKong/Orqa_Betaflight_Ports/actions/workflows/build.yml)
and download the matching firmware-<build-ID> artifact. GitHub sign-in is
required, and artifacts expire after 30 days. [Tagged prereleases](https://github.com/DroneWuKong/Orqa_Betaflight_Ports/releases)
appear only after manual approval.

Each artifact contains .hex, .bin, .elf, a provenance manifest and SHA256SUMS.
Prefer the .hex through Betaflight Configurator's local-firmware path.
**These images start at 0x08000000 and are not ArduPilot/PX4 application images.**
Changing firmware families can overwrite the installed bootloader and settings.
Back up first; do not send these through an ArduPilot/PX4 uploader.

## Build (Linux x86_64)

Pinned stable base: Betaflight 2026.6.2. The exact revision, compiler and targets
are in [upstream.lock.json](upstream.lock.json). Use a fresh source directory
per target to prevent stale objects crossing sensor variants.

From this repository root:

~~~sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-build.txt
python scripts/build.py toolchain work/tools
export PATH="$PWD/work/tools/arm-gnu-toolchain-13.3.rel1-x86_64-arm-none-eabi/bin:$PATH"
python scripts/build.py prepare work/h743
python scripts/build.py build work/h743 --target h743-icm42688
python scripts/build.py collect work/h743 --target h743-icm42688 --output artifacts/h743
python -m unittest discover -s tests -v
~~~

Requirements: Git, make, a host C compiler, tar/xz, Python and network access.
No sudo or flashing command is used. The toolchain installer refuses an existing
destination; reuse the installed bin directory rather than reinstalling.

## Logging

Betaflight uses Blackbox, not PX4 ULog. These configurations default to onboard
W25 flash. H743 SDMMC is configured but requires physical validation; APB has
no STM32 SD path. The [APB companion package](companion/apb/README.md) now
offloads onboard Blackbox flash through MSP to i.MX SD while disarmed. It uses
two full verification reads and never erases flash or changes FC settings.
This is post-flight archival, not live streaming or unlimited onboard capacity.
MSP replaces the old MAVLink UART use; review the bench-only migration and
rollback instructions before activation. The PX4 ULog recorder is not compatible.
