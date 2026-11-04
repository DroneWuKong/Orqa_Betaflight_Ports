import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "configs/ORQA/ORQA_APB/config.h"
FACTORY = json.loads((ROOT / "tests/fixtures/apb-dual-icm42605-factory.json").read_text())


def preprocess(*flags, macros=True):
    cmd = ["gcc", "-E", "-x", "c", *flags]
    if macros:
        cmd += ["-dM", str(HEADER)]
        text = subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE)
        return dict(re.findall(r"^#define (\w+) ?(.*)$", text, re.M))
    text = '#include "' + str(HEADER) + '"\nTIMER_PIN_MAPPING\n'
    return subprocess.check_output(cmd + ["-"], input=text, text=True, stderr=subprocess.PIPE)


class DualIcm42605Tests(unittest.TestCase):
    def test_sensor_rotations_match_exact_unit_backup(self):
        m = preprocess("-DORQA_APB_IMU_DUAL_ICM42605")
        self.assertEqual([m["GYRO_1_ALIGN"], m["GYRO_2_ALIGN"]], FACTORY["gyro_align"])
        self.assertIn("USE_GYRO_SPI_ICM42605", m)
        self.assertNotIn("USE_GYRO_SPI_MPU6000", m)

    def test_factory_output_pins_and_per_pin_timer_dma(self):
        m = preprocess("-DORQA_APB_IMU_DUAL_ICM42605")
        self.assertEqual([m[f"MOTOR{i}_PIN"] for i in range(1, 9)], FACTORY["pins"])
        expanded = preprocess("-DORQA_APB_IMU_DUAL_ICM42605", macros=False)
        mappings = re.findall(r"TIMER_PIN_MAP\(\s*(\d+),\s*(P[A-Z]\d+),\s*(\d+),\s*(-?\d+)\)", expanded)
        for i, (index, pin, occurrence, dma) in enumerate(mappings[:8]):
            self.assertEqual(int(index), i)
            self.assertEqual(pin, FACTORY["pins"][i])
            self.assertEqual(int(occurrence), FACTORY["timer_occurrences"][i])
            self.assertEqual(int(dma), FACTORY["dma_options"][i])
        self.assertEqual(len(mappings), 11)

    def test_prior_populations_unchanged(self):
        old = preprocess()
        later = preprocess("-DORQA_APB_IMU_ICM42688P")
        self.assertEqual(old["GYRO_2_ALIGN"], "CW0_DEG_FLIP")
        self.assertEqual(later["GYRO_2_ALIGN"], "CW90_DEG_FLIP")
        self.assertEqual(old["MOTOR3_PIN"], "PA1")
        self.assertEqual(later["MOTOR3_PIN"], "PA1")

    def test_conflicting_populations_rejected(self):
        with self.assertRaises(subprocess.CalledProcessError):
            preprocess("-DORQA_APB_IMU_DUAL_ICM42605", "-DORQA_APB_IMU_ICM42688P")

    def test_airframe_reorder_preserves_owner_confirmed_corners(self):
        pins = FACTORY["pins"]
        ordered = [pins[i] for i in FACTORY["installed_airframe_motor_output_reordering"][:4]]
        self.assertEqual(ordered, ["PB1", "PB0", "PD13", "PD12"])


if __name__ == "__main__":
    unittest.main()
