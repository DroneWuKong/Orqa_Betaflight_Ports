#!/usr/bin/env python3
"""Read-only, disarmed Betaflight Blackbox offload to the companion SD."""
import argparse
from functools import reduce
import hashlib
import operator
from pathlib import Path
import signal
import struct
import subprocess
import time

from storage import Store

API, VARIANT, SUMMARY, READ, STATUS, BOXIDS, UID = 1, 2, 70, 71, 101, 119, 160
READ_ONLY = {API, VARIANT, SUMMARY, READ, STATUS, BOXIDS, UID}


class Armed(RuntimeError):
    pass


def frame(command, payload=b"", direction=b"<"):
    if command not in READ_ONLY or len(payload) > 255:
        raise ValueError("only bounded read-only MSP commands are permitted")
    body = bytes([len(payload), command]) + payload
    return b"$M" + direction + body + bytes([reduce(operator.xor, body, 0)])


class MSP:
    def __init__(self, serial, timeout=1):
        self.serial, self.timeout = serial, timeout
        self.buffer = bytearray()

    def request(self, command, payload=b""):
        packet = frame(command, payload)
        for attempt in range(3):
            self.serial.write(packet)
            deadline = time.monotonic() + self.timeout
            while time.monotonic() < deadline:
                # read(256) waits for timeout on every smaller MSP reply.
                # Block for one byte when idle, otherwise drain only ready bytes.
                waiting = self.serial.in_waiting
                self.buffer.extend(self.serial.read(max(1, min(256, waiting))))
                while len(self.buffer) >= 6:
                    index = self.buffer.find(b"$M")
                    if index < 0:
                        self.buffer[:] = self.buffer[-1:]
                        break
                    del self.buffer[:index]
                    if len(self.buffer) < 6:
                        break
                    if self.buffer[2] not in (ord(">"), ord("!")):
                        del self.buffer[0]
                        continue
                    length = self.buffer[3]+6
                    if len(self.buffer) < length:
                        break
                    response = bytes(self.buffer[:length])
                    del self.buffer[:length]
                    if reduce(operator.xor, response[3:-1], 0) != response[-1]:
                        continue
                    if response[4] != command:
                        continue
                    if response[2] == ord("!"):
                        raise RuntimeError("MSP command rejected by firmware")
                    return response[5:-1]
            self.buffer.clear()
        raise TimeoutError("MSP response timeout or repeated checksum errors")


class Blackbox:
    def __init__(self, msp, store):
        self.msp, self.store = msp, store
        if msp.request(VARIANT) != b"BTFL":
            raise ValueError("not Betaflight; refusing wrong-firmware UART")
        api = msp.request(API)
        if len(api) != 3 or api[1] != 1 or api[2] < 43:
            raise ValueError("unsupported MSP API")
        self.api = list(api)
        self.uid = msp.request(UID)
        if len(self.uid) != 12 or self.uid == bytes(12):
            raise ValueError("missing device UID")
        boxes = msp.request(BOXIDS, b"\0")
        if boxes.count(0) != 1 or boxes.index(0) >= 32:
            raise ValueError("cannot locate ARM status bit")
        self.arm_bit = boxes.index(0)

    def disarmed(self):
        status = self.msp.request(STATUS)
        if len(status) < 11:
            raise ValueError("truncated MSP_STATUS")
        if struct.unpack_from("<I", status, 6)[0] & (1 << self.arm_bit):
            raise Armed("FC armed: Blackbox transfer suspended")

    def summary(self):
        self.disarmed()
        payload = self.msp.request(SUMMARY)
        if len(payload) != 13:
            raise ValueError("invalid flash summary")
        flags, sectors, total, used = struct.unpack("<BIII", payload)
        if flags & 3 != 3 or not sectors or not 0 < total <= 128*1024*1024 or used > total:
            raise RuntimeError("Blackbox flash unavailable, busy or invalid")
        return {"sectors": sectors, "total": total, "used": used}

    def chunk(self, offset, count):
        if not 0 <= offset < 128*1024*1024 or not 1 <= count <= 128:
            raise ValueError("invalid flash read")
        self.disarmed()
        self.store.check(count)
        reply = self.msp.request(READ, struct.pack("<IHB", offset, count, 0))
        if len(reply) < 7:
            raise ValueError("truncated flash reply")
        address, length, compression = struct.unpack_from("<IHB", reply)
        if address != offset or length != count or compression != 0 or len(reply) != 7+count:
            raise ValueError("mismatched, compressed or short flash reply")
        return reply[7:]

    def archive(self):
        initial = self.summary()
        size = initial["used"]
        if not size:
            return None
        self.store.check(size)
        with self.store.new("blackbox") as capture:
            for offset in range(0, size, 128):
                data = self.chunk(offset, min(128, size-offset))
                if offset == 0 and not data.startswith(b"H Product:Blackbox"):
                    raise ValueError("flash does not start with a Blackbox header")
                capture.append(data)
            capture.sync()
            verification = hashlib.sha256()
            for offset in range(0, size, 128):
                verification.update(self.chunk(offset, min(128, size-offset)))
            if verification.hexdigest() != capture.hash.hexdigest():
                raise ValueError("flash changed between verification reads")
            if self.summary() != initial or self.msp.request(UID) != self.uid:
                raise ValueError("FC identity or flash inventory changed during archive")
            return capture.finish("bbl", {"kind": "blackbox-flash-archive", "complete": True,
                "uid": self.uid.hex(), "msp_api": self.api, "flash": initial,
                "verification": "two full reads with matching SHA256 and stable flash inventory",
                "scope": "entire used flash volume; can contain multiple flights; not live streaming"})


def ensure_uart_available():
    # Do not stop another telemetry process just to acquire its UART.
    for unit in ("mavlink-router.service", "orqa-px4-recorder.service", "orqa-ardupilot-recorder.service"):
        status = subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True)
        if status.stdout.strip() not in ("inactive", "failed", "unknown"):
            raise RuntimeError("stop/reconfigure competing service on the bench first: " + unit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mount", type=Path, default=Path("/sdcard"))
    parser.add_argument("--device", default="/dev/ttymxc2")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--reserve-mib", type=int, default=256)
    parser.add_argument("--watch", action="store_true", help="archive at startup and after observed armed-to-disarmed transitions")
    parser.add_argument("--check", action="store_true", help="storage preflight only; do not open UART")
    args = parser.parse_args()
    if args.reserve_mib < 1 or args.baud not in (115200, 230400, 460800, 921600):
        parser.error("invalid reserve or baud")
    stopped = False
    def stop(*unused):
        nonlocal stopped
        stopped = True
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with Store(args.mount, "betaflight", "archive", args.reserve_mib*1024*1024) as store:
        if args.check:
            print("SD storage ready; UART and firmware not tested")
            return
        ensure_uart_available()
        import serial
        with serial.Serial(args.device, args.baud, timeout=0.05, write_timeout=1, exclusive=True) as uart:
            blackbox = Blackbox(MSP(uart), store)
            pending, disarmed_since = True, None
            while not stopped:
                store.check()
                try:
                    blackbox.disarmed()
                    if disarmed_since is None:
                        disarmed_since = time.monotonic()
                    if pending and (not args.watch or time.monotonic()-disarmed_since >= 10):
                        print(blackbox.archive() or "Blackbox flash empty", flush=True)
                        pending = False
                    if not args.watch:
                        return
                except Armed:
                    if not args.watch:
                        raise
                    pending, disarmed_since = True, None
                time.sleep(1)


if __name__ == "__main__":
    main()
