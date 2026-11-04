# MRM2-10 tuning recovery

This preset is derived from the exact reference unit's pre-update vendor
4.4.1 build 82c7bc9a4 configuration, not a manufacturer-wide factory download.
The full historical CLI SHA256 and sanitized tuning excerpt accompany it.
It is reviewed for `apb-dual-icm42605` at upstream 0db924466 (2026.6.3).
It must not be embedded as defaults for every H7/APB or other airframe.

The Nov. 4 reset discarded the aircraft's custom gains, D filters, input
smoothing and rates. Partial tuning around generic defaults did not restore
that package. New Acro logs showed no receiver loss/failsafe, pre-impact
roll activity, and post-tip-over rear-left RPM imbalance. The tune is not
proof that damaged props, motors or mounting have been repaired.

## Version mapping

Old `d_min_roll/pitch` 54/74 become base D. Old D 78/108 becomes D-max.
Roll P/I is 50/107; pitch 52/112; yaw 63/134. The PT3 D filter is 37-75 Hz,
with its second LPF disabled. The gyro filter is static PT2 300 Hz with its
second LPF disabled. RC setpoint and feedforward are both 12 Hz (one setting
in the current implementation), throttle 20 Hz. Actual rates are 530 deg/s
maximum with 70 deg/s center and zero expo. Modern feedforward/adaptive-D
algorithms remain modern; this is not bit-equivalent legacy firmware.

Raw gains and filters are explicit; automatic PID and D-filter sliders are
disabled to prevent regenerating a different package from modern defaults.
Unlisted modern settings are preserved. Motor output limits are not raised.
A blank destination name alone does not prove that profile is unused: review
both the plan and the baseline before applying it.

## Offline recovery

With the quad disarmed, props removed and propulsion battery disconnected,
identify the exact unit and installed sensor variant from its firmware
manifest and individual sensor checks. The planner's target argument is an
operator assertion; MCU/board_name alone cannot identify the sensor population.
Capture a fresh `dump all` as `before.cli.txt`; retain firmware recovery media.

```
python scripts/airframe_recovery.py plan --before before.cli.txt \
  --target apb-dual-icm42605 --output recovery
```

This command never connects to hardware. It creates a complete baseline,
reviewable `apply.cli.txt`, `rollback.cli.txt`, and `plan.json`. It rejects the
wrong upstream version, unsupported parameters, active/named destinations,
and presets containing hardware or authority changes. The default destination
is CLI PID profile 2 / UI Profile 3 and CLI rate profile 1 / UI Rate Profile 2.
Choose other inactive unnamed destinations explicitly if needed.

Review the plan, then apply the generated CLI only to the recorded MCU UID.
The master gyro/input filters affect **all** PID profiles; switching back to
an old PID profile is not a complete rollback. Use the full rollback file.
Never paste the historical tuning excerpt directly into current firmware.

After saving/restarting, capture a new complete dump as `after.cli.txt`:

```
python scripts/airframe_recovery.py verify --plan recovery/plan.json \
  --after after.cli.txt
```

Verification requires the same unit, firmware header, complete settings,
active selections and unchanged non-setting configuration. If USB stalls after
save, close the host connection, reconnect USB and read back; do not assume a
successful save or send repeated writes blindly.

## Evidence and remaining gate

The reference unit's 56 changed settings persisted after USB reconnection on
Nov. 4. Its verified dump SHA256 is
`5f2461f5e77cd47341f90eabf3413e2b22ffd356a6d594f1a74798eefadfdf90`.
Motor resources/reordering, corrected gyro setup, receiver/mode mappings,
calibration, reverse props, Blackbox and manual MSP authority were preserved.

Configuration readback is the completed gate. Following the logged impacts,
inspect the rear-left prop/motor and frame/FC mounting before a short controlled
Acro hover, motor-temperature check, and new Blackbox comparison. No flight
acceptance or ArduPilot compatibility is claimed by this preset.
