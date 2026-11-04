# Dual-ICM42605 APB correction

This is a separate population from MPU6000 + ICM42605 and dual ICM42688P.
It is based on the pre-update Betaflight 4.4.1 configuration of FC UID
`002c00323533510433373532`; the immutable backup SHA256 is recorded in the
fixture. Both ICM42605 sensors were detected on this unit. Gyro 2 is
`CW270FLIP`, not the legacy target's `CW0FLIP`. Averaging those misaligned
sensors mixes roll and pitch. The original motor resources also place the
four connected outputs on PD12, PD13, PB1, PB0, rather than PA1/PA0.

Build only with `upstream-apb-dual-icm42605.lock.json` and target
`apb-dual-icm42605`. It pins the same approved 2026.6.3 source as the installed
firmware. Existing variants are unchanged. A full configuration reset after
flashing is required to reset the hidden gyro-device parameter group.
Restore compatible setup selectively; do not restore that old parameter group.

Whole-board roll is separate: the owner corrected it to zero for this mounting.
Keep zero. The owner-confirmed motor corners on this installed frame are
PB1=RR, PB0=FR, PD13=RL, PD12=FL. With the recovered factory resource slots,
this corresponds to `motor_output_reordering = 2,3,1,0,4,5,6,7`.
The old factory reorder belongs to the original mounting/wiring and must not
replace these observations. Reverse-prop mode remains enabled.

Host checks/builds do not prove physical output or flight readiness. Verify
all four positions/directions and both gyro body axes props-off after install.
