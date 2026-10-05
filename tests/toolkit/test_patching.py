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

    def test_unknown_output_identity_is_allowed(self):
        """A translated ROM has no recorded hash until one is produced."""
        data = b"test"
        # Both expectations absent: nothing to check, so this passes.
        validate_rom(data, size=None, digest=None, description="translated ROM")
        # A supplied expectation is still enforced even when the other is absent.
        validate_rom(data, size=4, digest=None, description="translated ROM")

    def test_known_output_identity_is_still_enforced(self):
        import hashlib

        data = b"test"
        with self.assertRaisesRegex(WorkstationError, "expected SHA-256"):
            validate_rom(data, size=None, digest="0" * 64, description="translated ROM")
        with self.assertRaisesRegex(WorkstationError, "expected 9 bytes"):
            validate_rom(data, size=9, digest=hashlib.sha256(data).hexdigest(),
                         description="translated ROM")


if __name__ == "__main__":
    unittest.main()
