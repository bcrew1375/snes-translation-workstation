import tempfile
import unittest
from pathlib import Path

from snesworkbench.errors import WorkstationError
from snesworkbench.manifests import parse_manifest_text, read_manifest_collection


FIELDS = {"id": str, "value": int}


def manifest(identifier: str, value: int) -> str:
    return f'''schema_version = 1

[[record]]
id = "{identifier}"
value = {value}
'''


class ManifestCollectionTest(unittest.TestCase):
    def test_directory_members_are_concatenated_in_lexical_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "20_second.toml").write_text(manifest("second", 2), encoding="utf-8")
            (root / "10_first.toml").write_text(manifest("first", 1), encoding="utf-8")
            (root / "README.md").write_text("ignored\n", encoding="utf-8")

            records = read_manifest_collection(root, FIELDS)

            self.assertEqual([record["id"] for record in records], ["first", "second"])

    def test_empty_manifest_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(WorkstationError, "has no TOML files"):
                read_manifest_collection(directory, FIELDS)

    def test_malformed_member_is_rejected_with_its_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            malformed = root / "02_bad.toml"
            (root / "01_good.toml").write_text(manifest("good", 1), encoding="utf-8")
            malformed.write_text("schema_version = 1\nrecord = [", encoding="utf-8")

            with self.assertRaisesRegex(WorkstationError, r"02_bad\.toml"):
                read_manifest_collection(root, FIELDS)

    def test_optional_fields_may_be_omitted_or_validated(self):
        without_optional = parse_manifest_text(
            "record.toml", manifest("first", 1), FIELDS,
            optional_fields={"note": str},
        )
        self.assertNotIn("note", without_optional[0])

        with_optional = manifest("first", 1).replace("value = 1", 'value = 1\nnote = "ok"')
        records = parse_manifest_text(
            "record.toml", with_optional, FIELDS,
            optional_fields={"note": str},
        )
        self.assertEqual(records[0]["note"], "ok")

        wrong_type = with_optional.replace('note = "ok"', "note = 2")
        with self.assertRaisesRegex(WorkstationError, "key 'note' has invalid type int"):
            parse_manifest_text(
                "record.toml", wrong_type, FIELDS,
                optional_fields={"note": str},
            )


if __name__ == "__main__":
    unittest.main()