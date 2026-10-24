# APB Blackbox archive to i.MX microSD

**Start here:** [one-command setup and status](QUICKSTART.md). The common
`easy.py` tool handles dependencies, installation and explicit bench activation.
The detailed manual procedure below remains available.

This package automatically copies Betaflight's onboard Blackbox flash to the
Linux-owned SD **while disarmed**. It implements MSP framing/checksums, validates
BTFL firmware identity/API/device UID, locates the actual ARM mode bit, checks
every read address/length, reads the whole used flash twice, and requires matching
SHA256 plus unchanged flash inventory before publishing a `.bbl` and JSON receipt.
The dump can contain multiple flights and can be opened with Blackbox tools.

This is **post-flight offload, not live streaming or direct STM32 SD access**.
Onboard W25 capacity remains finite. It never erases flash, changes configuration,
disables arming, formats media or deletes old logs. Export/erase onboard logs
manually only after verifying your backups. Compilation is not hardware validation.

## Firmware and transport

New APB defaults enable MSP on UART4 PC10/PC11 at upstream's default 115200 baud.
Existing saved settings are not overwritten: verify UART4 MSP in Configurator's
Ports tab and keep `blackbox_device=FLASH`. The companion side is `/dev/ttymxc2`.
The program issues only MSP 1, 2, 70, 71, 101, 119 and 160. No write commands.

MSP is **not MAVLink**. Stop/reconfigure `mavlink-router.service` and any PX4 or
ArduPilot recorder **on the bench before changing firmware family**. Do not
stop telemetry services in flight. The archive refuses to open its UART while
those services are active, and pyserial requests exclusive access. Also check
for other UART owners with `fuser /dev/ttymxc2`; exclusive locking cannot protect
against every unrelated program that ignores locks. A dedicated MSP UART cannot
simultaneously be used by the old MAVLink telemetry path.

## Installation

Use `companion-apb.tar.gz` plus `SHA256SUMS` from this repository's tagged
prerelease, or this directory at the matching source commit. Verify the archive
checksum before extraction. Requires Python 3.10+, Linux/glibc with renameat2,
systemd and an SD filesystem with fsync/atomic rename. FAT/exFAT are supported
without requiring hard links. From the extracted directory or `companion/apb`:

```sh
sudo python3 -m venv /opt/orqa-betaflight-logger/venv
sudo /opt/orqa-betaflight-logger/venv/bin/pip install -r requirements.txt
sudo python3 install.py --repair-vendor-mount
```

Mount repair is optional and accepts only the inspected Scarthgap v1.0.5 vendor
helper SHA256 `501cf034fb6afb04f4fb8036139ab9b131d005c19863d522c95a76d8616452f6`.
It keeps `/etc/udev/scripts/orqa-drive-mounting.sh.pre-orqa-logging`, repairs the
SD-only synchronous mount path and preserves vendor USB handling. If the PX4
or ArduPilot package already repaired mounting, keep that repair and **omit**
`--repair-vendor-mount`. Unknown/custom destination files are rejected before
writes. `--root /path/to/staging-root` supports image staging. Installation
does not enable/restart services, touch FC settings or install dependencies.

After confirming the expected UART/firmware and stopping competing UART users:

```sh
sudo systemctl daemon-reload
sudo /opt/orqa-betaflight-logger/venv/bin/python /usr/local/lib/orqa-betaflight/archive.py --check
sudo systemctl enable --now orqa-betaflight-archive.service
journalctl -u orqa-betaflight-archive -f
```

`--check` only validates SD storage. The service waits ten seconds continuously
disarmed, archives once at startup and again after each observed armed→disarmed
transition. It checks arming before **every** 128-byte flash read and aborts on
arming; this is not an arming interlock, so don't intentionally arm during an
offload. It never reads flash while its latest status reports armed. Status
queries continue while waiting. Timeouts/restarts preserve partial files.

For a manual one-shot archive, stop the archive service and run `archive.py`
without `--watch`. Full two-pass offloads may take many minutes at 115200 baud;
wait for the receipt. Faster UART rates require configuring both ends and bench
testing. Override the unit's ExecStart with matching `--baud`/`--device` if needed.

## Storage and recovery

Files live in `/sdcard/betaflight`. A real read-write SD mount is required;
a directory is not enough. The guard rejects root/eMMC/symlinks, pins the open
filesystem, reserves 256 MiB, detects replacement/removal and refuses additional
writes when space is low. A lock prevents duplicate archive workers. No files
are deleted for retention. Repeated cycles retain separate archive copies.

`.partial` means unfinished; no complete receipt is issued for it. A finalized
`.bbl` has a JSON receipt with byte count, SHA256, UID, API and flash geometry.
`complete: true` describes the verified used-flash snapshot, **not** proof that
the FC recorded every sample or that a flight was safe. Device restart/change,
inventory changes, short/compressed replies and mismatched second reads all fail.

Only treat a capture as finalized when its matching JSON receipt exists and
the checksum matches. Receipt publication happens last; a crash may leave a
data file with only `.json.partial` metadata. Keep it for inspection rather
than treating it as verified. This package is GPL-3.0-or-later; see COPYING.

If mounting fails, fix the actual SD mount rather than creating a fallback log
directory. If no MSP reply arrives, check UART ownership, baud, UART4 MSP and
firmware identity. The service never stops other processes to acquire the UART.
If flash is full, preserve/verify the offload before manually erasing it through
Configurator. If SD is full, export older captures; the service will not choose
which data to delete. Inspect `.partial` files before any manual cleanup.

Rollback: disable/stop `orqa-betaflight-archive.service`; restore your saved
UART/Blackbox settings if needed. Keep logs and the shared SD repair. To undo
the mount repair, restore only the verified `.pre-orqa-logging` helper backup
while disarmed, and only if no other recorder needs it. Re-enable a MAVLink
router only after changing the FC back to compatible firmware/serial settings.

## Validation

For exact disarmed logging acceptance and evidence, use
[BENCH_ACCEPTANCE.md](BENCH_ACCEPTANCE.md).

Run `python -m unittest discover -s tests -v` from the repository. Host tests
exercise fragmented/corrupt MSP replies, readonly-command enforcement, wrong
firmware/UID, re-arming mid-transfer, changed flash data, short writes, fsync
failure, low space, duplicate workers and mount changes. These are not physical
serial/SD tests. On the APB with props off, compare a saved `.bbl` with a separate
Configurator flash download, open it in Blackbox Explorer and verify receipt
SHA256. Test power cycles, no-card boot, controlled media failures and telemetry
coexistence with sacrificial media. Retain actual evidence before flight use.

Protocol evidence: [pinned MSP implementation](https://github.com/betaflight/betaflight/blob/e0b7bb01b17b21351057e9ead2d1ab39dd44fa16/src/main/msp/msp.c),
[ARM status mapping](https://github.com/betaflight/betaflight/blob/e0b7bb01b17b21351057e9ead2d1ab39dd44fa16/src/main/msp/msp_box.c),
[UART defaults](https://github.com/betaflight/betaflight/blob/e0b7bb01b17b21351057e9ead2d1ab39dd44fa16/src/main/io/serial.c).
