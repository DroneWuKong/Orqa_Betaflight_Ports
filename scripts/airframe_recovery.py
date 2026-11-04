#!/usr/bin/env python3
"""Offline tuning recovery planner/verifier. Never opens a port or flashes."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PRESET = ROOT / "presets/mrm2-10/2026.6.3.json"
MASTER = set("gyro_lpf1_type gyro_lpf1_static_hz gyro_lpf2_static_hz gyro_lpf1_dyn_min_hz gyro_lpf1_dyn_max_hz dyn_notch_count dyn_notch_q dyn_notch_min_hz dyn_notch_max_hz rc_smoothing rc_smoothing_auto_factor rc_smoothing_auto_factor_throttle rc_smoothing_setpoint_cutoff rc_smoothing_throttle_cutoff simplified_gyro_filter simplified_gyro_filter_multiplier".split())
PROFILE = set("profile_name dterm_lpf1_dyn_min_hz dterm_lpf1_dyn_max_hz dterm_lpf1_type dterm_lpf1_static_hz dterm_lpf2_static_hz anti_gravity_gain iterm_relax_cutoff pidsum_limit pidsum_limit_yaw yaw_lowpass_hz p_pitch i_pitch d_pitch f_pitch p_roll i_roll d_roll f_roll p_yaw i_yaw d_yaw f_yaw d_max_roll d_max_pitch d_max_yaw d_max_gain feedforward_smooth_factor feedforward_jitter_factor feedforward_boost simplified_pids_mode simplified_master_multiplier simplified_i_gain simplified_d_gain simplified_pi_gain simplified_d_max_gain simplified_pitch_d_gain simplified_dterm_filter_multiplier simplified_dterm_filter".split())
RATE = set("rateprofile_name rates_type roll_srate pitch_srate yaw_srate roll_rc_rate pitch_rc_rate yaw_rc_rate roll_expo pitch_expo yaw_expo".split())
SCOPES = {"master": MASTER, "profile": PROFILE, "rateprofile": RATE}


def dump(text):
    if "###ERROR" in text:
        raise ValueError("Snapshot contains a CLI error")
    uid = re.search(r"^#?\s*mcu_id ([0-9a-fA-F]{24})\s*$", text, re.M)
    board = re.search(r"^board_name (\S+)", text, re.M)
    if not uid or not board:
        raise ValueError("Full snapshot must include MCU identity and board_name")
    settings, other, scope = {}, [], "master"
    for line in text.splitlines():
        if re.fullmatch(r"(profile|rateprofile|battery_profile) \d+", line):
            scope = line
        elif line.startswith("set "):
            match = re.fullmatch(r"set (\w+) = (.*)", line)
            if not match:
                raise ValueError("Malformed setting")
            key = scope + ":" + match[1]
            if key in settings:
                raise ValueError("Use one complete dump, not joined transcripts")
            settings[key] = match[2]
        elif line and not line.startswith("#") and line not in ("dump all", "save", "batch start", "batch end"):
            other.append(line)
    selected = {}
    for kind in ("profile", "rateprofile"):
        match = re.search(r"# restore original " + kind + r" selection\n" + kind + r" (\d+)\n", text)
        if not match:
            raise ValueError("Use dump all including active profile selections")
        selected[kind] = int(match[1])
    return dict(uid=uid[1].lower(), board=board[1], firmware_header=next((line for line in text.splitlines() if "# Betaflight /" in line), ""), settings=settings,
                other=other, selected=selected)


def validate_preset(preset):
    if preset.get("schema_version") != 1 or set(preset.get("settings", {})) != set(SCOPES):
        raise ValueError("Invalid preset schema")
    for scope, values in preset["settings"].items():
        if not values or not set(values) <= SCOPES[scope]:
            raise ValueError("Preset contains unsupported or hardware/authority settings")
        for key, value in values.items():
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
                raise ValueError("Invalid CLI value for " + key)
            if key.endswith("profile_name") and not 1 <= len(value) <= 8:
                raise ValueError("Profile names must fit firmware's eight-character limit")


def plan(text, preset, target, pid=2, rate=1):
    validate_preset(preset)
    before = dump(text)
    if target != preset["target"] or before["board"] != preset["board"]:
        raise ValueError("Board/sensor target mismatch")
    header = next((line for line in text.splitlines() if "# Betaflight /" in line), "")
    if (not re.search(r"\b" + re.escape(preset["firmware_version"]) + r"\b", header)
            or preset["upstream_short_revision"] not in header):
        raise ValueError("Preset requires its reviewed firmware version and revision")
    if not 0 <= pid <= 3 or not 0 <= rate <= 3:
        raise ValueError("Profile index out of range")
    if pid == before["selected"]["profile"] or rate == before["selected"]["rateprofile"]:
        raise ValueError("Use inactive profiles to preserve the current tune")
    for scope, name in ((f"profile {pid}", "profile_name"), (f"rateprofile {rate}", "rateprofile_name")):
        if before["settings"].get(scope + ":" + name) != "-":
            raise ValueError("Destination profile must exist and be unnamed; preserve named profiles")
    after = json.loads(json.dumps(before))
    commands, rollback, changed = [], [], []
    for group, scope in (("master", "master"), ("profile", f"profile {pid}"), ("rateprofile", f"rateprofile {rate}")):
        values = preset["settings"][group]
        # Freeze explicit coefficients before writing them, even on legacy profiles.
        ordered = sorted(values, key=lambda name: (name not in {"simplified_gyro_filter", "simplified_pids_mode", "simplified_dterm_filter"}, name))
        if group != "master":
            commands.append(scope)
            rollback.append(scope)
        for name in ordered:
            value = values[name]
            key = scope + ":" + name
            if key not in before["settings"]:
                raise ValueError("Missing supported setting; snapshot incomplete or incompatible: " + key)
            if before["settings"][key] == value:
                continue
            commands.append(f"set {name} = {value}")
            rollback.append(f"set {name} = {before['settings'][key]}")
            after["settings"][key] = value
            changed.append(dict(scope=scope, name=name, before=before["settings"][key], after=value))
    after["selected"] = dict(profile=pid, rateprofile=rate)
    commands += [f"profile {pid}", f"rateprofile {rate}", "save"]
    rollback += [f"profile {before['selected']['profile']}", f"rateprofile {before['selected']['rateprofile']}", "save"]
    return dict(schema_version=1, preset=preset["id"], target=target, unit_uid=before["uid"],
                qualification=preset["qualification"], before=before, expected=after,
                changes=changed, commands=commands, rollback=rollback)


def verify(receipt, text):
    actual = dump(text)
    if actual != receipt["expected"]:
        wrong = [key for key, value in receipt["expected"]["settings"].items()
                 if actual["settings"].get(key) != value]
        raise ValueError("Saved configuration/identity/mapping differs from plan: " + ", ".join(wrong[:12]))
    return dict(configuration_verified=True, unit_uid=actual["uid"],
                flight_validated=False, authority_and_hardware_changes=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    make = subs.add_parser("plan")
    make.add_argument("--before", type=Path, required=True)
    make.add_argument("--target", required=True)
    make.add_argument("--output", type=Path, required=True)
    make.add_argument("--pid-profile", type=int, default=2)
    make.add_argument("--rate-profile", type=int, default=1)
    check = subs.add_parser("verify")
    check.add_argument("--plan", type=Path, required=True)
    check.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "plan":
        result = plan(args.before.read_text(), json.loads(PRESET.read_text()), args.target,
                      args.pid_profile, args.rate_profile)
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "before.cli.txt").write_text(args.before.read_text())
        (args.output / "plan.json").write_text(json.dumps(result, indent=2) + "\n")
        (args.output / "apply.cli.txt").write_text("\n".join(result["commands"]) + "\n")
        (args.output / "rollback.cli.txt").write_text("\n".join(result["rollback"]) + "\n")
        print(json.dumps(dict(changed_settings=len(result["changes"]), unit_uid=result["unit_uid"],
                              output=str(args.output), device_written=False)))
    else:
        print(json.dumps(verify(json.loads(args.plan.read_text()), args.after.read_text())))


if __name__ == "__main__":
    main()
