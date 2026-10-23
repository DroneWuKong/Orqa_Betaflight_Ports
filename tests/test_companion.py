import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

COMPANION = Path(__file__).resolve().parents[1] / "companion/apb"
sys.path.insert(0, str(COMPANION))
import storage


class StorageFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        device = self.path.stat().st_dev
        self.identity = ("42", f"{os.major(device)}:{os.minor(device)}")
        self.identity_patch = patch.object(storage, "card_identity", return_value=self.identity)
        self.identity_mock = self.identity_patch.start()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.identity_patch.stop)

    def store(self):
        return storage.Store(self.path, "ardupilot", "archive", 0)


class StorageTests(StorageFixture):
    def test_mount_directory_is_not_mount(self):
        with self.assertRaises(storage.NotReady):
            storage.mount_record("1 0 8:1 / / rw - ext4 /dev/sda rw", Path("/sdcard"))

    def test_readonly_mount_rejected(self):
        for options, super_options in (("ro", "rw"), ("rw", "ro")):
            with self.assertRaises(storage.NotReady):
                storage.mount_record(f"1 0 8:1 / /sdcard {options} - vfat /dev/mmcblk1p1 {super_options}", Path("/sdcard"))

    def test_mount_identity(self):
        self.assertEqual(storage.mount_record("41 0 179:1 / /sdcard rw - vfat /dev/mmcblk1p1 rw", Path("/sdcard")), ("41", "179:1"))

    def test_symlink_log_directory_rejected(self):
        (self.path / "ardupilot").symlink_to(self.path, target_is_directory=True)
        with self.assertRaises(OSError):
            self.store()

    def test_duplicate_writer_rejected(self):
        with self.store():
            with self.assertRaises(BlockingIOError):
                self.store()

    def test_mount_replacement_rejected(self):
        with self.store() as store:
            self.identity_mock.return_value = ("43", self.identity[1])
            with self.assertRaises(storage.NotReady):
                store.new("dataflash")

    def test_low_space(self):
        with self.store() as store:
            with self.assertRaises(storage.NotReady):
                store.check(2**63)

    def test_commit_receipt_and_bytes(self):
        with self.store() as store, store.new("dataflash") as capture:
            capture.append(b"verified bytes")
            receipt = capture.finish("bin", {"complete": True})
            output = self.path / "ardupilot" / receipt["file"]
            self.assertEqual(output.read_bytes(), b"verified bytes")
            self.assertEqual(receipt["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
            self.assertEqual(json.loads(output.with_suffix(".bin.json").read_text()), receipt)
            self.assertFalse(receipt["hardware_validated"])

    def test_failed_capture_stays_partial(self):
        with self.store() as store, store.new("dataflash") as capture:
            name = capture.name
            capture.append(b"partial")
        self.assertEqual((self.path / "ardupilot" / name).read_bytes(), b"partial")
        self.assertFalse(list((self.path / "ardupilot").glob("*.bin")))

    def test_fsync_failure_cannot_complete(self):
        with self.store() as store, store.new("dataflash") as capture:
            capture.append(b"partial")
            with patch.object(storage.os, "fsync", side_effect=OSError("media failure")):
                with self.assertRaises(OSError):
                    capture.finish("bin", {"complete": True})
        self.assertFalse(list((self.path / "ardupilot").glob("*.bin")))

    def test_short_writes_are_completed(self):
        write = os.write
        with self.store() as store, store.new("dataflash") as capture:
            with patch.object(storage.os, "write", side_effect=lambda fd, data: write(fd, data[:2])):
                capture.append(b"abcdef")
            self.assertEqual(os.pread(capture.fd, 6, 0), b"abcdef")

    def test_existing_output_never_overwritten(self):
        with self.store() as store, store.new("dataflash") as capture:
            final = self.path / "ardupilot" / (capture.name.removesuffix(".partial") + ".bin")
            final.write_bytes(b"keep")
            capture.append(b"new")
            with self.assertRaises(FileExistsError):
                capture.finish("bin", {})
            self.assertEqual(final.read_bytes(), b"keep")


class FakeSerial:
    def __init__(self, data, armed=False, mutate=False, corrupt=False):
        self.data, self.armed, self.mutate, self.corrupt = data, armed, mutate, corrupt
        self.output = bytearray()
        self.reads = 0
        self.commands = []

    def write(self, packet):
        import archive as a
        self.commands.append(packet[4])
        command, payload = packet[4], packet[5:-1]
        replies = {a.API: bytes([0,1,48]), a.VARIANT: b"BTFL", a.UID: bytes(range(12)),
                   a.BOXIDS: bytes([1,0,2]), a.STATUS: struct.pack("<HHHIB", 100,0,0,2 if self.armed else 0,0),
                   a.SUMMARY: struct.pack("<BIII",3,256,16*1024*1024,len(self.data))}
        if command == a.READ:
            offset, size, compression = struct.unpack("<IHB",payload)
            chunk = self.data[offset:offset+size]
            self.reads += 1
            if self.mutate and self.reads > (len(self.data)+127)//128:
                chunk = bytes([chunk[0] ^ 1]) + chunk[1:]
            response = struct.pack("<IHB",offset,len(chunk),0)+chunk
        else:
            response = replies[command]
        wire = a.frame(command,response,b">")
        if self.corrupt:
            self.output.extend(wire[:-1]+bytes([wire[-1]^1]))
            self.corrupt = False
        self.output.extend(wire)
        return len(packet)

    def read(self, count):
        result = bytes(self.output[:7])  # exercise fragmented frames
        del self.output[:7]
        return result


class BlackboxTests(StorageFixture):
    raw = b"H Product:Blackbox flight data recorder by Nicholas Sherlock\n" + bytes(range(256))*2

    def recorder(self, store, **kwargs):
        import archive as a
        self.serial = FakeSerial(self.raw, **kwargs)
        return a.Blackbox(a.MSP(self.serial, timeout=0.01), store)

    def test_native_msp_archive_and_checksum(self):
        with self.store() as store:
            receipt = self.recorder(store, corrupt=True).archive()
            self.assertTrue(receipt["complete"])
            self.assertEqual(receipt["sha256"], hashlib.sha256(self.raw).hexdigest())
            self.assertEqual((self.path/"ardupilot"/receipt["file"]).read_bytes(),self.raw)
            self.assertTrue(set(self.serial.commands) <= {1,2,70,71,101,119,160})

    def test_armed_no_flash_reads(self):
        import archive as a
        with self.store() as store:
            recorder = self.recorder(store,armed=True)
            with self.assertRaises(a.Armed):
                recorder.archive()
            self.assertNotIn(a.READ,self.serial.commands)

    def test_rearmed_mid_transfer_keeps_partial(self):
        import archive as a
        with self.store() as store:
            recorder = self.recorder(store)
            original = recorder.chunk
            def chunk(offset,count):
                data = original(offset,count)
                self.serial.armed = True
                return data
            with patch.object(recorder,"chunk",side_effect=chunk):
                with self.assertRaises(a.Armed):
                    recorder.archive()
            self.assertTrue(list((self.path/"ardupilot").glob("*.partial")))
            self.assertFalse(list((self.path/"ardupilot").glob("*.bbl")))

    def test_changed_second_pass_rejected(self):
        with self.store() as store:
            with self.assertRaisesRegex(ValueError,"changed"):
                self.recorder(store,mutate=True).archive()

    def test_erase_and_configuration_commands_forbidden(self):
        import archive as a
        for command in (72, 200, 245, 250):
            with self.assertRaises(ValueError):
                a.frame(command)

    def test_wrong_firmware_rejected(self):
        import archive as a
        with self.store() as store:
            with self.assertRaisesRegex(ValueError,"not Betaflight"):
                a.Blackbox(Mock(request=Mock(return_value=b"INAV")),store)

    def test_mismatched_read_address_rejected(self):
        import archive as a
        with self.store() as store:
            recorder = self.recorder(store)
            original = recorder.msp.request
            def request(command,payload=b""):
                if command == a.READ:
                    return struct.pack("<IHB",999,10,0)+bytes(10)
                return original(command,payload)
            with patch.object(recorder.msp,"request",side_effect=request):
                with self.assertRaises(ValueError):
                    recorder.chunk(0,10)

    def test_changed_uid_rejected(self):
        import archive as a
        with self.store() as store:
            recorder = self.recorder(store)
            original = recorder.msp.request
            def request(command,payload=b""):
                return bytes(12) if command == a.UID else original(command,payload)
            with patch.object(recorder.msp,"request",side_effect=request):
                with self.assertRaisesRegex(ValueError,"identity"):
                    recorder.archive()


if __name__ == "__main__":
    unittest.main()
