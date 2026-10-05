import unittest

from snesworkbench.errors import WorkstationError
from snesworkbench.patching import (
    bounded_write,
    changed_offsets,
    fixed_slot,
    validate_changed_scope,
    validate_rom,
)


class PatchingTest(unittest.TestCase):
    def test_fixed_slot_padding_and_overflow(self):
        self.assertEqual(fixed_slot(b"AB", 4, "sample"), b"AB\x00\x00")
        with self.assertRaisesRegex(WorkstationError, "slot is 1"):
            fixed_slot(b"AB", 1, "sample")

    def test_bounded_write_rejects_overflow(self):
        with self.assertRaisesRegex(WorkstationError, "exceeds ROM"):
            bounded_write(bytearray(4), 3, b"AB", "sample")

    def test_changed_scope_is_enforced(self):
        changed = changed_offsets(b"ABC", b"AXC")
        self.assertEqual(changed, frozenset({1}))
        validate_changed_scope(changed, {1})
        with self.assertRaisesRegex(WorkstationError, "unapproved byte"):
            validate_changed_scope(changed, {0})

    def test_rom_identity_validation(self):
        import hashlib

        data = b"test"
        validate_rom(
            data,
            size=4,
            digest=hashlib.sha256(data).hexdigest(),
            description="fixture",
        )
        with self.assertRaisesRegex(WorkstationError, "unsupported fixture"):
            validate_rom(data, size=5, digest="0" * 64, description="fixture")


if __name__ == "__main__":
    unittest.main()
