import copy
import importlib.util
import json
from pathlib import Path
import re
import unittest
import tempfile
from unittest.mock import patch, call

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("recovery", ROOT / "scripts/airframe_recovery.py")
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)
PRESET = json.loads(recovery.PRESET.read_text())


def snapshot():
    lines = ["# Betaflight / STM32H743 2026.6.3 (0db924466)", "board_name ORQA_APB",
             "# mcu_id 000000000000000000000001", "resource MOTOR 1 D12", "serial 2 64 115200 57600 0 115200",
             "map AETR1234", "aux 0 0 0 1700 2100 0 0", "set acc_calibration = 17,22,-31,1",
             "set motor_output_reordering = 2,3,1,0,4,5,6,7", "set msp_override_channels_mask = 0"]
    for name,value in PRESET["settings"]["master"].items():
        lines.append(f"set {name} = {value}")
    for index in range(4):
        lines.append(f"profile {index}")
        for name,value in PRESET["settings"]["profile"].items():
            value = "-" if name == "profile_name" else "30" if name == "d_roll" else "RP" if name == "simplified_pids_mode" else value
            lines.append(f"set {name} = {value}")
    lines += ["# restore original profile selection", "profile 1"]
    for index in range(4):
        lines.append(f"rateprofile {index}")
        for name,value in PRESET["settings"]["rateprofile"].items():
            value = "-" if name == "rateprofile_name" else "67" if name.endswith("_srate") else value
            lines.append(f"set {name} = {value}")
    lines += ["# restore original rateprofile selection", "rateprofile 0", ""]
    return "\n".join(lines)


def render(state):
    lines = [state["firmware_header"], "# mcu_id " + state["uid"], *state["other"]]
    scope = "master"
    for key,value in state["settings"].items():
        new_scope,name = key.split(":",1)
        if new_scope != scope:
            lines.append(new_scope)
            scope = new_scope
        lines.append(f"set {name} = {value}")
    for kind in ("profile", "rateprofile"):
        lines += [f"# restore original {kind} selection", f"{kind} {state['selected'][kind]}"]
    return "\n".join(lines)+"\n"


class RecoveryTests(unittest.TestCase):
    def plan(self, text=None, preset=None, **kwargs):
        return recovery.plan(text or snapshot(), preset or PRESET, "apb-dual-icm42605", **kwargs)

    def test_restore_d_min_as_base_and_old_d_as_peak(self):
        historical=(ROOT/"presets/mrm2-10/reference-tuning-only.cli.txt").read_text()
        values=dict(re.findall(r"^set (\w+) = (.*)$", historical,re.M))
        result=self.plan()
        for axis in ("roll","pitch"):
            self.assertEqual(result["expected"]["settings"][f"profile 2:d_{axis}"],values[f"d_min_{axis}"])
            self.assertEqual(result["expected"]["settings"][f"profile 2:d_max_{axis}"],values[f"d_{axis}"])
        self.assertEqual(result["expected"]["settings"]["profile 2:dterm_lpf1_type"],"PT3")
        self.assertEqual(result["expected"]["settings"]["rateprofile 1:roll_srate"],"53")

    def test_preserve_hardware_authority_calibration_and_other_profiles(self):
        result=self.plan()
        before=result["before"];after=result["expected"]
        for key,value in before["settings"].items():
            if not key.startswith(("master:","profile 2:","rateprofile 1:")):
                self.assertEqual(after["settings"][key],value)
        self.assertEqual(after["settings"]["master:acc_calibration"],"17,22,-31,1")
        self.assertEqual(after["settings"]["master:msp_override_channels_mask"],"0")
        self.assertEqual(after["settings"]["master:motor_output_reordering"],before["settings"]["master:motor_output_reordering"])
        self.assertEqual(after["other"],before["other"])
        self.assertFalse(any(command.startswith(("resource ","aux ","map ","defaults","motor ")) for command in result["commands"]))

    def test_rollback_restores_global_filters_and_selections(self):
        text=snapshot().replace("set gyro_lpf1_static_hz = 300","set gyro_lpf1_static_hz = 250")
        result=self.plan(text)
        self.assertIn("set gyro_lpf1_static_hz = 250",result["rollback"])
        self.assertEqual(result["rollback"][-3:],["profile 1","rateprofile 0","save"])
        self.assertLess(result["commands"].index("set simplified_pids_mode = OFF"),result["commands"].index("set d_roll = 54"))

    def test_verify_cold_readback_without_claiming_flight_acceptance(self):
        result=self.plan()
        check=recovery.verify(result,render(result["expected"]))
        self.assertTrue(check["configuration_verified"])
        self.assertFalse(check["flight_validated"])

    def test_verify_rejects_wrong_unit_firmware_wiring_and_unrelated_change(self):
        result=self.plan();text=render(result["expected"])
        for bad in [text.replace("000000000000000000000001","000000000000000000000002"),
                    text.replace("0db924466","different"),text.replace("resource MOTOR 1 D12","resource MOTOR 1 A00"),
                    text.replace("set acc_calibration = 17,22,-31,1","set acc_calibration = 0,0,0,0")]:
            with self.subTest(bad=bad[:50]),self.assertRaises(ValueError):recovery.verify(result,bad)

    def test_reject_wrong_target_and_version(self):
        with self.assertRaises(ValueError):recovery.plan(snapshot(),PRESET,"apb-mpu6000-icm42605")
        with self.assertRaises(ValueError):self.plan(snapshot().replace("2026.6.3","2026.6.2"))

    def test_refuse_to_overwrite_active_or_named_profiles(self):
        with self.assertRaises(ValueError):self.plan(pid=1)
        text=snapshot()
        before=recovery.dump(text);before["settings"]["profile 2:profile_name"]="USER"
        with self.assertRaises(ValueError):self.plan(render(before))

    def test_preset_cannot_modify_motors_or_authority_or_inject_cli(self):
        for scope,key,value in [("master","motor_output_reordering","0,1,2,3,4,5,6,7"),
                                ("master","msp_override_channels_mask","3"),
                                ("profile","profile_name","X\nsave"),
                                ("profile","profile_name","TOO_LONG_NAME")]:
            preset=copy.deepcopy(PRESET);preset["settings"][scope][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.plan(preset=preset)

    def test_reject_incomplete_or_joined_snapshots(self):
        with self.assertRaises(ValueError):self.plan(snapshot().replace("set gyro_lpf1_type = PT2\n", ""))
        with self.assertRaises(ValueError):self.plan(snapshot()+snapshot())



class PinnedPrepareTests(unittest.TestCase):
    def module(self):
        spec=importlib.util.spec_from_file_location("pinned_build",ROOT/"scripts/build.py")
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def test_new_moving_branch_clone_fetches_and_detaches_pinned_commit(self):
        build=self.module()
        config={"revision":"a"*40,"tag":"maintenance","repository":"betaflight/betaflight","kind":"betaflight"}
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/"source"
            with patch.object(build,"run",return_value="b"*40) as run,patch.object(build,"verify_revision") as verify:
                build.prepare(source,config)
            self.assertIn(call("git","fetch","--depth","1","origin","a"*40,cwd=source),run.call_args_list)
            self.assertIn(call("git","checkout","--detach","a"*40,cwd=source),run.call_args_list)
            verify.assert_called_once_with(source,config)

    def test_existing_wrong_checkout_is_not_rewritten(self):
        build=self.module()
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)
            with patch.object(build,"run",return_value="b"*40) as run,self.assertRaises(ValueError):
                build.prepare(source,{"revision":"a"*40})
            self.assertFalse(any(args.args[:2] in (("git","fetch"),("git","checkout")) for args in run.call_args_list))


if __name__ == "__main__":unittest.main()
