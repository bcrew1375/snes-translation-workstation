import unittest

from snesworkbench.text import (
    AllocationRange,
    TextEncodeError,
    TextEncoding,
    allocate_streams,
    encode_text,
)


class GenericTextTest(unittest.TestCase):
    def test_configurable_controls_and_terminator(self):
        config = TextEncoding(
            characters={"A": 1, "B": 2},
            controls=(("<BR>", b"\xF0"),),
            terminator=b"\xFF",
            max_line_units=1,
            line_control="<BR>",
        )
        self.assertEqual(encode_text("A<BR>B", config), b"\x01\xF0\x02\xFF")

    def test_generic_allocator(self):
        addresses = allocate_streams(
            [("a", b"1234"), ("b", b"567")],
            [AllocationRange(0, 4), AllocationRange(10, 12)],
            minimum=0,
            maximum=20,
        )
        self.assertEqual(addresses, {"a": 0, "b": 10})

    def test_overlapping_ranges_are_rejected(self):
        with self.assertRaises(TextEncodeError):
            allocate_streams(
                [("a", b"1")],
                [AllocationRange(0, 5), AllocationRange(5, 10)],
            )


if __name__ == "__main__":
    unittest.main()