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
Every target is built against both supported upstream lines: Betaflight
2026.6.2 and 2025.12.5. The 2025.12 artifacts are prefixed `2025.12.5-` so
firmware from the two lines cannot silently overwrite or masquerade as each
other.
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

## Easy APB logging setup

See the [APB quick start](companion/apb/QUICKSTART.md): one setup command, then
`status` and `logs`. Use the matching companion package on the i.MX; flashing
the FC alone does not install Linux logging. Older tagged bundles without
`easy.py` require the current source/CI package.

## Downloads

Persistent downloads: [v0.1.0-rc3 prerelease](https://github.com/DroneWuKong/Orqa_Betaflight_Ports/releases/tag/v0.1.0-rc3).
Choose the matching `.hex`; `companion-apb.tar.gz` supplies the APB Linux archive
service. Verify downloads with `SHA256SUMS`. That prerelease predates the
2025.12 compatibility line and contains only the default 2026.6 builds; use a
newer verified CI run or prerelease for 2025.12 artifacts. These are
hardware-unvalidated bench-test builds.

Alternatively use the [latest successful Actions build](https://github.com/DroneWuKong/Orqa_Betaflight_Ports/actions/workflows/build.yml)
and download the matching firmware-<build-ID> artifact. GitHub sign-in is
required, and artifacts expire after 30 days. [Tagged prereleases](https://github.com/DroneWuKong/Orqa_Betaflight_Ports/releases)
appear only after manual approval.

Each artifact contains .hex, .bin, .elf, a provenance manifest and SHA256SUMS.
Prefer the .hex through Betaflight Configurator's local-firmware path.
**These images start at 0x08000000 and are not ArduPilot/PX4 application images.**
Changing firmware families can overwrite the installed bootloader and settings.
Back up first; do not send these through an ArduPilot/PX4 uploader.

## Supported Betaflight lines

| Series | Pinned release | Lock | Artifact naming |
|---|---|---|---|
| 2026.6 (default) | 2026.6.2 | `upstream.lock.json` | `<target>.*` |
| 2025.12 | 2025.12.5 | `upstream-2025.12.lock.json` | `2025.12.5-<target>.*` |

Both lock files pin the exact source revision and verified compiler. CI builds
all five targets from both locks. The older line is deliberately explicit;
omitting `--lock` continues to select the default 2026.6 line.

## Build (Linux x86_64)

Pinned default base: Betaflight 2026.6.2. The exact revisions, compiler and
targets are in `upstream*.lock.json`. Use a fresh source directory per target
and upstream line to prevent stale objects crossing sensor variants.

From this repository root:

~~~sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-build.txt -r companion/apb/requirements.txt
python scripts/build.py toolchain work/tools
export PATH="$PWD/work/tools/arm-gnu-toolchain-13.3.rel1-x86_64-arm-none-eabi/bin:$PATH"
python scripts/build.py prepare work/h743
python scripts/build.py build work/h743 --target h743-icm42688
python scripts/build.py collect work/h743 --target h743-icm42688 --output artifacts/h743
python -m unittest discover -s tests -v
~~~

To build the matching 2025.12.5 image, use a different source/output directory
and pass its lock to every action:

~~~sh
python scripts/build.py prepare work/2025.12-h743 --lock upstream-2025.12.lock.json
python scripts/build.py build work/2025.12-h743 --target h743-icm42688 --lock upstream-2025.12.lock.json
python scripts/build.py collect work/2025.12-h743 --target h743-icm42688 --lock upstream-2025.12.lock.json --output artifacts/2025.12-h743
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
