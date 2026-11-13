from __future__ import annotations

import json
import hashlib
import sys
import unittest
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "toolkit"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dbz_kakusei_hen.scenario import (  # noqa: E402
    decode_scenario_roots,
    decode_text_slots,
    restore_candidate_ranges,
)
from dbz_kakusei_hen.battle_hud import decompress_resource  # noqa: E402
from snesworkbench.analysis import calculate_coverage, load_analysis_manifest  # noqa: E402


class AnalysisTextRegionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        document = json.loads(
            (PROJECT_ROOT / "analysis" / "project.json").read_text(encoding="utf-8")
        )
        cls.regions = {
            (region["rom_start"], region["rom_end"]): region
            for region in document["regions"]
        }
        cls.rom = (PROJECT_ROOT / "rom" / "original.sfc").read_bytes()

    def test_command_08_pointer_and_text_regions_are_recorded(self):
        expected = [
            ("$0C41C8", "$0C4349", "pointer_table", 0x0182),
            ("$0C434A", "$0C74D7", "text", 0x318E),
            ("$0C8000", "$0C87BF", "pointer_table", 0x07C0),
            ("$0C87C0", "$0CF8ED", "text", 0x712E),
            ("$0D0000", "$0D03AD", "pointer_table", 0x03AE),
            ("$0D03AE", "$0D76C9", "text", 0x731C),
            ("$0D8000", "$0D83EF", "pointer_table", 0x03F0),
            ("$0D83F0", "$0DFC05", "text", 0x7816),
            ("$0E0000", "$0E039B", "pointer_table", 0x039C),
            ("$0E039C", "$0E786B", "text", 0x74D0),
            ("$0E8000", "$0E838F", "pointer_table", 0x0390),
            ("$0E8390", "$0EFB25", "text", 0x7796),
            ("$0F0000", "$0F03A1", "pointer_table", 0x03A2),
            ("$0F03A2", "$0F7D11", "text", 0x7970),
            ("$0F8000", "$0F837B", "pointer_table", 0x037C),
            ("$0F837C", "$0FFC5D", "text", 0x78E2),
        ]
        for start, end, region_type, size in expected:
            with self.subTest(start=start, end=end):
                region = self.regions[(start, end)]
                self.assertEqual(region["type"], region_type)
                self.assertEqual(region["confidence"], "confirmed")
                self.assertEqual(int(end[1:], 16) - int(start[1:], 16) + 1, size)

        self.assertEqual(
            sum(size for _, _, region_type, size in expected if region_type == "text"),
            224_422,
        )
        self.assertEqual(
            sum(
                size
                for _, _, region_type, size in expected
                if region_type == "pointer_table"
            ),
            7_978,
        )

    def test_bank_83_independently_entered_routine_boundaries(self):
        expected = [
            ("$01B339", "$01B33C", 4, "3975584437a5386c93bcde1bc593ceef4b4c4cf804d85ba324db4a6ca1f1916a", "20 58 B3", 0x6B, 0x08),
            ("$01B499", "$01B49C", 4, "ef76cf55cd72bc6ed16d9fc9eef896de0703b528e1ada0c02b45f9ab88973b79", "20 9D B4", 0x6B, 0x08),
            ("$01B59E", "$01B5A1", 4, "683f66c103e044939bc1ea3be2cfd2981455314296002492e56bf154aa0fb949", "20 A2 B5", 0x6B, 0x08),
            ("$01B33D", "$01B498", 348, "af1da1d76224adb43ba545cca7ac39b1388fd2ad3a30cd86bfbe92e1c573e29e", "08 8B E2", 0x60, 0x20),
            ("$01B49D", "$01B59D", 257, "20276c1314f9434b6c047b1707d7442b070888a4de61e7bd03511f632057ea2a", "08 E2 20", 0x60, 0x20),
            ("$01B5A2", "$01B751", 432, "38a7c65602e248131270c3540c2b30af75d97cbf00c15755bb15e502f9947145", "08 E2 20", 0x60, 0xA9),
            ("$01B752", "$01B86A", 281, "4cc4de0aef836d3938eeb3b4f231f5edc1743c959dc547dcd228229cf6600258", "A9 00 1C", 0x6B, 0x08),
            ("$01C581", "$01C7E3", 611, "fada099c4b85984fc15199ada583c48b4fdc0393ba7878ac2371b2fed4b2acd3", "C2 10 A2", 0x6B, 0x08),
            ("$01D2B1", "$01D3F6", 326, "3e2f5d0a78c077ed38b65355a139e1a91dddf108280a82c63a84b13a051914fd", "E2 20 A5", 0x6B, 0x06),
            ("$01DA20", "$01DD17", 760, "16acc0f6187faa8e2241012b70e301cc0c0c7bfd6c596de4ef67c8c461929d70", "08 C2 20", 0x6B, 0x08),
            ("$01DD18", "$01DF63", 588, "7cb56c287edd4a9549116ac6cc692a5b7e0553be8a6400fce309b26a075f5f5e", "08 C2 20", 0x6B, 0x08),
            ("$01DF64", "$01E1C1", 606, "553df984c37be1a4e2a9907587ce553491f8cd930f64c7503f7514c0c221fd0d", "08 C2 20", 0x6B, 0x08),
            ("$01E1C2", "$01E2A7", 230, "e8d5d2d18ecb121169e675b302258c08cd59c784eba79ac80142c490b200db7e", "08 C2 20", 0x60, 0xC2),
            ("$01E2A8", "$01E4FF", 600, "dbcd9ae995889740e4f906d5529d7b0f0b812b94424040efa5ea524181ae501d", "C2 20 A5", 0x60, 0xD0),
            ("$01B86B", "$01C580", 3350, "08512a9eb13a25707ae203f026ca4d91ef262483e7d588257193807b2eff885f", "08 E2 20", 0x60, 0xC2),
            ("$01C7E4", "$01D2B0", 2765, "4b2c7171abcdcc36752e76ad5c98b3f3227d0a61190a3ac626ca2176b07fe4f0", "08 8B E2", 0x60, 0xE2),
            ("$01D428", "$01DA1F", 1528, "1dd1d51da8a9d5da7f7420967a0c27c50322218335cd8a8217cb5d0e268a83b1", "08 8B E2", 0x60, 0x08),
            ("$01847E", "$018536", 185, "6000593212a2168c107166292d553fe0c39770ec17a0cf6bc2b854abcfeb4a17", "08 8B 4B", 0x6B, 0x08),
            ("$018537", "$01859B", 101, "79dc3d17547c5467cc08b227e334c94740dbe690d06d0067a892a3609cea4a7f", "08 8B 4B", 0x6B, 0x08),
            ("$0197A3", "$019868", 198, "a71abf31edf7ec8b0463f9b3eedefa260da501a059cde14c46e75e46607d9eb7", "08 8B 4B", 0x6B, 0xAD),
            ("$01988A", "$019935", 172, "2f30eff7d7910c78218cfe4738a350736aced6f05df4a1ae3f611b96976f5924", "08 8B 4B", 0x6B, 0xAD),
            ("$01B20C", "$01B24E", 67, "bfcac27550b77d90a4c94018e09c840be5108a5b00de65a00591f25f6e86d1e0", "08 8B 4B", 0xDD, 0xC2),
            ("$01995D", "$019C30", 724, "112530ed97b4cc7cb31b448fcb884e2a8d2e9ff104e9c13bc838f1bffd56d3bb", "08 8B 4B", 0x6B, 0x0C),
            ("$019D73", "$019EE3", 369, "5122cedb99a310e1f7183809b6eee387b0fbb4541231d59d69a1de6760aa6903", "08 8B 4B", 0x6B, 0x08),
            ("$019F87", "$01A020", 154, "61629fb1b71ac70bc12adc30fc99fbfb60ab5b00afe6d98d9fb2c381168fb967", "08 8B 4B", 0x6B, 0x08),
            ("$01A021", "$01A05A", 58, "a5987111e214c2373c0d6ae63448c4e0c98a7289934a9844055e9eb6d7eb8ef6", "08 C2 10", 0x6B, 0x08),
            ("$01A1F8", "$01A2FE", 263, "6418d4289685a75d400b54f3da93e0bdca7b5cecea5bf4fc0459828c1e3953b9", "08 8B 4B", 0x6B, 0xE6),
            ("$01A313", "$01A407", 245, "a6fa38e593196cfcdd19cecc1c7598f10d98092b78e021dee7e32da2099c58b3", "08 8B 4B", 0x6B, 0x08),
            ("$01A408", "$01A60D", 518, "82f6de9ba9caec49f587f8fe4be39d933494b4cbd1d8576cf6fcee930fd7b3a0", "08 8B 4B", 0x6B, 0x00),
        ]
        for start, end, size, digest, prefix, terminal, following in expected:
            with self.subTest(start=start, end=end):
                region = self.regions[(start, end)]
                self.assertEqual(region["type"], "code")
                self.assertEqual(region["confidence"], "confirmed")
                left = int(start[1:], 16)
                right = int(end[1:], 16)
                payload = self.rom[left:right + 1]
                self.assertEqual(len(payload), size)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)
                self.assertEqual(payload[:3], bytes.fromhex(prefix))
                self.assertEqual(payload[-1], terminal)
                self.assertEqual(self.rom[right + 1], following)

        radius = self.regions[("$01D3F7", "$01D427")]
        self.assertEqual(radius["type"], "data")
        self.assertEqual(radius["confidence"], "confirmed")
        payload = self.rom[0x01D3F7:0x01D428]
        self.assertEqual(len(payload), 49)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "ccf347094fbc0e4649e0004d424380830c38850370da9f61ef25fb7ab00ccf58",
        )
        self.assertEqual(payload[-1], 0xFF)
        self.assertEqual(self.rom[0x01D428:0x01D42B], bytes.fromhex("08 8B E2"))

    def test_bank_83_configuration_tables_are_consumer_bounded(self):
        expected = [
            ("$01A60E", "$01AA0D", 1024, "37af35f7fc06eebbe68e31c5f10aff85ad6143bffa09b90cc5e130f3ba67e555"),
            ("$01AD58", "$01AEAF", 344, "c125ee86fbf312dc7e490385f2a2257d2ec7bd9b7edd819027b0da3c795cc696"),
            ("$01AEB0", "$01B007", 344, "fb881f632d8567ae0eccbb64a8d0062e1a0ea4b69284b6df65ba7f819db4fb98"),
            ("$01B008", "$01B045", 62, "659bdd88972e259d2e327d85ba5667cc5f7bc9d071d43bef9bab6dd222ba24ef"),
            ("$01B046", "$01B0A3", 94, "7cb99fada89356a80c48f27af255469f1727e7730a7e5cbb2e33df089dcc82fc"),
            ("$01B0A4", "$01B10D", 106, "0bc8834f4a15900f687e2b97b64c67ea7f9efabdd5ef2db0752b6aaad9759dfa"),
            ("$01B10E", "$01B181", 116, "a6c58cac65ea5ef0faddb497e66b4a10ff2af966d71745333afcb93a78e14f8e"),
            ("$01B182", "$01B1E1", 96, "6820d8eda33619c5bc845eb58875bfaca01ea5f10a7eb2d700ee55ddd9b48b8f"),
            ("$01B1E2", "$01B20B", 42, "be5ba5cf90c21974be19f54ece99dade89c9a6cab7b47597afb97559795ec7b2"),
        ]
        for start, end, size, digest in expected:
            with self.subTest(start=start):
                region = self.regions[(start, end)]
                self.assertEqual(region["type"], "data")
                self.assertEqual(region["confidence"], "confirmed")
                left = int(start[1:], 16)
                right = int(end[1:], 16)
                payload = self.rom[left:right + 1]
                self.assertEqual(len(payload), size)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)

        records = self.rom[0x01A60E:0x01AA0E]
        self.assertEqual(len(records) // 4, 256)
        keys = self.rom[0x01AD58:0x01AEB0]
        values = self.rom[0x01AEB0:0x01B008]
        self.assertEqual(len(keys), len(values))
        self.assertEqual(int.from_bytes(keys[-2:], "little"), 0)
        for start, end, _, _ in expected[3:]:
            right = int(end[1:], 16)
            self.assertEqual(self.rom[right - 1:right + 1], b"\x00\x00")

    def test_bank_82_exact_long_call_routines(self):
        expected = [
            ("$012053", "$0120FF", 173, "1c6a86a84b054b49931f6c11e50beae1178a118982ee26bf9f4b4c980cba5e11", "C2 20 9C", 0x08),
            ("$012100", "$012142", 67, "fc36f42d98713f0bb96c0368ab4917ed479721e786adc3d2a3842f41fc5606c7", "08 8B C2", 0x00),
            ("$013459", "$01349B", 67, "9d74b8bbb22ab69688b447a95fd2629dc690cb267086dd985a3cd65e74330474", "08 8B C2", 0x00),
            ("$01469E", "$0146B9", 28, "3fb51483ba77968d9ae1470358d3faa08166b3a04b00eaac5a6b9439238e6ec3", "08 8B C2", 0x00),
            ("$014B79", "$014B94", 28, "7a6bdeb7687eaaf5515059e0da4e6a74856e84b13b561bac9a669571cc577c8a", "08 8B C2", 0x00),
            ("$01505A", "$015089", 48, "bd8ee8cd9c9e4f1235679dbcb186734ce5712ede2ce5c92eb772cee69969a859", "22 A2 92", 0x08),
        ]
        for start, end, size, digest, prefix, following in expected:
            with self.subTest(start=start):
                region = self.regions[(start, end)]
                self.assertEqual(region["type"], "code")
                self.assertEqual(region["confidence"], "confirmed")
                left = int(start[1:], 16)
                right = int(end[1:], 16)
                payload = self.rom[left:right + 1]
                self.assertEqual(len(payload), size)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)
                self.assertEqual(payload[:3], bytes.fromhex(prefix))
                self.assertEqual(payload[-1], 0x6B)
                self.assertEqual(self.rom[right + 1], following)

    def test_bank_90_exact_long_call_routines(self):
        expected = [
            ("$080145", "$080178", 52, "879ee78c1c6d9a23abcf287b7b80379daafe3fb4bb49e067fdc886b75935a35b", "C2 20 A9", 0xC2),
            ("$081543", "$081622", 224, "797f16e341cd1a0549299bf2e51dc5e538e0cf9b4a313f2429c7fece525bc247", "E2 20 A9", 0xE2),
            ("$081ABE", "$081B47", 138, "9716f9b9e2a916a8c67027cbfa8a04255e24b60054586ddd5cd96e209ff7f39e", "E2 20 A9", 0xC2),
        ]
        for start, end, size, digest, prefix, following in expected:
            with self.subTest(start=start):
                region = self.regions[(start, end)]
                self.assertEqual(region["type"], "code")
                self.assertEqual(region["confidence"], "confirmed")
                left = int(start[1:], 16)
                right = int(end[1:], 16)
                payload = self.rom[left:right + 1]
                self.assertEqual(len(payload), size)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)
                self.assertEqual(payload[:3], bytes.fromhex(prefix))
                self.assertEqual(payload[-1], 0x6B)
                self.assertEqual(self.rom[right + 1], following)

    def test_bank_90_executable_prefix_is_closed_before_fill(self):
        region = self.regions[("$080000", "$084327")]
        self.assertEqual(region["type"], "code")
        self.assertEqual(region["confidence"], "confirmed")
        payload = self.rom[0x080000:0x084328]
        self.assertEqual(len(payload), 17_192)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "956cbf9ed454c7d5ebea24af89fecc24eb247b558a503538d1665c07ed3c21d7",
        )
        self.assertEqual(payload[:8], bytes.fromhex("C2 20 A9 E0 00 8D 28 01"))
        self.assertEqual(payload[-8:], bytes.fromhex("60 6C 40 14 40 6C 98 C4"))
        self.assertEqual(self.rom[0x084328], 0x98)
        self.assertEqual(set(self.rom[0x084329:0x084340]), {0xFF})

    def test_bank_81_menu_code_and_embedded_consumer_data(self):
        container = self.regions[("$009C93", "$00D2C0")]
        self.assertEqual(container["type"], "code")
        self.assertEqual(container["confidence"], "confirmed")
        payload = self.rom[0x009C93:0x00D2C1]
        self.assertEqual(len(payload), 13_870)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "3d38d2d56cf012e95868c6da33ae22d3e9cbbd78d8bc3bd9c2ef74d49fd80d88",
        )
        expected_data = [
            ("$009C93", "$009CCE", 60, "86223303f5d011c068041077bfd07cbb7f6dc539396ffdb13d14714e53aea8d1"),
            ("$00A566", "$00A575", 16, "26afe966c6213cde6fede985fb28d1470bfa137a283817292ebdb4a8ef6b8544"),
            ("$00A60F", "$00A61B", 13, "f4c4adc56b178012f8eb8d218272500666644a8eca59f70c19b646f449971756"),
            ("$00C029", "$00C070", 72, "30482c5f47ece3dc204632ba42d4c8b9e3fae0a521d00d11dec340d056cf0f6f"),
            ("$00C410", "$00C41C", 13, "b3b40273564523775ca7baa9c5eea1bab5ec872519bd0370e4d2bbcbd46979ec"),
            ("$00C4E2", "$00C4EE", 13, "ab9f85abe72d036f689a515a8ec047403794477fbddc69f2db97b161c7c5b6f1"),
        ]
        for start, end, size, digest in expected_data:
            with self.subTest(start=start):
                region = self.regions[(start, end)]
                self.assertEqual(region["type"], "data")
                left = int(start[1:], 16)
                right = int(end[1:], 16)
                data = self.rom[left:right + 1]
                self.assertEqual(len(data), size)
                self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
        self.assertEqual(self.rom[0x00D2C0], 0x60)

    def test_bank_83_remaining_setup_and_resource_domains(self):
        expected = [
            ("$01859C", "$018E96", "code", 2_299, "29a0756cbc4310b61b4e3befcf77754148e5a06464664e956e56259300f9c91d"),
            ("$018E97", "$0197A2", "data", 2_316, "1c95d12384582cd18762dfaf22dfa667a7c6f5450255b8cc6320f90a27068cc2"),
            ("$01A05B", "$01A1F7", "code", 413, "dc493c89b0e2b1a582c8f4a1a1f67066f9e06dbb3d98d36576558c3e9846f1b9"),
            ("$01AA0E", "$01AD57", "data", 842, "7c8b1b2843d92156a2afd2f510cd02e81c59dffaad91a666cfb521f409725076"),
            ("$01F393", "$01FFE9", "data", 3_159, "48c66cb28abb6154658757e86be5ba3b42d54b914cd541bafbb3b241fba451e5"),
        ]
        for start, end, region_type, size, digest in expected:
            with self.subTest(start=start):
                region = self.regions[(start, end)]
                self.assertEqual(region["type"], region_type)
                self.assertEqual(region["confidence"], "confirmed")
                left = int(start[1:], 16)
                right = int(end[1:], 16)
                payload = self.rom[left:right + 1]
                self.assertEqual(len(payload), size)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)

    def test_bank_82_dispatch_tables_and_handler_closures(self):
        expected = [
            ("$012143", "$0121CC", "pointer_table", 138, "e718f6c327c679eef6c69f6104bbdc686a22014b3bc071f6d84e115355c749cb", 69),
            ("$0121CD", "$013458", "code", 4748, "dc78f5be2bddae9c5a5ccd2f5291ef9a208423ab0ba75e7d7d220fab7f827f4c", None),
            ("$01349C", "$013525", "pointer_table", 138, "40d05ab35b1cc4fc19710289b94bd8cff89af1420dd4f82661fb6338688d229f", 69),
            ("$013526", "$01469D", "code", 4472, "07d84ccc10471f80d781e7fca627a691f4a421882271a16d091f02fb84dacf54", None),
            ("$0146BA", "$014743", "pointer_table", 138, "aa289810e212211629cd9ca30c1f3283137990a39aee4602304a4d6914b4834b", 69),
            ("$014744", "$014B78", "code", 1077, "5c78b4950d951ae2520b21c324fecc81a74e74dee6e91c183cbe05ed8b1ea925", None),
            ("$014B95", "$014C1E", "pointer_table", 138, "c889330aff0e70f4e7596374ce4362e85410e5376203437b03a052f6fc4cd682", 69),
            ("$014C1F", "$015059", "code", 1083, "7e596183fd11e900542919a5d60159e24e76d6c6eb243d03bd48414211ebd66c", None),
            ("$01514C", "$015171", "pointer_table", 38, "f97f334fc5d530ed05b70e1aeb283a0ce1f8e8e77e04b9ddf1d84169ca588c56", 19),
            ("$015172", "$0153EC", "code", 635, "85b9b14e25c5fa77792f861ca775a46b66e847f24c182b37f3ee191b519a4af0", None),
        ]
        for start, end, kind, size, digest, entries in expected:
            with self.subTest(start=start):
                region = self.regions[(start, end)]
                self.assertEqual(region["type"], kind)
                self.assertEqual(region["confidence"], "confirmed")
                left = int(start[1:], 16)
                right = int(end[1:], 16)
                payload = self.rom[left:right + 1]
                self.assertEqual(len(payload), size)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)
                if entries is not None:
                    pointers = [
                        int.from_bytes(payload[offset:offset + 2], "little")
                        for offset in range(0, len(payload), 2)
                    ]
                    self.assertEqual(len(pointers), entries)
                    self.assertEqual(pointers[0], 0)

        self.assertEqual(self.rom[0x0153EC], 0x60)
        self.assertEqual(self.rom[0x0153ED], 0xC2)

    def test_bank_82_remaining_helper_closures(self):
        expected = [
            ("$0118D4", "$011AAD", "code", 474, "de4c70c49558ca4359709713a85c0036c6986c3c8c650a989b52ee5b56e85430"),
            ("$011AAE", "$011ACD", "data", 32, "1e585e58ea5b67af06172ddc36e982146957a91bae96554d9a7ef54cea3de510"),
            ("$011ACE", "$012052", "code", 1413, "ec5342bc73d798b0d404200f5719a433d49c5366dd3a4d56b52d9a0c5f698abe"),
            ("$0153ED", "$0156C2", "code", 726, "671d8769f59cde38b701830ab40c8530217a2aaa185b187b7b45b9ae283836aa"),
            ("$01508A", "$01514B", "code", 194, "cf8f0434005dea32f99420be50fcea05239c4dd0bf067de7aa1547c4d5fa477e"),
        ]
        for start, end, kind, size, digest in expected:
            with self.subTest(start=start):
                region = self.regions[(start, end)]
                self.assertEqual(region["type"], kind)
                self.assertEqual(region["confidence"], "confirmed")
                left = int(start[1:], 16)
                right = int(end[1:], 16)
                payload = self.rom[left:right + 1]
                self.assertEqual(len(payload), size)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)

        self.assertEqual(len(self.rom[0x011AAE:0x011ACE]), 4 * 8)
        self.assertEqual(self.rom[0x012052], 0x60)
        self.assertEqual(self.rom[0x0156C2], 0x60)

    def test_command_08_presentation_metadata_is_recorded(self):
        region = self.regions[("$0C0000", "$0C1B29")]
        self.assertEqual(region["type"], "data")
        self.assertEqual(region["confidence"], "confirmed")
        self.assertIn("selectors $0200-$0F94", region["name"])
        self.assertEqual(0x0C1B29 - 0x0C0000 + 1, 6_954)

    def test_command_08_bank_tails_are_confirmed_padding(self):
        expected = [
            ("$0C74D8", "$0C7FFF", 0x98, 0xF4D8),
            ("$0CF8EE", "$0CFFFF", 0x99, 0xF8EE),
            ("$0D76CA", "$0D7FFF", 0x9A, 0xF6CA),
            ("$0DFC06", "$0DFFFF", 0x9B, 0xFC06),
            ("$0E786C", "$0E7FFF", 0x9C, 0xF86C),
            ("$0EFB26", "$0EFFFF", 0x9D, 0xFB26),
            ("$0F7D12", "$0F7FFF", 0x9E, 0xFD12),
            ("$0FFC5E", "$0FFFFF", 0x9F, 0xFC5E),
        ]
        targets = {
            (slot.pointer_bank, slot.target_address)
            for slot in decode_text_slots(self.rom)
            if not slot.is_null
        }
        for start_text, end_text, cpu_bank, cpu_start in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "padding")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(set(self.rom[start:end]), {0xFF})
                self.assertFalse(
                    [
                        address
                        for bank, address in targets
                        if bank == cpu_bank and cpu_start <= address <= 0xFFFF
                    ]
                )
                far_pointer = cpu_start.to_bytes(2, "little") + bytes([cpu_bank])
                self.assertNotIn(far_pointer, self.rom)

    def test_scenario_bank_tails_are_confirmed_padding(self):
        expected = [
            ("$097DF8", "$097FFF", 0x92, 0xFDF8),
            ("$09C225", "$09FFFF", 0x93, 0xC225),
        ]
        roots = decode_scenario_roots(self.rom)
        for start_text, end_text, cpu_bank, cpu_start in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "padding")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(self.rom[start - 1], 0x49)
                self.assertEqual(set(self.rom[start:end]), {0xFF})
                self.assertFalse(
                    [root for root in roots if root.bank == cpu_bank and root.address >= cpu_start]
                )
                far_pointer = cpu_start.to_bytes(2, "little") + bytes([cpu_bank])
                self.assertNotIn(far_pointer, self.rom)

    def test_coverage_includes_confirmed_bank_tails(self):
        manifest = load_analysis_manifest(PROJECT_ROOT / "analysis" / "project.json")
        report = calculate_coverage(manifest)
        self.assertEqual(report.analyzed_bytes, 2_097_152)
        self.assertEqual(report.rom_size - report.analyzed_bytes, 0)
        self.assertEqual(report.type_bytes["code"], 110_837)
        self.assertEqual(report.type_bytes["data"], 53_221)
        self.assertEqual(report.type_bytes["graphics"], 431_403)
        self.assertEqual(report.type_bytes["scenario_data"], 86_089)
        self.assertEqual(report.type_bytes["fill"], 288_284)
        self.assertEqual(report.type_bytes["text"], 281_456)
        self.assertEqual(report.type_bytes["pointer_table"], 34_326)
        self.assertEqual(report.type_bytes["padding"], 34_554)

    def test_battle_presentation_script_banks_are_losslessly_partitioned(self):
        expected = [
            (0x158000, 0x1584FF, 0x158500, 0x15DBA7, 0xDBA8, 342),
            (0x160000, 0x1604FF, 0x160500, 0x166848, 0xE849, 364),
        ]
        for table_start, table_end, data_start, data_end, sentinel, stream_count in expected:
            with self.subTest(table_start=f"{table_start:06X}"):
                table_region = self.regions[(f"${table_start:06X}", f"${table_end:06X}")]
                self.assertEqual(table_region["type"], "pointer_table")
                self.assertEqual(table_region["confidence"], "confirmed")
                script_region = self.regions[(f"${data_start:06X}", f"${data_end:06X}")]
                self.assertEqual(script_region["type"], "battle_script_data")
                self.assertEqual(
                    script_region["confidence"],
                    "confirmed_structure_partial_schema",
                )

                pointers = [
                    int.from_bytes(self.rom[offset:offset + 2], "little")
                    for offset in range(table_start, table_end + 1, 2)
                ]
                self.assertEqual(len(pointers), 640)
                self.assertTrue(all(left <= right for left, right in zip(pointers, pointers[1:])))
                self.assertEqual(pointers[0], 0x8500)
                self.assertEqual(pointers[-1], sentinel)
                self.assertEqual(pointers.count(sentinel), 192)

                unique_targets = sorted(set(pointers))
                real_targets = [target for target in unique_targets if target < sentinel]
                self.assertEqual(len(real_targets), stream_count)
                self.assertEqual(real_targets[0], 0x8500)
                self.assertEqual(unique_targets[-1], sentinel)
                self.assertEqual(
                    sum(right - left for left, right in zip(unique_targets, unique_targets[1:])),
                    sentinel - 0x8500,
                )
                bank_file_start = table_start
                for left, right in zip(unique_targets, unique_targets[1:]):
                    stream_end = bank_file_start + right - 0x8000
                    self.assertEqual(self.rom[stream_end - 1], 0x00)

                self.assertEqual(data_start, table_start + 0x500)
                self.assertEqual(data_end + 1, table_start + sentinel - 0x8000)
                self.assertEqual(self.rom[data_end + 1], 0xFF)

    def test_battle_presentation_group_hierarchy_is_recorded(self):
        primary = self.regions[("$178000", "$17838F")]
        self.assertEqual(primary["type"], "data")
        self.assertEqual(primary["confidence"], "confirmed")
        self.assertEqual(0x17838F - 0x178000 + 1, 19 * 48)

        fallbacks = self.regions[("$178390", "$1783F5")]
        self.assertEqual(fallbacks["type"], "data")
        self.assertEqual(fallbacks["confidence"], "confirmed")
        self.assertEqual(0x1783F5 - 0x178390 + 1, 3 * 34)

        records = self.regions[("$1783F6", "$17BBF5")]
        self.assertEqual(records["type"], "data")
        self.assertEqual(records["confidence"], "confirmed_structure_partial_schema")
        self.assertEqual(0x17BBF5 - 0x1783F6 + 1, 448 * 32)

        primary_values = self.rom[0x178000:0x178390]
        fallback_values = self.rom[0x178390:0x1783F6]
        reachable_groups = set(primary_values) | set(fallback_values)
        reachable_groups.discard(0xFF)
        self.assertEqual(min(reachable_groups), 0x00)
        self.assertEqual(max(reachable_groups), 0xFE)

        group_records = self.rom[0x1783F6:0x17BBF6]
        for group_id in range(448):
            record = group_records[group_id * 32:(group_id + 1) * 32]
            self.assertEqual(len(record), 32)
            first_side = [
                int.from_bytes(record[offset:offset + 2], "little")
                for offset in range(0, 16, 2)
            ]
            second_side = [
                int.from_bytes(record[offset:offset + 2], "little")
                for offset in range(16, 32, 2)
            ]
            self.assertTrue(all(value == 0xFFFF or value < 0x0280 for value in first_side))
            self.assertTrue(
                all(value == 0xFFFF or 0x0100 <= value < 0x0380 for value in second_side)
            )

        self.assertEqual(group_records[-14:], bytes([0xFF]) * 14)

    def test_additional_loader_owned_codec_resources_have_exact_extents(self):
        import hashlib

        expected = [
            (
                0x188000,
                0x18AC9D,
                0x3A00,
                "6d534a93a0783868e132c07c1eedc355aea8ae8ff45eb196b746005dc969609c",
                0x00D86F,
            ),
            (
                0x190000,
                0x1928E8,
                0x3000,
                "a221b3447032c8622949a0ab428881e6bd9e0598bdfe239c1e4e30f44b696f88",
                0x00D879,
            ),
        ]
        for start, end, output_length, digest, loader_record in expected:
            with self.subTest(start=f"{start:06X}"):
                region = self.regions[(f"${start:06X}", f"${end:06X}")]
                self.assertEqual(region["type"], "compressed_resource")
                self.assertEqual(region["confidence"], "confirmed")
                resource = decompress_resource(self.rom, start)
                self.assertEqual(resource.consumed, end - start + 1)
                self.assertEqual(len(resource.data), output_length)
                self.assertEqual(hashlib.sha256(resource.data).hexdigest(), digest)

                record = self.rom[loader_record:loader_record + 5]
                source_address = int.from_bytes(record[0:2], "little")
                source_bank = record[2]
                transfer_length = int.from_bytes(record[3:5], "little")
                source_offset = (source_bank - 0x80) * 0x8000 + source_address - 0x8000
                self.assertEqual(source_offset, start)
                self.assertEqual(transfer_length, output_length)

        self.assertEqual(self.rom[0x1928E9], 0x01)
        self.assertEqual(self.regions[("$1928E9", "$1928E9")]["type"], "padding")

    def test_battle_palette_source_table_owns_nine_exact_blocks(self):
        table = self.regions[("$011287", "$0112A1")]
        self.assertEqual(table["type"], "pointer_table")
        self.assertEqual(table["confidence"], "confirmed")

        expected_offsets = [
            0x183CF2,
            0x186890,
            0x18E9D2,
            0x195F42,
            0x1978C0,
            0x18B7B2,
            0x18E952,
            0x1933AA,
            0x1957DA,
        ]
        for index, expected_offset in enumerate(expected_offsets):
            descriptor = self.rom[0x011287 + index * 3:0x01128A + index * 3]
            address = int.from_bytes(descriptor[0:2], "little")
            bank = descriptor[2]
            offset = (bank - 0x80) * 0x8000 + address - 0x8000
            self.assertEqual(offset, expected_offset)

            bounds = (f"${offset:06X}", f"${offset + 0x7F:06X}")
            region = self.regions[bounds]
            self.assertEqual(region["type"], "graphics")
            self.assertEqual(region["confidence"], "confirmed")
            words = [
                int.from_bytes(self.rom[position:position + 2], "little")
                for position in range(offset, offset + 0x80, 2)
            ]
            self.assertEqual(len(words), 64)
            self.assertTrue(all(value <= 0x7FFF for value in words))

        self.assertEqual(self.rom[0x183CF1], 0x00)
        self.assertEqual(self.regions[("$183CF1", "$183CF1")]["type"], "padding")
        self.assertEqual(self.rom[0x1957D9], 0x00)
        self.assertEqual(self.regions[("$1957D9", "$1957D9")]["type"], "padding")

    def test_bank_84_raw_graphics_source_has_exact_wram_to_vram_transfer(self):
        region = self.regions[("$020000", "$0201FF")]
        self.assertEqual(region["type"], "graphics")
        self.assertEqual(region["confidence"], "confirmed")
        self.assertEqual(len(self.rom[0x020000:0x020200]), 0x200)
        self.assertEqual(
            hashlib.sha256(self.rom[0x020000:0x020200]).hexdigest(),
            "43c12e7be15d3a323b050d3af9db0d8abe362615bf887887ddfa62a099acd3a2",
        )

        copy_sequence = bytes.fromhex(
            "a2 00 80 a0 00 80 c2 20 a9 ff 01 54 7e 84"
        )
        self.assertEqual(self.rom[0x008075:0x008083], copy_sequence)
        self.assertEqual(self.rom.count(copy_sequence), 1)

        transfer_setup = bytes.fromhex(
            "a9 00 00 85 eb a9 00 02 85 ed a9 01 00 04 dc 22 d7 88 80"
        )
        self.assertEqual(self.rom[0x008083:0x008096], transfer_setup)

        vblank_dma = self.rom[0x000523:0x000568]
        self.assertEqual(vblank_dma[0:10], bytes.fromhex("a9 01 8d 70 43 a9 18 8d 71 43"))
        self.assertIn(bytes.fromhex("69 00 80 8d 72 43"), vblank_dma)
        self.assertIn(bytes.fromhex("8d 16 21"), vblank_dma)

        following = self.regions[("$020200", "$0203E1")]
        self.assertEqual(following["type"], "compressed_resource")
        self.assertEqual(following["confidence"], "confirmed")

    def test_six_more_loader_owned_codec_resources_have_exact_extents(self):
        import hashlib

        expected = [
            (0x183D72, 0x18688E, 0x31C0, "8f5bd632e88d51c2dc04a1955333ca1f992557d9ef08fc16a5f99529bb16f936", 0x00D85B),
            (0x186910, 0x1877CB, 0x1E00, "5cf7387ca2961e393ff90b7c8ba4b4d10e74042bccc6dc6267ee13c3f8e7e0b3", 0x00D860),
            (0x18B832, 0x18DEDD, 0x2D00, "54b706ecdde6f9dc66dfb6def7aa921829c34ba7b4651a4bee06e1597261df7b", 0x00D874),
            (0x19342A, 0x195135, 0x2BC0, "9c0fa7e42cf0f6c759a5243dbdaa7b33950a89d339838c75f4ded7e8bb299c0f", 0x00D87E),
            (0x19585A, 0x1959F2, 0x0240, "f2735ea5396eef8bbea7d36e5965a351ce3274f5ffc4e7232cb35f6b9b7b1bcf", 0x00D865),
            (0x195FC2, 0x197180, 0x15A0, "4155a32b94f87c6cbf5a68b249ee0cf8627274b6430282cdcb4dedbc555c30f0", 0x00D86A),
        ]
        for start, end, output_length, digest, loader_record in expected:
            with self.subTest(start=f"{start:06X}"):
                region = self.regions[(f"${start:06X}", f"${end:06X}")]
                self.assertEqual(region["type"], "compressed_resource")
                self.assertEqual(region["confidence"], "confirmed")
                resource = decompress_resource(self.rom, start)
                self.assertEqual(resource.consumed, end - start + 1)
                self.assertEqual(len(resource.data), output_length)
                self.assertEqual(hashlib.sha256(resource.data).hexdigest(), digest)

                record = self.rom[loader_record:loader_record + 5]
                address = int.from_bytes(record[0:2], "little")
                bank = record[2]
                transfer_length = int.from_bytes(record[3:5], "little")
                offset = (bank - 0x80) * 0x8000 + address - 0x8000
                self.assertEqual(offset, start)
                self.assertEqual(transfer_length, output_length)

        for offset, value in [(0x18688F, 0x10), (0x1959F3, 0x52), (0x197181, 0x00)]:
            self.assertEqual(self.rom[offset], value)
            self.assertEqual(self.regions[(f"${offset:06X}", f"${offset:06X}")]["type"], "padding")

    def test_bank_b3_object_layout_table_and_streams_form_exact_partition(self):
        table = self.regions[("$198000", "$19851F")]
        self.assertEqual(table["type"], "pointer_table")
        self.assertEqual(table["confidence"], "confirmed")
        corpus = self.regions[("$198520", "$19DD03")]
        self.assertEqual(corpus["type"], "graphics")
        self.assertEqual(corpus["confidence"], "confirmed_structure_partial_schema")

        pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x198000, 0x198520, 2)
        ]
        self.assertEqual(len(pointers), 656)
        self.assertTrue(all(0x8520 <= pointer < 0xDD04 for pointer in pointers))
        unique_targets = sorted(set(pointers))
        self.assertEqual(len(unique_targets), 360)
        self.assertEqual(unique_targets[0], 0x8520)
        self.assertEqual(unique_targets[-1], 0xDCD1)
        boundaries = unique_targets + [0xDD04]
        self.assertEqual(
            sum(right - left for left, right in zip(boundaries, boundaries[1:])),
            0xDD04 - 0x8520,
        )
        for left, right in zip(boundaries, boundaries[1:]):
            stream_start = 0x198000 + left - 0x8000
            stream_end = 0x198000 + right - 0x8000
            self.assertEqual(self.rom[stream_end - 1], 0x80)
            self.assertEqual((right - left - 1) % 5, 0)
            for record_start in range(stream_start, stream_end - 1, 5):
                self.assertIn(self.rom[record_start], (0x00, 0x01))

        self.assertEqual(self.rom[0x198520], 0x80)
        self.assertEqual(set(self.rom[0x19DD04:0x1A0000]), {0xFF})

    def test_banks_85_and_86_complete_object_layout_hierarchy(self):
        expected = [
            (0x028000, 880, 0x86E0, 0xF547, 82, True),
            (0x030000, 832, 0x8681, 0xF5D5, 0, False),
        ]
        for base, slot_count, corpus_start, corpus_end, null_count, allow_aliases in expected:
            with self.subTest(base=f"{base:06X}"):
                table_end = base + slot_count * 2 - 1
                table = self.regions[(f"${base:06X}", f"${table_end:06X}")]
                self.assertEqual(table["type"], "pointer_table")
                self.assertEqual(table["confidence"], "confirmed")
                corpus_file_start = base + corpus_start - 0x8000
                corpus_file_end = base + corpus_end - 0x8000 - 1
                corpus = self.regions[
                    (f"${corpus_file_start:06X}", f"${corpus_file_end:06X}")
                ]
                self.assertEqual(corpus["type"], "graphics")
                self.assertEqual(corpus["confidence"], "confirmed_structure_partial_schema")

                pointers = [
                    int.from_bytes(self.rom[offset:offset + 2], "little")
                    for offset in range(base, table_end + 1, 2)
                ]
                self.assertEqual(len(pointers), slot_count)
                self.assertEqual(pointers.count(0), null_count)
                active_targets = sorted(set(pointer for pointer in pointers if pointer))
                self.assertTrue(
                    all(corpus_start <= pointer < corpus_end for pointer in active_targets)
                )

                stream_ranges = []
                covered = set()
                control_values = set()
                for pointer in active_targets:
                    stream_start = base + pointer - 0x8000
                    cursor = stream_start
                    while self.rom[cursor] != 0x80:
                        control_values.add(self.rom[cursor])
                        cursor += 5
                    stream_end = cursor + 1
                    stream_ranges.append((pointer, 0x8000 + stream_end - base))
                    covered.update(range(pointer, 0x8000 + stream_end - base))
                self.assertEqual(
                    covered,
                    set(range(corpus_start, corpus_end)),
                )

                aliases = [
                    pointer
                    for pointer in active_targets
                    if any(left < pointer < right for left, right in stream_ranges)
                ]
                if allow_aliases:
                    self.assertEqual(aliases, [0x86E1, 0x86E7, 0x86ED, 0x86F3, 0x86F9])
                    self.assertEqual(control_values, {0x00, 0x01, 0x30, 0xF8})
                else:
                    self.assertEqual(aliases, [])
                    self.assertEqual(control_values, {0x00, 0x01})

        self.assertEqual(self.rom[0x030680], 0x80)
        self.assertEqual(self.regions[("$030680", "$030680")]["type"], "data")

    def test_bank_89_control_stream_selector_hierarchy(self):
        table = self.regions[("$048000", "$0482E3")]
        self.assertEqual(table["type"], "pointer_table")
        self.assertEqual(table["confidence"], "confirmed")
        corpus = self.regions[("$0482E4", "$04930F")]
        self.assertEqual(corpus["type"], "scenario_data")
        self.assertEqual(corpus["confidence"], "confirmed_structure_partial_schema")

        pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x048000, 0x0482E4, 2)
        ]
        self.assertEqual(len(pointers), 370)
        self.assertEqual(pointers[0x0161:0x016F], [0] * 14)
        self.assertEqual(pointers.count(0), 14)
        active = [pointer for pointer in pointers if pointer]
        self.assertEqual(len(active), 356)
        self.assertEqual(len(set(active)), 355)
        self.assertTrue(all(left <= right for left, right in zip(active, active[1:])))
        self.assertEqual(min(active), 0x82E4)
        self.assertEqual(max(active), 0x930A)
        self.assertEqual(pointers[0x016F:0x0172], [0x92FE, 0x9304, 0x930A])
        self.assertEqual(self.rom[0x04930A:0x049310], bytes.fromhex("2D 71 01 01 0C FF"))
        self.assertEqual(self.rom[0x049310:0x049314], bytes.fromhex("08 8B 4B AB"))

    def test_bank_89_post_stream_code_and_presentation_resources(self):
        code = self.regions[("$049310", "$049988")]
        self.assertEqual(code["type"], "code")
        self.assertEqual(code["confidence"], "confirmed")
        self.assertEqual(self.rom[0x049310:0x049314], bytes.fromhex("08 8B 4B AB"))
        self.assertEqual(self.rom[0x049987:0x049989], bytes.fromhex("28 60"))
        self.assertEqual(
            hashlib.sha256(self.rom[0x049310:0x049989]).hexdigest(),
            "06456e8a847e7d5661857146f0cc576d232e6edf5317991d86acf2043512f491",
        )

        stream = self.regions[("$049989", "$04999C")]
        self.assertEqual(stream["type"], "text")
        words = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x049989, 0x04999D, 2)
        ]
        self.assertEqual(
            words,
            [0x0235, 0x01F1, 0x01A1, 0x01E3, 0x0240,
             0x01C0, 0x0201, 0x01F5, 0x0215, 0x0000],
        )
        self.assertEqual(
            hashlib.sha256(self.rom[0x049989:0x04999D]).hexdigest(),
            "0fd4044b242112466b12ea2da4fa4ccf33583436b9b8f7700353c81f79d96957",
        )

        blocks = [
            (0x04999D, 0x049A9C, "9079c1fe81fefb857bc353a4613390cbe5446b29d91da988a062094f268d4873"),
            (0x049A9D, 0x049B9C, "d25baf530880c3d5546084868e73fda0461b1ef26abb77cde641950068279cfe"),
        ]
        for start, end, digest in blocks:
            with self.subTest(start=f"{start:06X}"):
                region = self.regions[(f"${start:06X}", f"${end:06X}")]
                self.assertEqual(region["type"], "graphics")
                self.assertEqual(region["confidence"], "confirmed")
                self.assertEqual(end - start + 1, 0x100)
                self.assertEqual(hashlib.sha256(self.rom[start:end + 1]).hexdigest(), digest)
        following = self.regions[("$049B9D", "$04A9B4")]
        self.assertEqual(following["type"], "compressed_resource")

    def test_bank_88_selector_owned_graphics_hierarchy(self):
        pointer_region = self.regions[("$04024C", "$040277")]
        self.assertEqual(pointer_region["type"], "pointer_table")
        pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x04024C, 0x040278, 2)
        ]
        self.assertEqual(len(pointers), 22)
        targets = set(pointers)
        self.assertEqual(len(targets), 18)
        self.assertEqual(targets, set(range(0x8278, 0x8938, 0x60)))
        self.assertEqual(
            hashlib.sha256(self.rom[0x04024C:0x040278]).hexdigest(),
            "fca195db9b32ce6abad3e322454ce67e3728d8b24851fd2e42954d7d1ec468dd",
        )

        graphics = self.regions[("$040278", "$040937")]
        self.assertEqual(graphics["type"], "graphics")
        self.assertEqual(graphics["confidence"], "confirmed")
        self.assertEqual(0x040938 - 0x040278, 18 * 0x60)
        for address in targets:
            start = 0x040000 + address - 0x8000
            self.assertEqual(len(self.rom[start:start + 0x60]), 0x60)
        self.assertEqual(
            hashlib.sha256(self.rom[0x040278:0x040938]).hexdigest(),
            "808ca875022dbbccc0385f734d3186eab74f14e1f859f508ea04b71abbae42b0",
        )

        selectors = [
            (0x040938, 0x04094D, "185364339b0fc8d9b6cbea350264459f0e2209c50a9afcf962dbaae6238b454d"),
            (0x04094E, 0x040963, "7404169368295aefae181473255da95d600f49e8dd69eb1507bda3d1cd38011d"),
        ]
        for start, end, digest in selectors:
            with self.subTest(start=f"{start:06X}"):
                region = self.regions[(f"${start:06X}", f"${end:06X}")]
                self.assertEqual(region["type"], "data")
                self.assertEqual(end - start + 1, 22)
                self.assertEqual(hashlib.sha256(self.rom[start:end + 1]).hexdigest(), digest)
        following = self.regions[("$040964", "$040D56")]
        self.assertEqual(following["type"], "compressed_resource")
        self.assertEqual(self.regions[("$04022C", "$04024B")]["type"], "text")
        self.assertEqual(
            [
                offset
                for offset in range(len(self.rom))
                if self.rom.startswith(bytes.fromhex("22 10 93 89"), offset)
            ],
            [0x00006A, 0x0036A0],
        )

    def test_bank_a0_battle_graphics_and_animation_extents(self):
        expected = [
            (0x100000, 0x1003DF, "graphics", "12ffaad7d0888b2157d389edf97349fbaeb8ea04a1c29033b57b62ab44f4bf2a"),
            (0x10079E, 0x102E5D, "graphics", "192d027b266a5ce1c31871a3233345d0a3ed3e1a6e1435acab3fbf7fefa65f46"),
            (0x102E5E, 0x102E6D, "data", "cc8cd41cef907c4d216069122c4b89936211361f9050a717a1e37ad1862e952f"),
            (0x102E7A, 0x103069, "graphics", "5dc63047520b0e5e10d4b98ec6e74b477b35cab49d4c7e9b70902a237bb7a2b0"),
            (0x10306E, 0x103075, "data", "a01bd6d7c4521a8132395250da445216e0ceacc3d8abd937a11d6d9383f2576e"),
            (0x103078, 0x103163, "graphics", "7812a63d8e538eb35e69d959a18c71819e5e74e0d6fb645453565b894f68d9d9"),
            (0x103176, 0x103195, "graphics", "9295db0d1740e4bd1b1aa2920baf56a33c2b857124a36b6af6e82fa13c8a4a2f"),
            (0x103196, 0x1035B5, "graphics", "6480b6c5d5edba34fdc6c0434de8ea51705d7493d913bcde30c5d0ea68cf4414"),
            (0x1035B6, 0x1035D5, "graphics", "85ef162c0d2bf37d6ebfae647e4431190a809f930f74d45724c6d8cb48748e73"),
            (0x1035D6, 0x1035E4, "data", "604d689b27506d20f95dc9a8ede5d9fbfbf3e97306330315bdd5bb6e40be7a92"),
            (0x1035E7, 0x103684, "graphics", "1805cba88d965720a31727903e4099213c15679c7e3d255fb963a55970a3bd2f"),
        ]
        for start, end, region_type, digest in expected:
            with self.subTest(start=f"{start:06X}"):
                region = self.regions[(f"${start:06X}", f"${end:06X}")]
                self.assertEqual(region["type"], region_type)
                self.assertEqual(region["confidence"], "confirmed")
                self.assertEqual(
                    hashlib.sha256(self.rom[start:end + 1]).hexdigest(),
                    digest,
                )

        configuration_pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x16A080, 0x16A120, 2)
        ]
        configuration_selectors = {
            self.rom[0x168000 + pointer - 0x8000]
            for pointer in configuration_pointers[:0x44]
        }
        self.assertEqual(configuration_selectors, set(range(24)))

        for gap_start, gap_end, region_type in [
            (0x102E6E, 0x102E79, "data"),
            (0x10306A, 0x10306D, "data"),
            (0x103076, 0x103077, "data"),
            (0x103164, 0x103175, "graphics"),
            (0x1035E5, 0x1035E6, "data"),
        ]:
            self.assertEqual(
                self.regions[(f"${gap_start:06X}", f"${gap_end:06X}")]["type"],
                region_type,
            )

    def test_bank_98_choice_resource_hierarchy_is_losslessly_partitioned(self):
        table = self.regions[("$0C1B2A", "$0C1E29")]
        self.assertEqual(table["type"], "pointer_table")
        self.assertEqual(table["confidence"], "confirmed")
        corpus = self.regions[("$0C1E2A", "$0C41C7")]
        self.assertEqual(corpus["type"], "text")
        self.assertEqual(corpus["confidence"], "confirmed_structure_partial_schema")

        pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x0C1B2A, 0x0C1E2A, 2)
        ]
        self.assertEqual(len(pointers), 384)
        self.assertEqual(pointers[:373], sorted(pointers[:373]))
        self.assertEqual(len(set(pointers[:373])), 373)
        self.assertEqual(pointers[0], 0x9E2A)
        self.assertEqual(pointers[373:], [0xC1C8] * 11)

        targets = pointers[:373]
        boundaries = targets + [0xC1C8]
        self.assertEqual(
            sum(right - left for left, right in zip(boundaries, boundaries[1:])),
            0xC1C8 - 0x9E2A,
        )
        for left, right in zip(boundaries, boundaries[1:]):
            with self.subTest(target=f"{left:04X}"):
                start = 0x0C0000 + left - 0x8000
                end = 0x0C0000 + right - 0x8000
                self.assertEqual((end - start) % 2, 0)
                self.assertEqual(self.rom[end - 2:end], bytes(2))

        self.assertEqual(0x0C1B2A + 384 * 2, 0x0C1E2A)
        self.assertEqual(self.rom[0x0C41C6:0x0C41C8], bytes(2))
        command_08_table = self.regions[("$0C41C8", "$0C4349")]
        self.assertEqual(command_08_table["type"], "pointer_table")

    def test_bank_94_palette_source_hierarchy(self):
        table = self.regions[("$0A0180", "$0A01FF")]
        self.assertEqual(table["type"], "pointer_table")
        self.assertEqual(table["confidence"], "confirmed")
        corpus = self.regions[("$0A0200", "$0A0BFF")]
        self.assertEqual(corpus["type"], "graphics")
        self.assertEqual(corpus["confidence"], "confirmed")

        pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x0A0180, 0x0A0200, 2)
        ]
        self.assertEqual(len(pointers), 64)
        self.assertEqual(pointers.count(0), 20)
        active = [pointer for pointer in pointers if pointer]
        self.assertEqual(len(active), 44)
        self.assertEqual(
            set(active),
            set(range(0x8200, 0x8C00, 0x40)),
        )
        self.assertEqual(len(set(active)), 40)
        self.assertEqual(pointers[0x30:0x32], [0x8B80, 0x8BC0])
        self.assertEqual(pointers[0x32:], [0] * 14)
        for pointer in set(active):
            start = 0x0A0000 + pointer - 0x8000
            self.assertEqual(len(self.rom[start:start + 0x40]), 0x40)

        self.assertEqual(
            hashlib.sha256(self.rom[0x0A0180:0x0A0200]).hexdigest(),
            "e005c512ab3c5bfcbdafa356c5f04435a54d8f14b470a873a77cd3358110f85a",
        )
        self.assertEqual(
            hashlib.sha256(self.rom[0x0A0200:0x0A0C00]).hexdigest(),
            "e32e8649819415badee850d2d007bd67096335045fbabcda42224a0223d594b8",
        )
        compressed = self.regions[("$0A0D14", "$0A17A0")]
        self.assertEqual(compressed["type"], "compressed_resource")

    def test_bank_82_encounter_lookup_and_display_tables_have_exact_extents(self):
        expected = [
            (0x017705, 0x017749, "data", "fabe5577d070854a04ec481237536ea24967e0d903d1b3a24b073ae27491dcfe"),
            (0x01774D, 0x017761, "data", "229b0fa392a73fb69084892a4c7d95bb5f87b2101184a29535e2f35137f45b30"),
            (0x017762, 0x01777A, "data", "12705d909db44fdf6cac212b0fd8e6e18de103e4bb48d3d39b8635600a0d2306"),
            (0x01777B, 0x017792, "data", "2339375e6a8baabb340ebcdbc15a171202630d3d7847f639b8be699d32afc047"),
            (0x017993, 0x017A1A, "data", "07dd69bc76094e16faaa2942396f4c5670ddc4304134e150f30fe42dc7190282"),
            (0x017A1B, 0x017A36, "text", "eb12b758d30f388c58fd1af692bca3560b8a25403f8eb74bd2fe13825d666577"),
        ]
        for start, end, region_type, digest in expected:
            with self.subTest(start=f"{start:06X}"):
                region = self.regions[(f"${start:06X}", f"${end:06X}")]
                self.assertEqual(region["type"], region_type)
                self.assertEqual(region["confidence"], "confirmed")
                self.assertEqual(
                    hashlib.sha256(self.rom[start:end + 1]).hexdigest(),
                    digest,
                )

        encounter_pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x16A080, 0x16A108, 2)
        ]
        fighter_indexes = [
            self.rom[0x168000 + pointer - 0x8000]
            for pointer in encounter_pointers
        ]
        self.assertEqual(len(encounter_pointers), 68)
        self.assertEqual(set(fighter_indexes), set(range(24)))

        self.assertEqual(self.rom[0x017761], 0xFF)
        self.assertEqual(self.rom[0x01777A], 0xFF)
        self.assertEqual(len(self.rom[0x01777B:0x017793]), 24)
        side_values = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x017993, 0x017A1B, 2)
        ]
        self.assertEqual(set(side_values), {0, 1, 2, 3})
        self.assertEqual(Counter(side_values), Counter({0: 37, 3: 18, 2: 9, 1: 4}))
        self.assertEqual(len(self.rom[0x017993:0x017A1B]), 68 * 2)
        self.assertEqual(self.rom[0x017A35:0x017A37], bytes(2))
        self.assertEqual(self.regions[("$01774A", "$01774C")]["type"], "data")
        self.assertEqual(
            self.regions[("$017793", "$017992")]["confidence"],
            "confirmed_structure_partial_schema",
        )

    def test_bank_84_battle_display_and_coordinate_hierarchy_is_lossless(self):
        records = self.regions[("$023F16", "$024105")]
        self.assertEqual(records["type"], "text")
        self.assertEqual(records["confidence"], "confirmed")
        self.assertEqual(0x024106 - 0x023F16, 31 * 0x10)
        for start in range(0x023F16, 0x024106, 0x10):
            words = [
                int.from_bytes(self.rom[offset:offset + 2], "little")
                for offset in range(start, start + 0x10, 2)
            ]
            self.assertIn(0, words)

        coordinates = self.regions[("$024106", "$024225")]
        self.assertEqual(coordinates["type"], "data")
        self.assertEqual(coordinates["confidence"], "confirmed")
        self.assertEqual(0x024226 - 0x024106, 3 * 24 * 4)
        self.assertEqual(
            hashlib.sha256(self.rom[0x024106:0x024226]).hexdigest(),
            "33a2fb3440932d5880e060b9f4835a657589594c6cef818227109712ace5b7c4",
        )

        pointer_region = self.regions[("$024226", "$02422B")]
        self.assertEqual(pointer_region["type"], "pointer_table")
        pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x024226, 0x02422C, 2)
        ]
        self.assertEqual(pointers, [0xC22C, 0xC374, 0xC4BE])

        corpus = self.regions[("$02422C", "$02454F")]
        self.assertEqual(corpus["type"], "text")
        self.assertEqual(corpus["confidence"], "confirmed")
        boundaries = pointers + [0xC550]
        self.assertEqual(
            sum(right - left for left, right in zip(boundaries, boundaries[1:])),
            0xC550 - 0xC22C,
        )
        for left, right in zip(boundaries, boundaries[1:]):
            start = 0x020000 + left - 0x8000
            end = 0x020000 + right - 0x8000
            self.assertEqual(self.rom[end - 2:end], bytes(2))
            self.assertNotIn(bytes(2), self.rom[start:end - 2])
        self.assertEqual(
            hashlib.sha256(self.rom[0x024226:0x024550]).hexdigest(),
            "481beb9317000a83a92849c61be527c82c2cb6a84d986e47be6430c20e72d9fb",
        )

    def test_bank_ae_animated_cgram_arrays_have_exact_record_domains(self):
        expected = [
            (0x170D88, 0x170F07, "84930143798097180a1d99222124885bbda93c6088b159779409687e331a6ccb"),
            (0x170F08, 0x171087, "0b52f5baec2cf3adc0f9da3dc1896a50bdb81575e4b1bf3440839d3abdcde5ff"),
            (0x171088, 0x171207, "8dba75c9d946e64ddd225326d0f3475c983d68e47008b056b9cb49c4c592067a"),
        ]
        cursor = 0x170D88
        for start, end, digest in expected:
            with self.subTest(start=f"{start:06X}"):
                self.assertEqual(start, cursor)
                region = self.regions[(f"${start:06X}", f"${end:06X}")]
                self.assertEqual(region["type"], "graphics")
                self.assertEqual(region["confidence"], "confirmed")
                data = self.rom[start:end + 1]
                self.assertEqual(len(data), 12 * 0x20)
                self.assertEqual(
                    [len(data[offset:offset + 0x20]) for offset in range(0, len(data), 0x20)],
                    [0x20] * 12,
                )
                self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
                cursor = end + 1
        self.assertEqual(cursor, 0x171208)
        self.assertEqual(
            hashlib.sha256(self.rom[0x170D88:0x171208]).hexdigest(),
            "6c1fa19aaf3a9d40b544c5277916c6d3019aaad271c936fc0690d66b6c72f6e8",
        )

    def test_bank_b6_reachable_glyph_code_lookup_prefix(self):
        region = self.regions[("$1B0000", "$1B0013")]
        self.assertEqual(region["type"], "data")
        self.assertEqual(region["confidence"], "confirmed")
        words = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x1B0000, 0x1B0014, 2)
        ]
        self.assertEqual(
            words,
            [0x0260, 0x0261, 0x0262, 0x0263, 0x0264,
             0x0265, 0x0266, 0x0267, 0x0270, 0x0271],
        )
        timestamp = self.rom[0x007F80:0x007F91]
        indexes = [byte - 0x30 for byte in timestamp if 0x30 <= byte <= 0x39]
        self.assertEqual(set(indexes), {0, 2, 3, 5, 6, 8, 9})
        self.assertEqual(
            hashlib.sha256(self.rom[0x1B0000:0x1B0014]).hexdigest(),
            "3fbca36c1bb70ddd0769e812236cd2e08f497c899ee6369f64ee6f8bbb6c7250",
        )
        self.assertNotIn(("$1B0014", "$1B009F"), self.regions)

    def test_spc_upload_packages_have_exact_length_delimited_extents(self):
        expected = [
            ("$1C0000", "$1C7162", 2, 4),
            ("$1C8000", "$1C8187", 1, 1),
            ("$1D0000", "$1D6682", 15, 31),
            ("$1DCE15", "$1DDEA3", 1, 2),
            ("$1E8000", "$1E9844", 5, 11),
        ]
        for start_text, end_text, package_count, block_count in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "audio")
                offset = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                parsed_blocks = 0
                parsed_packages = 0
                while offset < end:
                    while True:
                        length = int.from_bytes(self.rom[offset : offset + 2], "little")
                        destination = int.from_bytes(
                            self.rom[offset + 2 : offset + 4], "little"
                        )
                        offset += 4
                        if length == 0:
                            self.assertEqual(destination, 0x0800)
                            parsed_packages += 1
                            break
                        offset += length
                        parsed_blocks += 1
                self.assertEqual(offset, end)
                self.assertEqual(parsed_packages, package_count)
                self.assertEqual(parsed_blocks, block_count)

    def test_raw_2bpp_descriptor_tables_own_exact_tile_sets(self):
        descriptor_region = self.regions[("$168000", "$16A07F")]
        self.assertEqual(descriptor_region["type"], "pointer_table")
        self.assertEqual(descriptor_region["confidence"], "confirmed")
        self.assertIn("CPU $82:93FE/$82:9465", descriptor_region["name"])
        self.assertIn("VRAM $4000 or $4B00", descriptor_region["name"])

        observed_sources = {}
        populated_records = 0
        zero_records = 0
        for table_index in range(26):
            table_start = 0x168000 + table_index * 64 * 5
            for index in range(64):
                entry = table_start + index * 5
                pointer = int.from_bytes(self.rom[entry:entry + 3], "little")
                byte_count = int.from_bytes(
                    self.rom[entry + 3:entry + 5], "little"
                )
                if pointer == 0 and byte_count == 0:
                    zero_records += 1
                    continue
                bank = (pointer >> 16) & 0x7F
                address = pointer & 0xFFFF
                self.assertGreaterEqual(address, 0x8000)
                source = bank * 0x8000 + address - 0x8000
                self.assertGreater(byte_count, 0)
                self.assertEqual(byte_count % 0x20, 0)
                self.assertLessEqual(source + byte_count, len(self.rom))
                key = (source, byte_count)
                observed_sources[key] = observed_sources.get(key, 0) + 1
                populated_records += 1

        self.assertEqual(populated_records, 977)
        self.assertEqual(zero_records, 687)
        self.assertEqual(len(observed_sources), 211)
        self.assertEqual(sum(length for _, length in observed_sources), 267_936)

        extents = sorted(
            (start, start + byte_count - 1, byte_count)
            for start, byte_count in observed_sources
        )
        for previous, current in zip(extents, extents[1:]):
            self.assertLess(previous[1], current[0])

        expected_groups = [
            (0x108B4E, 0x10D2ED, 14, 1_146),
            (0x10DCA2, 0x10FDA1, 6, 528),
            (0x1123AC, 0x11638B, 12, 1_022),
            (0x118C02, 0x11FC81, 25, 1_800),
            (0x120AC8, 0x1230A7, 9, 606),
            (0x12394A, 0x124A69, 4, 274),
            (0x128920, 0x12B7DF, 9, 748),
            (0x12C1B2, 0x12EE31, 9, 712),
            (0x1308B4, 0x1320F3, 5, 388),
            (0x1328C4, 0x134243, 5, 408),
            (0x134C2A, 0x137DC9, 9, 794),
            (0x138000, 0x13857F, 1, 88),
            (0x138D60, 0x13A25F, 4, 336),
            (0x13ACFA, 0x13EBB9, 12, 1_004),
            (0x140A44, 0x142EE3, 7, 586),
            (0x1436AA, 0x145089, 5, 414),
            (0x1459D2, 0x146D91, 4, 316),
            (0x148CD0, 0x14CEEF, 14, 1_058),
            (0x14D77E, 0x14F05D, 5, 398),
            (0x1509DE, 0x15781D, 23, 1_764),
            (0x1F2E4A, 0x1F58E9, 8, 682),
            (0x1F8C00, 0x1FCCBF, 13, 1_036),
            (0x1FD666, 0x1FFE45, 8, 638),
        ]
        observed_groups = []
        for extent in extents:
            if not observed_groups or extent[0] != observed_groups[-1][-1][1] + 1:
                observed_groups.append([extent])
            else:
                observed_groups[-1].append(extent)

        self.assertEqual(len(observed_groups), len(expected_groups))
        for group, (start, end, extent_count, tile_count) in zip(
            observed_groups, expected_groups
        ):
            self.assertEqual(group[0][0], start)
            self.assertEqual(group[-1][1], end)
            self.assertEqual(len(group), extent_count)
            self.assertEqual(sum(item[2] for item in group) // 16, tile_count)
            region = self.regions[(f"${start:06X}", f"${end:06X}")]
            self.assertEqual(region["type"], "graphics")
            self.assertEqual(region["confidence"], "confirmed")
            self.assertIn(f"{tile_count:,} complete tiles", region["name"])

    def test_raw_2bpp_descriptor_selector_and_dma_path(self):
        pointer_table_start = 0x16A080
        pointers = [
            int.from_bytes(
                self.rom[pointer_table_start + index * 2:pointer_table_start + index * 2 + 2],
                "little",
            )
            for index in range(80)
        ]
        self.assertEqual(pointers[0], 0xA120)
        self.assertEqual(pointers[0x43], 0xB662)
        self.assertEqual(pointers[0x44:], [0xB68A] * 12)
        self.assertEqual(len(set(pointers)), 69)
        self.assertEqual(pointers, sorted(pointers))

        selectors = []
        table_01_record_indices = []
        table_2_25_record_indices = []
        record_lengths = []
        record_modes = []
        appended_mode_blocks = {}
        for pointer, next_pointer in zip(pointers[:0x44], pointers[1:0x45]):
            record = 0x168000 + pointer - 0x8000
            record_length = next_pointer - pointer
            selectors.append(self.rom[record])
            table_01_record_indices.append(self.rom[record + 4])
            table_2_25_record_indices.append(self.rom[record + 9])
            record_lengths.append(record_length)

            # CPU $82:8D65-$82:8E30 consumes a fixed header through +$1F.
            mode = self.rom[record + 0x20]
            record_modes.append(mode)
            if mode == 0:
                count = self.rom[record + 0x21]
                confirmed_length = 0x22 + count * 2
                self.assertLessEqual(confirmed_length, record_length)
                if confirmed_length != record_length:
                    appended_mode_blocks[pointer] = record_length - confirmed_length
            elif mode == 1:
                # Two 16-word lists begin at +$21 and +$41.
                self.assertEqual(record_length, 0x61)
            elif mode == 2:
                # A 16-word list begins at +$21; +$41 holds six four-word slots.
                self.assertEqual(record_length, 0x71)
            else:
                self.fail(f"unexpected configuration-record mode {mode:#04x}")
        self.assertEqual(len(record_lengths), 68)
        self.assertTrue(all(length > 0 for length in record_lengths))
        self.assertEqual(sum(record_lengths), 0x156A)
        self.assertEqual(pointers[0] + sum(record_lengths), 0xB68A)
        self.assertEqual(set(selectors), set(range(24)))
        self.assertTrue(all(index < 64 for index in table_01_record_indices))
        self.assertTrue(all(index < 64 for index in table_2_25_record_indices))
        self.assertEqual(Counter(record_modes), Counter({0: 33, 1: 11, 2: 24}))
        descriptor_tables = [
            self.rom[0x168000 + 0x280 + index * 0x140:0x168000 + 0x280 + (index + 1) * 0x140]
            for index in range(24)
        ]
        self.assertEqual(descriptor_tables[0], bytes(0x140))
        self.assertEqual(descriptor_tables[6], bytes(0x140))
        self.assertEqual(descriptor_tables[2], descriptor_tables[4])
        self.assertTrue(all(any(descriptor_tables[index]) for index in set(range(24)) - {0, 6}))

        # Configuration header +$00 is reused as an entity-level resource selector.
        selector_consumers = self.rom[0x01117B:0x0113F4]
        self.assertIn(bytes.fromhex("AD 27 0E E2 20 8D 02 42 A9 20 8D 03 42"), selector_consumers)
        self.assertIn(bytes.fromhex("AD 27 0E C9 FF FF F0"), selector_consumers)
        sprite_consumer = self.rom[0x0114CB:0x0115B4]
        self.assertIn(bytes.fromhex("AD 27 0E C9 FF FF F0 34 E2 20 8D 02 42 A9 40 8D 03 42"), sprite_consumer)
        descriptor_consumer = self.rom[0x011465:0x0114C6]
        self.assertIn(bytes.fromhex("AD 27 0E C9 FF FF F0 45 E2 20 8D 02 42 A9 40 8D 03 42"), descriptor_consumer)
        fighter_name_consumer = self.rom[0x016E8C:0x016F29]
        self.assertIn(bytes.fromhex("AD 27 0E 0A 0A 0A 0A C2 30 AA"), fighter_name_consumer)
        self.assertIn(bytes.fromhex("BF 16 BF 84"), fighter_name_consumer)
        self.assertEqual(
            appended_mode_blocks,
            {0xA780: 81, 0xA8EE: 81, 0xAAED: 65},
        )

        appended_selector_blocks = {
            0xA7A8: (2, 81),
            0xA916: (2, 81),
            0xAB15: (1, 65),
        }
        for address, (mode, length) in appended_selector_blocks.items():
            start = 0x168000 + address - 0x8000
            self.assertEqual(self.rom[start], mode)
            self.assertEqual(
                self.rom.count(address.to_bytes(2, "little") + bytes([0xAD])),
                0,
            )
            if mode == 1:
                self.assertEqual(length, 1 + 32 * 2)
            else:
                self.assertEqual(length, 1 + 16 * 2 + 6 * 4 * 2)

        self.assertEqual(self.rom.count(bytes.fromhex("BF 80 A0 AD")), 4)
        for pointer in (0xA780, 0xA8EE, 0xAAED):
            record = 0x168000 + pointer - 0x8000
            self.assertEqual(self.rom[record + 0x20], 0)
            self.assertEqual(self.rom[record + 0x21], 3)
            self.assertEqual(pointer + 0x28, {0xA780: 0xA7A8, 0xA8EE: 0xA916, 0xAAED: 0xAB15}[pointer])

        pointer_region = self.regions[("$16A080", "$16A11F")]
        self.assertEqual(pointer_region["type"], "pointer_table")
        self.assertEqual(pointer_region["confidence"], "confirmed")
        configuration_region = self.regions[("$16A120", "$16B689")]
        self.assertEqual(configuration_region["type"], "data")
        self.assertEqual(
            configuration_region["confidence"],
            "confirmed_structure_partial_schema",
        )

        final_record_writers = self.rom[0x018510:0x0185A0]
        for index in (0x42, 0x43):
            self.assertEqual(
                final_record_writers.count(
                    bytes.fromhex(f"A9 {index:02X} 00 8D 2B 0E 22 00 80 82")
                ),
                2,
            )

        configuration_decode = self.rom[0x010DC3:0x010E76]
        self.assertIn(bytes.fromhex("B9 00 00 29 FF 00 8D 27 0E"), configuration_decode)
        self.assertIn(bytes.fromhex("B9 04 00 29 FF 00 8D B0 0D"), configuration_decode)
        self.assertIn(bytes.fromhex("B9 09 00 29 FF 00 8D B8 0D"), configuration_decode)
        for offset in range(0x0E, 0x20, 2):
            self.assertIn(bytes.fromhex(f"B9 {offset:02X} 00"), configuration_decode)

        second_candidate_selector = self.rom[0x010AE6:0x010B8A]
        self.assertIn(bytes.fromhex("B9 20 00 29 FF 00 C9 01 00"), second_candidate_selector)
        self.assertIn(bytes.fromhex("B9 21 00 29 FF 00 22 70 91 80"), second_candidate_selector)
        self.assertIn(bytes.fromhex("B9 41 00 8D 42 0E"), second_candidate_selector)
        self.assertIn(bytes.fromhex("B9 00 00 29 FF 00 AB 0A 0A 0A"), second_candidate_selector)
        self.assertIn(bytes.fromhex("A9 04 00 22 70 91 80"), second_candidate_selector)

        first_candidate_selector = self.rom[0x010BDC:0x010C42]
        self.assertIn(bytes.fromhex("B9 20 00 29 FF 00 C9 01 00 B0"), first_candidate_selector)
        self.assertIn(bytes.fromhex("B9 21 00 29 FF 00 22 70 91 80"), first_candidate_selector)
        self.assertIn(bytes.fromhex("B9 21 00 8D 42 0E"), first_candidate_selector)

        action_name_pointer_region = self.regions[("$024550", "$0246CF")]
        self.assertEqual(action_name_pointer_region["type"], "pointer_table")
        self.assertEqual(action_name_pointer_region["confidence"], "confirmed")
        action_name_region = self.regions[("$0246D0", "$024DD9")]
        self.assertEqual(action_name_region["type"], "text")
        self.assertEqual(
            action_name_region["confidence"],
            "confirmed_structure_partial_schema",
        )

        action_name_pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x024550, 0x0246D0, 2)
        ]
        self.assertEqual(len(action_name_pointers), 192)
        self.assertEqual(action_name_pointers[0x00], 0xC6D0)
        self.assertEqual(action_name_pointers[0x46:0x80], [0xCAD6] * 58)
        self.assertEqual(action_name_pointers[0x80], 0xCAD8)
        self.assertEqual(action_name_pointers[0xB1], 0xCDCC)
        self.assertEqual(action_name_pointers[0xB2:], [0xCDD8] * 14)
        self.assertEqual(self.rom[0x024AD6:0x024AD8], bytes(2))
        self.assertEqual(self.rom[0x024DD8:0x024DDA], bytes(2))

        active_action_names = sorted(
            set(action_name_pointers[:0x47] + action_name_pointers[0x80:0xB2])
        )
        self.assertEqual(len(active_action_names), 121)
        self.assertEqual(active_action_names[0], 0xC6D0)
        self.assertEqual(active_action_names[-1], 0xCDCC)
        for current, following in zip(active_action_names, active_action_names[1:]):
            self.assertEqual((following - current) % 2, 0)
            following_offset = 0x020000 + following - 0x8000
            self.assertEqual(self.rom[following_offset - 2:following_offset], bytes(2))
        self.assertEqual(0xCDD8 - active_action_names[-1], 12)

        action_pointer_region = self.regions[("$024E12", "$024F91")]
        self.assertEqual(action_pointer_region["type"], "pointer_table")
        self.assertEqual(action_pointer_region["confidence"], "confirmed")
        action_record_region = self.regions[("$024F92", "$0252D9")]
        self.assertEqual(action_record_region["type"], "data")
        self.assertEqual(
            action_record_region["confidence"],
            "confirmed_structure_partial_schema",
        )

        action_pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x024E12, 0x024F92, 2)
        ]
        self.assertEqual(len(action_pointers), 192)
        self.assertEqual(action_pointers[0x00], 0xCF92)
        self.assertEqual(action_pointers[0x46], 0xD17C)
        self.assertEqual(action_pointers[0x47:0x80], [0xD17C] * 57)
        self.assertEqual(action_pointers[0x80], 0xD17C)
        self.assertEqual(action_pointers[0xB1], 0xD2D3)
        self.assertEqual(action_pointers[0xB2:], [0xD2DA] * 14)

        unique_action_pointers = sorted(set(action_pointers[:0xB2]))
        self.assertEqual(len(unique_action_pointers), 120)
        self.assertEqual(
            unique_action_pointers,
            list(range(0xCF92, 0xD2DA, 7)),
        )
        action_classes = []
        for address in unique_action_pointers:
            record = 0x020000 + address - 0x8000
            action_classes.append(self.rom[record])
        self.assertEqual(set(action_classes), set(range(6)))
        self.assertEqual(
            Counter(action_classes),
            Counter({0: 26, 1: 19, 2: 19, 3: 20, 4: 21, 5: 15}),
        )

        player_field_2 = []
        for index in range(0x47):
            record = 0x020000 + action_pointers[index] - 0x8000
            player_field_2.append(self.rom[record + 2])
        self.assertEqual(Counter(player_field_2), Counter({0: 31, 1: 25, 2: 14, 0xFF: 1}))
        self.assertEqual(
            {
                self.rom[0x020000 + action_pointers[index] - 0x8000 + 2]
                for index in range(0x80, 0xB2)
            },
            {0xFF},
        )

        player_families = {}
        for index in range(0x46):
            record = 0x020000 + action_pointers[index] - 0x8000
            family = (self.rom[record], self.rom[record + 1])
            tier = self.rom[record + 2]
            coefficient = int.from_bytes(self.rom[record + 3:record + 5], "little")
            self.assertIn(tier, range(3))
            player_families.setdefault(family, []).append((tier, coefficient))
        for family, variants in player_families.items():
            for lower_tier, lower_coefficient in variants:
                for upper_tier, upper_coefficient in variants:
                    if lower_tier < upper_tier:
                        self.assertLessEqual(
                            lower_coefficient,
                            upper_coefficient,
                            f"action family {family} is not coefficient-ordered by +$02",
                        )

        first_player_bank = [
            tuple(self.rom[0x020000 + action_pointers[index] - 0x8000:][:3])
            for index in range(0x20)
        ]
        second_player_bank = [
            tuple(self.rom[0x020000 + action_pointers[index] - 0x8000:][:3])
            for index in range(0x20, 0x40)
        ]
        expected_classes = [3] * 8 + [0] * 8 + [1] * 8 + [2] * 8
        self.assertEqual([record[0] for record in first_player_bank], expected_classes)
        self.assertEqual([record[0] for record in second_player_bank], expected_classes)
        self.assertEqual(
            [record[1] for record in first_player_bank],
            [
                0x0A, 0x0A, 0x0B, 0x0B, 0x0C, 0x0C, 0x0D, 0x0D,
                0x00, 0x00, 0x00, 0x01, 0x01, 0x01, 0x02, 0x03,
                0x04, 0x04, 0x05, 0x05, 0x05, 0x06, 0x06, 0x06,
                0x07, 0x07, 0x07, 0x08, 0x08, 0x08, 0x09, 0x09,
            ],
        )
        self.assertEqual(
            [record[1] for record in second_player_bank],
            [
                0x0A, 0x0A, 0x0A, 0x0B, 0x0C, 0x0D, 0x0D, 0x0D,
                0x00, 0x00, 0x00, 0x01, 0x01, 0x01, 0x02, 0x02,
                0x04, 0x04, 0x04, 0x05, 0x05, 0x06, 0x06, 0x06,
                0x07, 0x07, 0x07, 0x08, 0x08, 0x08, 0x09, 0x09,
            ],
        )
        exceptional_records = [
            self.rom[0x020000 + action_pointers[index] - 0x8000:][:7]
            for index in range(0x40, 0x46)
        ]
        self.assertEqual([record[0] for record in exceptional_records], [5, 4, 4, 5, 4, 4])
        self.assertEqual(
            [int.from_bytes(record[3:5], "little") for record in exceptional_records],
            [0, 2000, 3000, 0, 1800, 3600],
        )

        action_table_load = bytes.fromhex("BF 12 CE 84")
        direct_consumer_offsets = []
        search_offset = 0
        while True:
            search_offset = self.rom.find(action_table_load, search_offset)
            if search_offset < 0:
                break
            direct_consumer_offsets.append(search_offset)
            search_offset += len(action_table_load)
        self.assertEqual(len(direct_consumer_offsets), 24)

        consumed_record_offsets = []
        for consumer_offset in direct_consumer_offsets:
            consumer = self.rom[consumer_offset + 4:consumer_offset + 12]
            self.assertEqual(consumer[0], 0xA8)  # TAY
            self.assertEqual(consumer[1], 0xB9)  # LDA $xxxx,Y
            consumed_record_offsets.append(int.from_bytes(consumer[2:4], "little"))
        self.assertEqual(
            set(consumed_record_offsets),
            {0x0000, 0x0001, 0x0003, 0x0005, 0x0006},
        )
        self.assertNotIn(0x0002, consumed_record_offsets)
        self.assertNotIn(bytes.fromhex("BD 12 CE"), self.rom)
        self.assertNotIn(bytes.fromhex("B9 12 CE"), self.rom)
        self.assertNotIn(bytes.fromhex("AF 12 CE 84"), self.rom)
        self.assertNotIn(bytes.fromhex("A9 12 CE"), self.rom)

        # Player unlocks and equipped slots use flat action IDs rather than +$02.
        unlock_calls = []
        unlock_call = bytes.fromhex("22 FB ED 82")
        search_offset = 0
        while True:
            search_offset = self.rom.find(unlock_call, search_offset)
            if search_offset < 0:
                break
            immediate = self.rom[search_offset - 3:search_offset]
            if len(immediate) == 3 and immediate[0] == 0xA9:
                unlock_calls.append(int.from_bytes(immediate[1:3], "little"))
            search_offset += len(unlock_call)
        self.assertEqual(set(unlock_calls), set(range(0x40)))

        action_menu = self.rom[0x00AF11:0x00B7E0]
        self.assertEqual(
            action_menu.count(bytes.fromhex("A5 13 0A 0A 0A 18 6D 2F 02 85 27")),
            8,
        )
        self.assertEqual(action_menu.count(bytes.fromhex("BD 2E 0D 25 37")), 4)
        self.assertEqual(action_menu.count(bytes.fromhex("A5 27 9D 96 0C")), 4)

        unlock_setter = self.rom[0x016DFB:0x016E2A]
        self.assertIn(bytes.fromhex("C2 20 85 4E 4A 4A 4A 4A 85 50"), unlock_setter)
        self.assertIn(bytes.fromhex("BD 2E 0D 05 00 9D 2E 0D"), unlock_setter)

        class_pair_region = self.regions[("$024DDA", "$024E11")]
        self.assertEqual(class_pair_region["type"], "data")
        self.assertEqual(
            class_pair_region["confidence"],
            "confirmed_structure_partial_schema",
        )
        class_pair_matrix = self.rom[0x024DDA:0x024E12]
        self.assertEqual(len(class_pair_matrix), 7 * 8)
        self.assertEqual(set(class_pair_matrix), {0, 1, 2, 3, 0xFF})
        self.assertEqual(
            [list(class_pair_matrix[row * 8:(row + 1) * 8]) for row in range(7)],
            [
                [2, 0, 2, 1, 1, 0, 0, 0xFF],
                [1, 2, 0, 2, 1, 0, 0, 0xFF],
                [2, 1, 2, 0, 1, 0, 0, 0xFF],
                [0, 2, 1, 2, 1, 0, 0, 0xFF],
                [0, 0, 0, 0, 3, 1, 0, 0xFF],
                [1, 1, 1, 1, 0, 2, 0, 0xFF],
                [1, 1, 1, 1, 1, 1, 0xFF, 0xFF],
            ],
        )
        self.assertEqual(self.rom.count(bytes.fromhex("BF DA CD 84")), 1)
        class_pair_consumer = self.rom[0x0119C8:0x011A46]
        self.assertIn(bytes.fromhex("B9 00 00 29 FF 00 0A 0A 0A 85 04"), class_pair_consumer)
        self.assertIn(bytes.fromhex("B9 00 00 29 FF 00 18 65 04 AA BF DA CD 84"), class_pair_consumer)
        active_classes = set(action_classes)
        self.assertEqual(active_classes, set(range(6)))
        reachable_offsets = {
            player_class * 8 + opponent_class
            for player_class in active_classes
            for opponent_class in active_classes
        }
        self.assertEqual(len(reachable_offsets), 36)
        self.assertTrue(all(offset < 6 * 8 for offset in reachable_offsets))
        self.assertTrue(all(offset % 8 < 6 for offset in reachable_offsets))

        outcome_resolver = self.rom[0x0119C8:0x011AAE]
        self.assertIn(bytes.fromhex("C9 03 00 D0 34 20 0E 9D"), outcome_resolver)
        self.assertIn(bytes.fromhex("C9 05 00 B0 18"), outcome_resolver)
        self.assertIn(bytes.fromhex("A9 02 00 80 08 A9 01 00 80 03 A9 00 00 8D 48 0E"), outcome_resolver)

        damage_outcome = self.rom[0x011DA6:0x011F78]
        self.assertIn(bytes.fromhex("AD 48 0E C9 02 00 D0 03 4C 69 9F"), damage_outcome)
        self.assertIn(bytes.fromhex("C9 01 00 D0 03 4C 78 9E"), damage_outcome)
        self.assertIn(bytes.fromhex("AD 68 0E 38 ED 9B 0E"), damage_outcome)
        self.assertIn(bytes.fromhex("AD 66 0E 38 ED 9B 0E"), damage_outcome)
        self.assertIn(bytes.fromhex("A9 00 00 8D 25 0E 9C 52 0E 9C 54 0E"), damage_outcome)

        outcome_palette = self.rom[0x011A45:0x011AAE]
        self.assertIn(bytes.fromhex("BF AE 9A 82 9D 28 04 BF B6 9A 82 9D 30 04"), outcome_palette)
        self.assertIn(bytes.fromhex("BF B6 9A 82 9D 28 04 BF AE 9A 82 9D 30 04"), outcome_palette)
        self.assertIn(bytes.fromhex("BF BE 9A 82 9D 28 04 9D 30 04"), outcome_palette)

        opponent_success_log = self.rom[0x016E2A:0x016E7B]
        self.assertIn(bytes.fromhex("AD 48 0E F0 49 C9 02 00 F0 44"), opponent_success_log)
        self.assertEqual(
            self.rom[0x01777B:0x017793],
            bytes(range(0xA2, 0xB2)) + bytes(range(0x86, 0x8E)),
        )

        self.assertEqual(self.rom.count(bytes.fromhex("BF 50 C5 84")), 14)
        dash_punch_player = 0x38
        dash_punch_opponent = 0x91
        self.assertNotEqual(
            action_name_pointers[dash_punch_player],
            action_name_pointers[dash_punch_opponent],
        )
        self.assertNotEqual(
            action_pointers[dash_punch_player],
            action_pointers[dash_punch_opponent],
        )
        player_name_offset = (
            0x020000 + action_name_pointers[dash_punch_player] - 0x8000
        )
        opponent_name_offset = (
            0x020000 + action_name_pointers[dash_punch_opponent] - 0x8000
        )
        self.assertEqual(
            self.rom[player_name_offset:player_name_offset + 16],
            self.rom[opponent_name_offset:opponent_name_offset + 16],
        )

        side_initializer_region = self.regions[("$023ECE", "$023F15")]
        self.assertEqual(side_initializer_region["type"], "data")
        self.assertEqual(
            side_initializer_region["confidence"],
            "confirmed_structure_partial_schema",
        )
        side_records = self.rom[0x023ECE:0x023F16]
        self.assertEqual(len(side_records), 0x48)
        self.assertEqual(side_records[0x10:0x15], bytes([0x02] * 5))
        self.assertEqual(side_records[0x34:0x39], bytes([0x25] * 5))

        # CPU $80:9555 chooses one of the two $24-byte side records.
        self.assertEqual(
            self.rom[0x001555:0x00156A],
            bytes.fromhex("08 C2 20 AD 5A 02 C9 02 00 B0 05 A9 00 00 28 6B A9 24 00 28 6B"),
        )

        # CPU $82:D4CF maps normal input to a five-entry side row and maps
        # special two-button cases directly to action indexes $40-$44.
        player_selector = self.rom[0x0154CF:0x01557D]
        for direct_index in range(0x40, 0x45):
            self.assertIn(
                bytes.fromhex(f"A9 {direct_index:02X} 00 80"),
                player_selector,
            )
        self.assertIn(bytes.fromhex("22 55 95 80 18 65 23 C2 30 AA"), player_selector)
        self.assertIn(bytes.fromhex("BD 96 0C 29 FF 00 8D 40 0E"), player_selector)

        configuration_candidates = []
        for pointer, next_pointer in zip(pointers[:0x44], pointers[1:0x45]):
            record = 0x168000 + pointer - 0x8000
            mode = self.rom[record + 0x20]
            if mode == 0:
                count = self.rom[record + 0x21]
                candidate_offsets = range(record + 0x22, record + 0x22 + count * 2, 2)
            elif mode == 1:
                candidate_offsets = range(record + 0x21, record + 0x61, 2)
            else:
                candidate_offsets = range(record + 0x21, record + 0x71, 2)
            configuration_candidates.extend(
                int.from_bytes(self.rom[offset:offset + 2], "little")
                for offset in candidate_offsets
            )
        self.assertEqual(min(configuration_candidates), 0x80)
        self.assertEqual(max(configuration_candidates), 0xB1)
        self.assertTrue(all(0x80 <= value <= 0xB1 for value in configuration_candidates))

        configuration_00 = 0x168000 + pointers[0x00] - 0x8000
        self.assertEqual(self.rom[configuration_00 + 0x20], 0)
        self.assertEqual(self.rom[configuration_00 + 0x21], 3)
        self.assertEqual(
            [
                int.from_bytes(self.rom[offset:offset + 2], "little")
                for offset in range(configuration_00 + 0x22, configuration_00 + 0x28, 2)
            ],
            [0x84, 0x8F, 0x91],
        )
        configuration_03 = 0x168000 + pointers[0x03] - 0x8000
        self.assertEqual(self.rom[configuration_03 + 0x20], 2)
        configuration_03_candidates = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(configuration_03 + 0x21, configuration_03 + 0x71, 2)
        ]
        self.assertEqual(min(configuration_03_candidates), 0x80)
        self.assertEqual(max(configuration_03_candidates), 0xA3)

        # Identified consumers load +$03 as one 16-bit coefficient. No
        # identified action-record consumer reads the independent byte +$02.
        combat_coefficient_consumers = self.rom[0x011DEB:0x011F43]
        self.assertEqual(
            combat_coefficient_consumers.count(bytes.fromhex("B9 03 00 8D 95 0E")),
            2,
        )

        descriptor_consumers = self.rom[0x01140E:0x0114C5]
        for operand in ("BF 00 80 AD", "BF 40 81 AD", "BF 80 82 AD"):
            self.assertIn(bytes.fromhex(operand), descriptor_consumers)
        self.assertIn(bytes.fromhex("A9 00 40 85 EB"), descriptor_consumers)
        self.assertIn(bytes.fromhex("A9 00 4B 85 EB"), descriptor_consumers)
        self.assertEqual(descriptor_consumers.count(bytes.fromhex("A9 40 00 04 DC")), 2)

        vblank_dma = self.rom[0x00059F:0x0005ED]
        self.assertIn(bytes.fromhex("A9 01 8D 70 43"), vblank_dma)
        self.assertIn(bytes.fromhex("A9 18 8D 71 43"), vblank_dma)
        self.assertIn(bytes.fromhex("A5 EA 8D 74 43"), vblank_dma)
        self.assertIn(bytes.fromhex("65 EB 8D 16 21"), vblank_dma)
        self.assertIn(bytes.fromhex("65 E8 8D 72 43"), vblank_dma)
        self.assertIn(bytes.fromhex("8D 75 43 E2 20 A9 80 8D 0B 42"), vblank_dma)

    def test_referenced_brr_records_partition_confirmed_audio_ranges(self):
        selector_bytes = self.rom[0x018298:0x018302]
        sample_indices = sorted(set(selector_bytes) - {0xFF})
        self.assertEqual(len(sample_indices), 35)
        self.assertEqual(sample_indices[0], 0x10)
        self.assertEqual(sample_indices[-1], 0x36)

        records = []
        for sample_index in sample_indices:
            descriptor_offset = 0x018302 + sample_index * 4
            self.assertEqual(self.rom[descriptor_offset], sample_index)
            pointer = int.from_bytes(
                self.rom[descriptor_offset + 1 : descriptor_offset + 4], "little"
            )
            record_offset = ((pointer >> 16) & 0x7F) * 0x8000 + (pointer & 0xFFFF) - 0x8000
            loop_offset = int.from_bytes(self.rom[record_offset : record_offset + 2], "little")
            byte_length = int.from_bytes(
                self.rom[record_offset + 2 : record_offset + 4], "little"
            )
            self.assertEqual(byte_length % 9, 0)
            self.assertLessEqual(loop_offset, byte_length)
            self.assertEqual(loop_offset % 9, 0)
            payload = self.rom[record_offset + 4 : record_offset + 4 + byte_length]
            end_blocks = [
                block
                for block in range(byte_length // 9)
                if payload[block * 9] & 0x01
            ]
            self.assertEqual(end_blocks, [byte_length // 9 - 1])
            records.append((record_offset, record_offset + 4 + byte_length))

        self.assertEqual(sum(end - start for start, end in records), 102_947)
        records.sort()
        for (_, previous_end), (current_start, _) in zip(records, records[1:]):
            self.assertGreaterEqual(current_start, previous_end)

        expected_regions = [
            ("$1C8188", "$1CF296"),
            ("$1D8000", "$1DCE14"),
            ("$1E0000", "$1E65D8"),
            ("$1E9845", "$1EE18A"),
            ("$1F0000", "$1F23DF"),
        ]
        for start, end in expected_regions:
            self.assertEqual(self.regions[(start, end)]["type"], "audio")

    def test_spc_bootstrap_reconstructs_confirmed_apu_memory_map(self):
        def lorom_offset(pointer: int) -> int:
            return ((pointer >> 16) & 0x7F) * 0x8000 + (pointer & 0xFFFF) - 0x8000

        apu = bytearray(0x10000)
        written = bytearray(0x10000)
        package_pointers = []
        for index in range(4):
            pointer_offset = 0x01828C + index * 3
            package_pointers.append(
                int.from_bytes(self.rom[pointer_offset : pointer_offset + 3], "little")
            )
        self.assertEqual(
            package_pointers,
            [0xB88000, 0xBBCE15, 0xB89135, 0xB98000],
        )

        for pointer in package_pointers:
            offset = lorom_offset(pointer)
            while True:
                length = int.from_bytes(self.rom[offset : offset + 2], "little")
                destination = int.from_bytes(
                    self.rom[offset + 2 : offset + 4], "little"
                )
                offset += 4
                if length == 0:
                    self.assertEqual(destination, 0x0800)
                    break
                apu[destination : destination + length] = self.rom[offset : offset + length]
                written[destination : destination + length] = bytes([1]) * length
                offset += length

        runs = []
        cursor = 0
        while cursor < len(written):
            if not written[cursor]:
                cursor += 1
                continue
            end = cursor + 1
            while end < len(written) and written[end]:
                end += 1
            runs.append((cursor, end))
            cursor = end
        self.assertEqual(
            runs,
            [
                (0x0800, 0x1921),
                (0x1B00, 0x1D80),
                (0x1E00, 0x1E5E),
                (0x1F00, 0x2F27),
                (0x4000, 0x9F22),
            ],
        )

        directory = [
            (
                int.from_bytes(apu[0x1B00 + index * 4 : 0x1B02 + index * 4], "little"),
                int.from_bytes(apu[0x1B02 + index * 4 : 0x1B04 + index * 4], "little"),
            )
            for index in range(64)
        ]
        active_indices = [
            index
            for index, entry in enumerate(directory)
            if entry != (0x4000, 0x4000)
        ]
        self.assertEqual(
            active_indices,
            list(range(0x0E)) + [0x3C, 0x3E, 0x3F],
        )

        resident_records = []
        for index in active_indices:
            start, loop = directory[index]
            self.assertGreaterEqual(start, 0x4000)
            self.assertGreaterEqual(loop, start)
            self.assertLess(loop, 0x9F22)
            self.assertEqual((loop - start) % 9, 0)
            cursor = start
            end_blocks = 0
            while True:
                header = apu[cursor]
                cursor += 9
                if header & 0x01:
                    end_blocks += 1
                    break
                self.assertLess(cursor, 0x9F22)
            self.assertEqual(end_blocks, 1)
            resident_records.append((start, cursor))
        self.assertEqual(min(start for start, _ in resident_records), 0x4000)
        self.assertEqual(max(end for _, end in resident_records), 0x9F22)

        instruments = [
            bytes(apu[0x1C00 + index * 6 : 0x1C06 + index * 6])
            for index in range(64)
        ]
        self.assertEqual(len(instruments), 64)
        self.assertEqual([record[0] for record in instruments[:0x0E]], list(range(0x0E)))
        self.assertTrue(all(record[0] < 64 for record in instruments))
        self.assertTrue(all(record[3] == 0xB8 for record in instruments))
        pitch_multipliers = [
            int.from_bytes(record[4:6], "big")
            for record in instruments
        ]
        self.assertEqual(pitch_multipliers[:5], [0x0200, 0x0200, 0x0200, 0x02B0, 0x0290])
        self.assertEqual(pitch_multipliers[0x3E:], [0x01F0, 0x0110])

        self.assertEqual(int.from_bytes(apu[0x1E00:0x1E02], "little"), 0x2000)
        sequence_pointers = [
            int.from_bytes(apu[offset : offset + 2], "little")
            for offset in range(0x1E02, 0x1E5C, 2)
        ]
        self.assertEqual(len(sequence_pointers), 45)
        self.assertEqual(sequence_pointers[0], 0x1F00)
        self.assertEqual(sequence_pointers[-1], 0x2034)
        self.assertEqual(sequence_pointers, sorted(sequence_pointers))
        self.assertTrue(all(0x1F00 <= pointer < 0x2F27 for pointer in sequence_pointers))
        self.assertEqual(apu[0x1E5C:0x1E5E], b"\x00\x00")

        self.assertEqual(apu[0x0800:0x0805], bytes.fromhex("20 cd 7f bd e8"))
        self.assertEqual(apu[0x0FA4:0x0FB2], bytes.fromhex("cc f2 00 c5 f3 00 6f cc f2 00 e5 f3 00 6f"))
        self.assertEqual(
            apu[0x0F2A:0x0F3A],
            bytes([1, 2, 4, 8, 16, 32, 64, 128]) * 2,
        )
        self.assertEqual(
            list(apu[0x0F6C:0x0F8C]),
            [
                2, 2, 3, 4, 1, 2, 3, 2,
                3, 2, 2, 4, 1, 2, 3, 4,
                2, 4, 4, 1, 2, 4, 1, 4,
                4, 4, 2, 1, 2, 3, 4, 1,
            ],
        )
        event_handlers = [
            int.from_bytes(apu[offset : offset + 2], "little")
            for offset in range(0x1182, 0x11C2, 2)
        ]
        self.assertEqual(
            event_handlers,
            [
                0x11C2, 0x122E, 0x123D, 0x125A, 0x1277, 0x127D, 0x128C, 0x12A1,
                0x12B7, 0x12D4, 0x12DA, 0x12E1, 0x12FE, 0x1304, 0x1312, 0x132E,
                0x1377, 0x1390, 0x13A8, 0x13C0, 0x13CA, 0x13D1, 0x13F5, 0x140D,
                0x1466, 0x147E, 0x149F, 0x14A6, 0x14AC, 0x14B3, 0x14C0, 0x14D8,
            ],
        )
        parameter_reader = bytes.fromhex("3f b2 0f")
        handler_ends = event_handlers[1:] + [0x14DA]
        parameter_reads = [
            sum(
                apu[offset : offset + 3] == parameter_reader
                for offset in range(handler, end - 2)
            )
            for handler, end in zip(event_handlers, handler_ends)
        ]
        self.assertEqual(
            parameter_reads,
            [length - 1 for length in apu[0x0F6C:0x0F8C]],
        )
        self.assertEqual(apu[0x14AC:0x14D8].count(parameter_reader), 6)
        self.assertEqual(
            apu[0x14AC:0x14D8],
            bytes.fromhex(
                "3f b2 0f d5 60 06 6f "
                "3f b2 0f d5 70 06 3f b2 0f d5 80 06 6f "
                "e8 01 d5 90 06 3f b2 0f d5 80 03 "
                "3f b2 0f d5 d0 03 3f b2 0f d5 c0 03 6f"
            ),
        )
        port_handlers = [
            int.from_bytes(apu[offset : offset + 2], "little")
            for offset in range(0x17EA, 0x181A, 2)
        ]
        self.assertEqual(
            port_handlers,
            [
                0x181A, 0x181E, 0x1825, 0x182F, 0x1836, 0x183D,
                0x184D, 0x1851, 0x1855, 0x1856, 0x1857, 0x1862,
                0x186D, 0x1878, 0x1883, 0x1884, 0x1884, 0x18C8,
                0x18D1, 0x18EF, 0x18FA, 0x190C, 0x1913, 0x1916,
            ],
        )
        self.assertEqual(
            apu[0x1857:0x1883],
            bytes.fromhex(
                "e5 13 00 c4 21 8d 5d 3f a4 0f 6f "
                "e5 12 00 c4 22 e5 13 00 c4 23 6f "
                "e5 12 00 c4 24 e5 13 00 c4 25 6f "
                "e5 12 00 c4 26 e5 13 00 c4 27 6f"
            ),
        )
        self.assertEqual(apu[0x1883:0x1885], bytes.fromhex("6f 6f"))

    def test_reviewed_translation_ranges_are_structurally_classified(self):
        expected = {
            ("$001B2C", "$001B2F"): "code",
            ("$008685", "$00868A"): "data",
            ("$011843", "$011887"): "code",
            ("$011888", "$0118D3"): "code",
            ("$0176FD", "$017704"): "text",
            ("$022048", "$022079"): "text",
            ("$0221D8", "$0223DF"): "text",
            ("$0225C0", "$02262B"): "text",
            ("$023F16", "$024105"): "text",
            ("$040002", "$040003"): "pointer_table",
            ("$040018", "$040019"): "pointer_table",
            ("$040046", "$040047"): "pointer_table",
            ("$040064", "$04006F"): "text",
            ("$040070", "$040077"): "text",
            ("$040210", "$04022B"): "text",
            ("$047FB4", "$047FF1"): "padding",
            ("$0C1B2A", "$0C1E29"): "pointer_table",
            ("$0C416A", "$0C41A7"): "text",
            ("$0C41A8", "$0C41BD"): "text",
            ("$0C41BE", "$0C41C7"): "text",
            ("$1A0800", "$1A083F"): "text",
            ("$1A1D76", "$1A1DDB"): "text",
            ("$1A3006", "$1A3327"): "text",
            ("$1B3BC0", "$1B3C9F"): "padding",
            ("$1B6420", "$1B649F"): "padding",
            ("$1B64A0", "$1B6CDF"): "padding",
            ("$1B6DA0", "$1B6DDF"): "padding",
        }
        for bounds, region_type in expected.items():
            with self.subTest(bounds=bounds):
                region = self.regions[bounds]
                self.assertEqual(region["type"], region_type)
                self.assertEqual(region["confidence"], "confirmed")

    def test_observed_compressed_resources_are_classified_to_exact_extents(self):
        expected = {
            ("$1003E0", "$10079C"): (0x0800, 0x03BD),
            ("$108000", "$108B4C"): (0x1400, 0x0B4D),
            ("$110580", "$1117C9"): (0x1A00, 0x124A),
            ("$180000", "$1834D9"): (0x4000, 0x34DA),
            ("$1834DA", "$183CF0"): (0x1000, 0x0817),
            ("$1A8000", "$1A9B07"): (0x35A0, 0x1B08),
        }
        for bounds, (decoded_size, consumed) in expected.items():
            with self.subTest(bounds=bounds):
                region = self.regions[bounds]
                self.assertEqual(region["type"], "compressed_resource")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(bounds[0][1:], 16)
                resource = decompress_resource(self.rom, start)
                self.assertEqual(len(resource.data), decoded_size)
                self.assertEqual(resource.consumed, consumed)
                self.assertEqual(
                    int(bounds[1][1:], 16) - start + 1,
                    consumed,
                )

    def test_94_descriptor_tables_own_exact_codec_resource_extents(self):
        descriptor_ranges = [
            (0x0A0000, 44, 30),
            (0x0A00C0, 44, 37),
        ]
        for start, active_count, unique_count in descriptor_ranges:
            with self.subTest(start=start):
                entry_count = 64
                end = start + entry_count * 3 - 1
                region = self.regions[(f"${start:06X}", f"${end:06X}")]
                self.assertEqual(region["type"], "pointer_table")
                self.assertEqual(region["confidence"], "confirmed")
                records = [
                    self.rom[offset:offset + 3]
                    for offset in range(start, end + 1, 3)
                ]
                self.assertEqual(len(records), 64)
                self.assertEqual(sum(record != b"\0\0\0" for record in records), active_count)
                self.assertEqual(len(set(records) - {b"\0\0\0"}), unique_count)
                self.assertNotEqual(records[0x30], b"\0\0\0")
                self.assertNotEqual(records[0x31], b"\0\0\0")
                self.assertEqual(records[0x32:], [b"\0\0\0"] * 14)

        resources = {}
        for table_start, _, _ in descriptor_ranges:
            for index in range(64):
                entry = table_start + index * 3
                address = int.from_bytes(self.rom[entry:entry + 2], "little")
                bank = self.rom[entry + 2]
                if address == 0 and bank == 0:
                    continue
                self.assertGreaterEqual(bank, 0x80)
                self.assertGreaterEqual(address, 0x8000)
                start = (bank & 0x7F) * 0x8000 + (address & 0x7FFF)
                resource = decompress_resource(self.rom, start)
                resources[start] = resource

        self.assertEqual(len(resources), 67)
        self.assertEqual(sum(resource.consumed for resource in resources.values()), 109_553)
        for start, resource in resources.items():
            with self.subTest(start=start):
                end = start + resource.consumed - 1
                region = self.regions[(f"${start:06X}", f"${end:06X}")]
                self.assertEqual(region["type"], "compressed_resource")
                self.assertEqual(region["confidence"], "confirmed")

    def test_94_hard_coded_8c00_resource_has_exact_codec_extent(self):
        region = self.regions[("$0A0C00", "$0A0D12")]
        self.assertEqual(region["type"], "compressed_resource")
        self.assertEqual(region["confidence"], "confirmed")
        resource = decompress_resource(self.rom, 0x0A0C00)
        self.assertEqual(resource.consumed, 275)
        self.assertEqual(len(resource.data), 0x03C0)
        self.assertEqual(
            hashlib.sha256(resource.data).hexdigest(),
            "414a13a3310ffc839de15d929426d5ad505c20a43c5d5c173778ca1eb50ef413",
        )
        self.assertEqual(self.regions[("$0A0D13", "$0A0D13")]["type"], "padding")

        # Exact codec consumption excludes these one-byte inter-resource separators.
        for offset in (0x0A17A1, 0x0A3E8B, 0x0A56DB, 0x0B96DD):
            self.assertEqual(
                self.regions[(f"${offset:06X}", f"${offset:06X}")]["type"],
                "padding",
            )

    def test_81_loader_tables_own_exact_codec_resource_extents(self):
        tables = [
            (0x00D6C6, 0x00D855),
            (0x00D8BF, 0x00DA4E),
        ]
        resources = {}
        mismatches = []
        for table_start, table_end in tables:
            region = self.regions[(f"${table_start:06X}", f"${table_end:06X}")]
            self.assertEqual(region["type"], "pointer_table")
            self.assertEqual(region["confidence"], "confirmed")
            self.assertEqual(table_end - table_start + 1, 80 * 5)
            for index in range(80):
                entry = table_start + index * 5
                address = int.from_bytes(self.rom[entry:entry + 2], "little")
                bank = self.rom[entry + 2]
                transfer_size = int.from_bytes(self.rom[entry + 3:entry + 5], "little")
                if address == 0 and bank == 0 and transfer_size == 0:
                    continue
                self.assertGreaterEqual(bank, 0x80)
                self.assertGreaterEqual(address, 0x8000)
                start = (bank & 0x7F) * 0x8000 + (address & 0x7FFF)
                resource = decompress_resource(self.rom, start)
                resources[start] = resource
                if transfer_size != len(resource.data):
                    mismatches.append((table_start, index, transfer_size, len(resource.data)))

        self.assertEqual(len(resources), 105)
        self.assertEqual(
            mismatches,
            [
                (0x00D6C6, 0x13, 0x3F00, 0x3E00),
                (0x00D6C6, 0x4C, 0x16A0, 0x16B0),
            ],
        )
        for start, resource in resources.items():
            end = start + resource.consumed - 1
            region = self.regions[(f"${start:06X}", f"${end:06X}")]
            self.assertEqual(region["type"], "compressed_resource")
            self.assertEqual(region["confidence"], "confirmed")

    def test_81_popcount_and_resource_loader_routines_have_exact_boundaries(self):
        expected = [
            (
                "$00D315",
                "$00D356",
                "code",
                "5d3a03e4bd57471b1aa7732ca5f08bf865cee68eefa292395a6a7ce88cc161de",
            ),
            (
                "$00D357",
                "$00D398",
                "code",
                "9e779b56db2eb7b1fe3f77057cb33de59f542a46306a03b200397f6d7e7ad80a",
            ),
            (
                "$00D399",
                "$00D3DA",
                "code",
                "e67036ca42e9b387f769bd6800140038f56ff7e6e7b6b79f128dc9efbce894ae",
            ),
            (
                "$00D3DB",
                "$00D653",
                "code",
                "f5e05982f9e10a2b4480a4c9adce7341815b5213eb8c6494d931fcb6ec77c8a2",
            ),
            (
                "$00D654",
                "$00D689",
                "text",
                "5af2c76ac025598c254d4df6c5fb42d907fbd17e583da32ac5eeba60a1f33014",
            ),
            (
                "$00D68A",
                "$00D6C5",
                "code",
                "86d7eaa60618fa09381dd1da24bde194274a3be3f100ca953bf2ba1efed830c5",
            ),
        ]
        for start_text, end_text, region_type, digest in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], region_type)
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(hashlib.sha256(self.rom[start:end]).hexdigest(), digest)

        for start_text, end_text, return_opcode in (
            ("$00D315", "$00D356", 0x6B),
            ("$00D357", "$00D398", 0x6B),
            ("$00D399", "$00D3DA", 0x6B),
            ("$00D3DB", "$00D653", 0x60),
            ("$00D68A", "$00D6C5", 0x6B),
        ):
            end = int(end_text[1:], 16)
            self.assertEqual(self.rom[end], return_opcode)
        self.assertEqual(self.rom[0x00D688:0x00D68A], bytes(2))
        self.assertNotIn(bytes(2), self.rom[0x00D654:0x00D688])

    def test_81_configuration_workflow_has_exact_code_data_partitions(self):
        expected = [
            (
                "$009427",
                "$009919",
                "code",
                "74a4540649ba36688fc9e3fee57aac4eee0e5596752ff1f77a7347214f1b9ad5",
            ),
            (
                "$00991A",
                "$009923",
                "pointer_table",
                "3f4464a6fb163a099c3255525fef208771c0eac3d9dbd033c2f1b2924b2f4b2a",
            ),
            (
                "$009924",
                "$009C40",
                "code",
                "54420bc86b0d8197296c3895ce9eb586ea2232c2fc3490b73feb3b49eaa2eb94",
            ),
            (
                "$009C41",
                "$009C4D",
                "data",
                "c0abf9ed0254bd98ae81996825afb743a6ea4887afce9bc3bb226e20d5aff898",
            ),
            (
                "$009C4E",
                "$009C88",
                "code",
                "3b0ca1ba4bbfbdba7539c216d85059204e88df019af8c456aaf9e8be5e14a264",
            ),
            (
                "$009C89",
                "$009C92",
                "data",
                "4939f4f0c7fdd8f0fb725ff3b1c51c8126c0f2139603d7ca68891102f9290ca9",
            ),
            (
                "$00D2C1",
                "$00D314",
                "code",
                "540fa55cb238d50329260448354bbec3f01f5ebfb734508fb0be0969ea780773",
            ),
        ]
        for start_text, end_text, region_type, digest in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], region_type)
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(hashlib.sha256(self.rom[start:end]).hexdigest(), digest)

        self.assertEqual(
            [
                int.from_bytes(self.rom[offset:offset + 2], "little")
                for offset in range(0x00991A, 0x009924, 2)
            ],
            [0x9924, 0x9933, 0x9936, 0x9939, 0x993C],
        )
        self.assertEqual(
            [
                int.from_bytes(self.rom[offset:offset + 2], "little")
                for offset in range(0x009C89, 0x009C93, 2)
            ],
            [0x0068, 0x0078, 0x0088, 0x0098, 0x00A8],
        )
        self.assertEqual(self.rom[0x009C4D], 0)
        self.assertEqual(self.rom[0x009C88], 0x60)
        self.assertEqual(self.rom[0x00D314], 0x60)

    def test_80_reset_nmi_input_and_ppu_routines_have_exact_boundaries(self):
        expected = [
            ("$000012", "$0002A3", "f291c63bb4032efa9b1a0d77fa1fbce4a98f5944f69ed19f726e73f55190416f"),
            ("$0002A4", "$000627", "04443a1188850700c22bbdca0c222c92ba050d217a41c0bb7ba21b8a3007f99c"),
            ("$000628", "$00064F", "edeb310c0ec0d53d8ea58754a236952f349148a924a5137cd08cb86d4b209f63"),
            ("$00065E", "$00066B", "1e20bdaba497c39fd0af564b370f2c5b89cf3865355eaaf15d85afae181d019a"),
            ("$00066C", "$000679", "36ead01c253bffad185fd3b693028d73aa7a039485356e814988454702fe12c6"),
            ("$00067A", "$0006C1", "a91f28b5691eba0e5c24f8675154bb808d6c13f5afe017ad053a99acfc97184c"),
            ("$0006C2", "$0006E4", "8eb6777f31c379346030020323e01da9f0f9da71453b233ef173e6d045a8280c"),
            ("$0006E5", "$0006F5", "19bd371d522322bdbe6f345fe97032ca7cb51ffe7137fd75c57dbc6de18fa1ac"),
            ("$000721", "$00074B", "e038edfea924b61d81876d1c39a84694afa707ea680213e77b2be2d40cbcf5a4"),
            ("$00074C", "$000759", "fcf1c0d53a0162e08e8c48f51c16fe4130711b1a44fc49109b56ce80f916abce"),
            ("$00075A", "$000767", "9704487145aef75a06d852df84ca83943e5c4dc07fac6523a08dc42b7aadbe67"),
            ("$000768", "$000895", "5477e9cdf19a58a8a5a966d81aa6c18eae6f924ec84c2b93ac843a90fefafb9f"),
            ("$000896", "$0008D6", "2d6eaac84e875ce2eee88bae92587a17db8e6a7a8d9351a0bcf2ec44127fa275"),
            ("$0008D7", "$0008E7", "a00e1cc74fa8ed2a7294334908a981cbd71aefb2a9d4dcce9bb5dd24b9570ac5"),
            ("$000906", "$00091F", "259299b99f11087ea06e0355762c876b30f56989c7b8a0091e55fc7a10a31334"),
            ("$000920", "$000946", "6bd8b9d774f32613f654dd33c6c66ce99ff77f51dc3df9f7eb11ea32b21a1026"),
            ("$000947", "$00095A", "b7c4143dfa53a990471d3e83aab3881b55c87ff4d324f3824ccefc6f119099e7"),
            ("$00095B", "$00097B", "5c17b603411e525c74fb9af717f52f9eb4804ac735d9d37e49d8beb57a240975"),
        ]
        for start_text, end_text, digest in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "code")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(hashlib.sha256(self.rom[start:end]).hexdigest(), digest)

        self.assertEqual(int.from_bytes(self.rom[0x007FEA:0x007FEC], "little"), 0x82A4)
        self.assertEqual(int.from_bytes(self.rom[0x007FFA:0x007FFC], "little"), 0x82A4)
        for end in (
            0x0002A3,
            0x00064F,
            0x00066B,
            0x000679,
            0x0006C1,
            0x0006E4,
            0x0006F5,
            0x00074B,
            0x000759,
            0x000767,
            0x0008D6,
            0x0008E7,
            0x00091F,
            0x000946,
            0x00095A,
            0x00097B,
        ):
            self.assertEqual(self.rom[end], 0x6B)
        self.assertEqual(self.rom[0x000627], 0x60)
        self.assertEqual(self.rom[0x000895], 0x60)

        for start, end, region_type in ((0x000650, 0x00065D, "data"), (0x0006F6, 0x000720, "code"), (0x0008E8, 0x000905, "code")):
            with self.subTest(start=start):
                self.assertEqual(self.regions[(f"${start:06X}", f"${end:06X}")]["type"], region_type)

    def test_80_arithmetic_rendering_and_palette_source_regions_are_exact(self):
        expected = [
            ("$000A31", "$000B45", "code", "3cc1e434a670c923c40926cb486cf8fa3fde6322d74462ce39422ae9b13e276d"),
            ("$000B46", "$000B66", "code", "6499a494dd8448b3438af116beb2ea0baf94ce8c414c01ba11d7e485b8c37a71"),
            ("$000B67", "$000B81", "code", "5b95196549360aee5128c7df588f7f3e1f812842ca9ccc1b5a11c3f245ff9ace"),
            ("$000C37", "$000C75", "code", "85ac6269d2ee31eea9d013299cfb4d61f131caaa8fff8513125c7092171cb64c"),
            ("$000C76", "$000CAF", "code", "b0955f7a3eb905f16cd111906abe4e8c01ba4f34817dcdfdc4821ff65751f51c"),
            ("$000CB0", "$000CBD", "data", "d7469bfc03c37dc5672d6b89df074463c03b46864c087513cd51996b49527edc"),
            ("$000CBE", "$000CF5", "code", "0986b7999053544ec3859d5c5463bb87894f24667b564e4a96a20612435aa1ee"),
            ("$000CF6", "$000D03", "data", "43a27c8ba66948928e23174bda02ece2d2bc1e6be2995c8f17d5a8c6b51a150d"),
            ("$000EDE", "$000F0E", "code", "407b7e68907df31d0fdc5613382bd4551163319a2add9f8be322fb6557e1a6ab"),
            ("$000F0F", "$000F44", "code", "39bfd1e008aa7f0f8984d0c40e8749f920167e66a457b98db3b45a9709446665"),
            ("$000F45", "$000F90", "code", "b050ee9834333b76c12d91e1977fee95196925f918016480fa9430996a0ba7fd"),
            ("$000F91", "$001033", "code", "f0a8bd40d821a30178c087c134a6bf47ad203d43bc490aa196d6bb3b9f864538"),
            ("$001034", "$0010B0", "code", "e858be0b8c0b815384c15616a6d7f6aeae26ef44e322f9ef02ac47f0ba16e252"),
            ("$0010DB", "$001136", "code", "eecffd39466c8e5ee21be46a5fb68a443a270a7f58ea9348ab799ba775dd0797"),
            ("$001137", "$001156", "data", "f14be69aafcb84cab13d238c0c3d1d824d50c75e152eb6d1250b2f0ca3574a7b"),
            ("$001157", "$00116F", "code", "d6efda45a11cb5a0351628b1925753978844aa87a5c238346bd03a9f4b5934ec"),
            ("$001170", "$00118E", "code", "24f9598e4d3f5e8884a4bffbcc4c12fc8a61d4890d6ffbeab50cc47f0b7e9b72"),
            ("$0012A1", "$001352", "code", "a52e3506119882829f2f2c5d8886ae7a7f88dffa6201171105090607874c256f"),
            ("$001353", "$001554", "data", "34582995af7f8f379f975d214118ed7eb9016427f6b34231b00856cc154b1b08"),
            ("$001555", "$001569", "code", "3e325edfe96f99fcc29fc343dc6810f52c7754edc355ce9f6631451c8dbe7124"),
            ("$00156A", "$00159F", "code", "b3ddc1cb9ae55c70e64625ce0f500a80fb79124a296f629fce235074efa37ad1"),
            ("$0015A0", "$0015FA", "code", "71419de01b01723e7a7a84ebd7740c341fa66733b855a0e818de07c7183bd1c2"),
            ("$0015FB", "$0017C4", "code", "0cdd021937dc67446a00db90efa7fc0022ba5b5221e569fbe18b80394d80cd4c"),
            ("$0017C5", "$0017DE", "code", "310d309ede8ef201e19d72e9896c2fa6ecbf0efcf4799e974a5ba840beff5ed7"),
            ("$0017DF", "$0017F8", "code", "89e6b434803a69ae90dd492384bc2ebf88d868d2b673499e72f43dce03481ac4"),
            ("$001839", "$0018B1", "code", "0ea8c576e21fd07ceaf430e1f7af4d230229b7c60cc2e4919f04dda14349c324"),
            ("$0018E3", "$00197A", "code", "1f0a0fe4803a4c55ffe8e73dfa5c00c1f4258a81f4e84888948ee368e85cc1f1"),
            ("$00197B", "$001CF9", "code", "67edfc5b9a95a50771cef252fb77f1d9bae47d5f52f71008861e80e5c4be4a70"),
            ("$001CFA", "$001DA6", "code", "7fa075a8c04ae08df7eba90df74e0a323812b0780241ca26d3a65c4e5d86659c"),
            ("$1B0020", "$1B005F", "graphics", "952e6f2cb26c0951505e583afba1853bdf27573ea36039c7528d6aed3c5e7697"),
            ("$1B0060", "$1B009F", "graphics", "de47aa44e0866dec65a291f45676f74dfca2ea9f32c94818dc033738c23d430d"),
        ]
        for start_text, end_text, region_type, digest in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], region_type)
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(hashlib.sha256(self.rom[start:end]).hexdigest(), digest)

        self.assertEqual(
            [int.from_bytes(self.rom[offset:offset + 2], "little") for offset in range(0x000CB0, 0x000CBE, 2)],
            [0x0000, 0x0001, 0x0202, 0x4444, 0xAAAA, 0xDDDD, 0xFFFF],
        )
        self.assertEqual(
            [int.from_bytes(self.rom[offset:offset + 2], "little") for offset in range(0x000CF6, 0x000D04, 2)],
            [0xFFFF, 0xDDDD, 0xAAAA, 0x4444, 0x0202, 0x0001, 0x0000],
        )
        self.assertEqual(
            [int.from_bytes(self.rom[offset:offset + 2], "little") for offset in range(0x001137, 0x001157, 2)],
            [0x0260, 0x0261, 0x0262, 0x0263, 0x0264, 0x0265, 0x0266, 0x0267,
             0x0270, 0x0271, 0x0280, 0x0281, 0x0282, 0x0283, 0x0284, 0x0285],
        )

        thresholds = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x001353, 0x001555, 2)
        ]
        self.assertEqual(len(thresholds), 257)
        self.assertTrue(all(left <= right for left, right in zip(thresholds, thresholds[1:])))
        self.assertEqual(thresholds[0], 0)
        self.assertEqual(thresholds[-1], 0xFFFF)

        self.assertEqual(self.rom[0x0017C5:0x0017C9], bytes.fromhex("08 C2 10 A2"))
        self.assertEqual(self.rom[0x0017C9:0x0017CB], bytes.fromhex("20 80"))
        self.assertEqual(self.rom[0x0017DF:0x0017E3], bytes.fromhex("08 C2 10 A2"))
        self.assertEqual(self.rom[0x0017E3:0x0017E5], bytes.fromhex("60 80"))

        for start, end, region_type in (
            (0x000B82, 0x000C36, "code"),
            (0x000D04, 0x000EDD, "code"),
            (0x0010B1, 0x0010DA, "code"),
            (0x00118F, 0x0012A0, "data"),
            (0x0017F9, 0x001838, "code"),
            (0x0018B2, 0x0018E2, "code"),
            (0x1B0014, 0x1B001F, "data"),
        ):
            with self.subTest(start=start):
                self.assertEqual(self.regions[(f"${start:06X}", f"${end:06X}")]["type"], region_type)

    def test_80_diagnostic_workflow_regions_are_exact(self):
        expected = [
            ("$001DA7", "$001E2E", "code", "9428acb8d00b3e736717268c23ed6f0af34d12b0e714fd6419206357dea67df8"),
            ("$001F2B", "$001FEC", "code", "443cc55e5d8b5440e24b7d1f44073774a963c81fde87aed8ad6c2867840edb55"),
            ("$001FED", "$001FF4", "pointer_table", "4a77767d1957e99250f12fd14918df16fa0570d7981a06849b244e258996f68f"),
            ("$001FF5", "$0020AF", "code", "31f12568d0ad59b668cff618a2bd5bf6014c84429f343a23334bdc67109ca6a2"),
            ("$0020B0", "$0020D5", "pointer_table", "e4eb201d97a252144eefb0cf9be73441c155cd2c2d813d85c7150075de4a3937"),
            ("$0020D6", "$0021B9", "text", "5ea375cd145418cb9fbf066b0b62047c66f50ecf43afd7c2cf2c78bab7cb9e4b"),
            ("$0021BA", "$002229", "code", "f4d3ae18d524759c44148be0c6bd7c964b111faefd4dddc462aee314886906c3"),
            ("$00222A", "$002312", "code", "0d29ef68396c7d565ed2f9aee19022cbf640234fad7adb827b2ac565a7047faa"),
            ("$002313", "$00235E", "text", "e1f7207f985d0e9dad841975f9f61603f47ecb1195aa8420bb2ae6ee207ed8b0"),
            ("$00235F", "$00259E", "graphics", "e5f5130a0015934239366c50a4027304e56120d48f979ccfa14431714572d2ee"),
            ("$00259F", "$0025BE", "graphics", "9741d97025f58495f3c3260ea02fc35beafb913e3fcbf99bbde42fe28c6d8b2e"),
            ("$0025BF", "$0025DA", "data", "937f6a21663140ee4cb2b7ea1bafe86cb120df1ef758f976886ace9dba1f706c"),
            ("$007F80", "$007F8F", "data", "be8c0c4188bbf50911f72e472784cd218aaf806217ad92c8e9970ef79392b401"),
            ("$002BEA", "$002C23", "code", "eb73375cbce8a71d30c4105bd940ac940ad412a9745fb95518c92ac3084eddf6"),
            ("$002F73", "$002FDF", "code", "a005bb71c63ff0d27617a29ab20fc9638a746a0167a94c97d2ccfab377a62f64"),
            ("$003548", "$003681", "code", "f184a0e8b834baf4894baf3d910178136d5ace5eaf8db4a931314e8f1fe01e7e"),
            ("$003682", "$00368F", "pointer_table", "0df155d9916d2944b5f9e85d2e513f93394c461fb9219c1a18bcbe7875b4f88c"),
            ("$003690", "$0036E6", "code", "4cf0d74f1bd01c716366e271ad6b336e6de3cdc2c24bda77e337e7b6976a92d7"),
            ("$0036E7", "$003722", "code", "d040ecfcab85aea36782edd4406126488c545aadb334aa895f18008d7e6a8efc"),
            ("$003723", "$0037D8", "code", "2978c450dfe77e9c77888167ec05b49ed2bd786e5bd721a841d4ff42bad5b69b"),
            ("$0037D9", "$003AFF", "code", "f5ce457c2a3ffb09572386b14e2f2c89ec33e57570b423864339ecd52326d80d"),
            ("$003B00", "$003CA1", "code", "b3ea92951aa667357801117f597f4deaaed25de896bc5f82a576b527d9d0a17a"),
            ("$003CA2", "$003DEA", "code", "3a6d97e301b66142cb9d7b1a1752526d089fddb14d7a2b5508308a960402caf1"),
            ("$0041B1", "$0042D2", "code", "963d32379fad157872d339ad0e5562323d1ad3770837e8f94ddd669b76c43d70"),
            ("$0042D3", "$004538", "code", "92be2e32b49408af0250760725e534815c01ea073981ac7ec58279b2cd99addd"),
            ("$004539", "$004638", "pointer_table", "ede89a109821415445453c4ef511c0d2f719c4d32606966c66ed6d1d56acf448"),
            ("$00496B", "$004A50", "text", "43437b4e68bfd68aa0d82268189c5adbb9763adec7d19fe5607618938cbe7fb8"),
            ("$004A51", "$004A72", "text", "d5e9864b0dac749c81b6aa1dd2edcbf7925942acf7c94d313f66c506dd27c7f9"),
            ("$004A73", "$004A7C", "pointer_table", "811709f11bcef4c5718327ee45f40c790f71475989c44c411207127ce635d924"),
            ("$004A7D", "$004A82", "text", "fdd6fc9f69a5666c8e957f2dd7245e436b2fe7247a9e43f860fd3bd8efc16c02"),
            ("$004A85", "$004A8A", "text", "e73c76225c106f896a01024dedffe76bacf631c1ea014d389dbf2e799ca036e0"),
            ("$004A8D", "$004A92", "text", "8d7c3e9c91ea5df931bd6f81af51ff4800cd052fa79aaa1c2beca74a37944db8"),
            ("$004A95", "$004A9A", "text", "b9c6edeaf4dca2e05dcdc7865318d9aaaad9d3d987837e1a0aae42582dbcc424"),
            ("$004A9D", "$004AA2", "text", "a15a26db89e1107be819a295b4ad7bb9401d04d004c19cf8c42d2f79f71b3913"),
            ("$004AFB", "$004B89", "code", "910706fe73df3d273f866b714669ef9e29835a663efc1a989eb1591481619c33"),
            ("$004EFA", "$004FBC", "code", "5b3b4c31fa32d69ed5fcd730776b1e6081b6204f45b7059de3770b39122c801a"),
            ("$0058AC", "$00596D", "code", "18b28393bf7f866bb5625bd32d30d2ab44c9cf908adf49fe1799948315272a2e"),
            ("$00596E", "$00598B", "code", "5ac0c9d564f36e7066f1a2b4d42ef153fb9ff2287d6435ce0c8ffb2fccb79b21"),
            ("$00598C", "$0059DF", "code", "a0110253bdba56f937d741156756c7e12e50d76df7d0bd67912c7edec919ea59"),
            ("$005A80", "$005A99", "code", "88b4cbe8ee56449ba2141ddbaf2b186e4bc5d3398467ee5dbba717854c504295"),
        ]
        for start_text, end_text, region_type, digest in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], region_type)
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(hashlib.sha256(self.rom[start:end]).hexdigest(), digest)

        self.assertEqual(
            [int.from_bytes(self.rom[offset:offset + 2], "little") for offset in range(0x001FED, 0x001FF5, 2)],
            [0x9FFF, 0xA009, 0xA00C, 0x9FF5],
        )
        menu_pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x0020B0, 0x0020D6, 2)
        ]
        self.assertEqual(menu_pointers, list(range(0xA0D6, 0xA1BA, 0x000C)))
        for pointer in menu_pointers:
            start = pointer - 0x8000
            self.assertEqual(self.rom[start + 10:start + 12], b"\x00\x00")

        self.assertEqual(
            [
                (
                    int.from_bytes(self.rom[offset:offset + 2], "little"),
                    int.from_bytes(self.rom[offset + 2:offset + 4], "little"),
                )
                for offset in range(0x0025BF, 0x0025DB, 4)
            ],
            [(0x0010, value) for value in range(0x001A, 0x007B, 0x0010)],
        )
        self.assertEqual(self.rom[0x007F80:0x007F90], b"95/08/0306:38:02")
        self.assertEqual(
            [int.from_bytes(self.rom[offset:offset + 2], "little") for offset in range(0x003682, 0x003690, 2)],
            [0xB690, 0xB6E7, 0xB723, 0xB7D9, 0xBB00, 0xBCA2, 0xC1B1],
        )
        self.assertEqual(
            [int.from_bytes(self.rom[offset:offset + 2], "little") for offset in range(0x004A73, 0x004A7D, 2)],
            [0xCA9D, 0xCA95, 0xCA85, 0xCA8D, 0xCA7D],
        )
        for offset in (0x004A83, 0x004A8B, 0x004A93, 0x004A9B):
            self.assertEqual(self.rom[offset:offset + 2], b"\x00\x00")
            self.assertEqual(
                self.regions[(f"${offset:06X}", f"${offset + 1:06X}")]["type"],
                "padding",
            )
        self.assertEqual(self.rom[0x004AA3:0x004AA5], b"\x00\x00")
        self.assertEqual(self.regions[("$004AA3", "$004AFA")]["type"], "data")
        c539_pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x004539, 0x004639, 2)
        ]
        self.assertEqual(len(c539_pointers), 128)
        self.assertEqual(len(set(c539_pointers)), 10)
        self.assertEqual(min(c539_pointers), 0xC639)
        self.assertEqual(max(c539_pointers), 0xC679)
        self.assertEqual(c539_pointers.count(0xC679), 63)
        self.assertEqual(self.regions[("$004639", "$00496A")]["type"], "data")
        self.assertEqual(self.regions[("$0059E0", "$005A7B")]["type"], "code")
        self.assertEqual(self.regions[("$005A7C", "$005A7F")]["type"], "pointer_table")

        # Fixed MVN source operands and lengths in $80:A2D2.
        self.assertIn(bytes.fromhex("A2 5F A3 A0 00 80 C2 20 A9 3F 02 8B 54 7E 80"), self.rom[0x0022D2:0x002313])
        self.assertIn(bytes.fromhex("A2 9F A5 A0 00 05 A9 1F 00 8B 54 80 80"), self.rom[0x0022D2:0x002313])

        self.assertEqual(self.regions[("$001E2F", "$001F2A")]["type"], "code")
        self.assertEqual(self.regions[("$0025DB", "$0025E3")]["type"], "pointer_table")

    def test_8a_ff42_tail_reference_is_inside_a_confirmed_compressed_resource(self):
        tail = self.regions[("$057F42", "$057FFF")]
        self.assertEqual(tail["type"], "fill")
        self.assertEqual(tail["confidence"], "confirmed")
        self.assertEqual(set(self.rom[0x057F42:0x058000]), {0xFF})

        far_pointer = bytes.fromhex("42 FF 8A")
        self.assertEqual(self.rom.count(far_pointer), 1)
        occurrence = self.rom.index(far_pointer)
        resource = self.regions[("$038000", "$03B6EB")]
        self.assertEqual(resource["type"], "compressed_resource")
        self.assertLessEqual(int(resource["rom_start"][1:], 16), occurrence)
        self.assertGreaterEqual(int(resource["rom_end"][1:], 16), occurrence + 2)

    def test_portrait_descriptor_hierarchy_owns_exact_codec_resources(self):
        roots = self.regions[("$01EE97", "$01EF96")]
        self.assertEqual(roots["type"], "pointer_table")
        self.assertEqual(roots["confidence"], "confirmed")

        descriptors = self.regions[("$01EF97", "$01F392")]
        self.assertEqual(descriptors["type"], "pointer_table")
        self.assertEqual(descriptors["confidence"], "confirmed")

        pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x01EE97, 0x01EF97, 2)
        ]
        self.assertEqual(len(pointers), 128)
        unique_pointers = sorted(set(pointers))
        self.assertEqual(len(unique_pointers), 125)
        self.assertEqual(unique_pointers[0], 0xEF97)
        self.assertEqual(unique_pointers[-1], 0xF390)

        record_count = 0
        resources = {}
        output_sizes = set()
        for index, address in enumerate(unique_pointers):
            next_address = (
                unique_pointers[index + 1]
                if index + 1 < len(unique_pointers)
                else 0xF393
            )
            self.assertEqual((next_address - address) % 3, 0)
            for entry in range(
                0x018000 + (address & 0x7FFF),
                0x018000 + (next_address & 0x7FFF),
                3,
            ):
                source_address = int.from_bytes(self.rom[entry:entry + 2], "little")
                source_bank = self.rom[entry + 2]
                self.assertGreaterEqual(source_bank, 0x80)
                self.assertGreaterEqual(source_address, 0x8000)
                start = (source_bank & 0x7F) * 0x8000 + (source_address & 0x7FFF)
                resource = decompress_resource(self.rom, start)
                resources[start] = resource
                output_sizes.add(len(resource.data))
                record_count += 1

        self.assertEqual(record_count, 340)
        self.assertEqual(len(resources), 219)
        self.assertEqual(sum(resource.consumed for resource in resources.values()), 168_414)
        self.assertEqual(min(output_sizes), 0x00A0)
        self.assertEqual(max(output_sizes), 0x0400)
        for start, resource in resources.items():
            end = start + resource.consumed - 1
            region = self.regions[(f"${start:06X}", f"${end:06X}")]
            self.assertEqual(region["type"], "compressed_resource")
            self.assertEqual(region["confidence"], "confirmed")

    def test_8c_ff08_tail_references_are_inside_confirmed_compressed_resources(self):
        tail = self.regions[("$067F08", "$067FFF")]
        self.assertEqual(tail["type"], "fill")
        self.assertEqual(tail["confidence"], "confirmed")
        self.assertEqual(set(self.rom[0x067F08:0x068000]), {0xFF})

        far_pointer = bytes.fromhex("08 FF 8C")
        occurrences = [
            offset
            for offset in range(len(self.rom))
            if self.rom.startswith(far_pointer, offset)
        ]
        self.assertEqual(occurrences, [0x06C1F9, 0x18B390])
        owners = [
            ("$06BFEA", "$06C35F"),
            ("$18AC9E", "$18B7B1"),
        ]
        for occurrence, bounds in zip(occurrences, owners):
            region = self.regions[bounds]
            self.assertEqual(region["type"], "compressed_resource")
            self.assertLessEqual(int(bounds[0][1:], 16), occurrence)
            self.assertGreaterEqual(int(bounds[1][1:], 16), occurrence + 2)

    def test_portrait_companion_tables_and_palette_corpus_are_classified(self):
        palette_pointers = self.regions[("$050000", "$0500FF")]
        self.assertEqual(palette_pointers["type"], "pointer_table")
        self.assertEqual(palette_pointers["confidence"], "confirmed")

        pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x050000, 0x050100, 2)
        ]
        self.assertEqual(len(pointers), 128)
        unique_pointers = sorted(set(pointers))
        self.assertEqual(len(unique_pointers), 102)
        self.assertEqual(unique_pointers, list(range(0x8100, 0x8DC0, 0x20)))

        palettes = self.regions[("$050100", "$050DBF")]
        self.assertEqual(palettes["type"], "graphics")
        self.assertEqual(palettes["confidence"], "confirmed")
        self.assertEqual(0x050DC0 - 0x050100, 102 * 0x20)
        for address in unique_pointers:
            start = 0x050000 + (address & 0x7FFF)
            self.assertEqual(len(self.rom[start:start + 0x20]), 0x20)

        frame_ids = self.regions[("$01E500", "$01E5FF")]
        self.assertEqual(frame_ids["type"], "data")
        self.assertEqual(frame_ids["confidence"], "confirmed")
        self.assertEqual(0x100, 128 * 2)

        presentation_code = self.regions[("$01E600", "$01E8FF")]
        self.assertEqual(presentation_code["type"], "code")
        self.assertEqual(presentation_code["confidence"], "confirmed")
        self.assertEqual(self.rom[0x01E600:0x01E604], bytes.fromhex("c2 20 a6 0f"))
        self.assertEqual(self.rom[0x01E819:0x01E81D], bytes.fromhex("c2 20 a5 11"))
        self.assertEqual(self.rom[0x01E7E0], 0x6B)
        self.assertEqual(self.rom[0x01E818], 0x6B)
        self.assertEqual(self.rom[0x01E8FF], 0x6B)
        self.assertEqual(
            [
                offset
                for offset in range(len(self.rom) - 3)
                if self.rom[offset:offset + 4] == bytes.fromhex("22 00 e6 83")
            ],
            [0x01BF87, 0x01BFEA],
        )
        self.assertEqual(
            [
                offset
                for offset in range(len(self.rom) - 3)
                if self.rom[offset:offset + 4] == bytes.fromhex("22 19 e8 83")
            ],
            [0x01BF25],
        )
        self.assertEqual(
            hashlib.sha256(self.rom[0x01E600:0x01E900]).hexdigest(),
            "2beb935fbbd986875341201690555a25a378800ded348407f4bf1504386b076b",
        )

        placements = self.regions[("$01E900", "$01E917")]
        self.assertEqual(placements["type"], "data")
        self.assertEqual(placements["confidence"], "confirmed")
        self.assertEqual(0x18, 6 * 4)

        setup_code = self.regions[("$01E918", "$01E963")]
        self.assertEqual(setup_code["type"], "code")
        self.assertEqual(setup_code["confidence"], "confirmed")
        self.assertEqual(self.rom[0x01E918:0x01E91C], bytes.fromhex("08 c2 20 a9"))
        self.assertEqual(self.rom[0x01E963], 0x6B)
        self.assertEqual(
            [
                offset
                for offset in range(len(self.rom) - 3)
                if self.rom[offset:offset + 4] == bytes.fromhex("22 18 e9 83")
            ],
            [0x004EA0],
        )
        self.assertEqual(
            hashlib.sha256(self.rom[0x01E918:0x01E964]).hexdigest(),
            "124cb8bead6e754c3d4b68e02094e93fbddeddd154a74cb0597f4b575c9134f7",
        )
        self.assertNotIn(("$01E964", "$01EA40"), self.regions)

    def test_scenario_root_owned_ranges_form_the_classified_partition(self):
        expected = {
            ("$088000", "$08FFFF"): (0x91, 144, 0x8000),
            ("$090000", "$097DF7"): (0x92, 146, 0x7DF8),
            ("$098000", "$09C224"): (0x93, 65, 0x4225),
        }
        roots = decode_scenario_roots(self.rom)
        self.assertEqual(restore_candidate_ranges(self.rom, roots), self.rom)
        for bounds, (cpu_bank, root_count, size) in expected.items():
            with self.subTest(bounds=bounds):
                region = self.regions[bounds]
                self.assertEqual(region["type"], "scenario_data")
                self.assertEqual(
                    region["confidence"],
                    "confirmed_structure_partial_schema",
                )
                bank_roots = [root for root in roots if root.bank == cpu_bank]
                self.assertEqual(len(bank_roots), root_count)
                start = int(bounds[0][1:], 16)
                end = int(bounds[1][1:], 16) + 1
                self.assertEqual(end - start, size)
                cursor = start
                for root in bank_roots:
                    self.assertEqual(root.offset, cursor)
                    cursor = min(root.end_offset, end)
                    if cursor == end:
                        break
                self.assertEqual(cursor, end)

    def test_large_physical_bank_tails_are_recorded_as_fill_not_free_space(self):
        expected = [
            ("$00DD14", "$00FFFF", 0x81, 0xDD14),
            ("$027476", "$027FFF", 0x84, 0xF476),
            ("$047FF2", "$047FFF", 0x88, 0xFFF2),
            ("$05FFE0", "$05FFFF", 0x8B, 0xFFE0),
            ("$06FF94", "$06FFFF", 0x8D, 0xFF94),
            ("$077F8A", "$077FFF", 0x8E, 0xFF8A),
            ("$07FFFA", "$07FFFF", 0x8F, 0xFFFA),
            ("$04C801", "$04FFFF", 0x89, 0xC801),
            ("$084329", "$087FFF", 0x90, 0xC329),
            ("$0A6416", "$0A7FFF", 0x94, 0xE416),
            ("$0BE1CC", "$0BFFFF", 0x97, 0xE1CC),
            ("$103685", "$107FFF", 0xA0, 0xB685),
            ("$11638C", "$117FFF", 0xA2, 0xE38C),
            ("$125840", "$127FFF", 0xA4, 0xD840),
            ("$15DBA8", "$15FFFF", 0xAB, 0xDBA8),
            ("$16B68A", "$16FFFF", 0xAD, 0xB68A),
            ("$17230C", "$177FFF", 0xAE, 0xA30C),
            ("$17BBF6", "$17FFFF", 0xAF, 0xBBF6),
            ("$19DD04", "$19FFFF", 0xB3, 0xDD04),
            ("$1AD22D", "$1AFFFF", 0xB5, 0xD22D),
            ("$1DDEA4", "$1DFFFF", 0xBB, 0xDEA4),
            ("$1EE18B", "$1EFFFF", 0xBD, 0xE18B),
            ("$1F58EA", "$1F7FFF", 0xBE, 0xD8EA),
        ]
        incidental_pointer_bytes = {
            (0x88, 0xFFF2): [0x1F0953],
            (0xAF, 0xBBF6): [0x038DBD, 0x03B252],
        }
        for start_text, end_text, cpu_bank, cpu_start in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "fill")
                self.assertEqual(region["confidence"], "strong_inference")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(end % 0x8000, 0)
                self.assertEqual(set(self.rom[start:end]), {0xFF})
                far_pointer = cpu_start.to_bytes(2, "little") + bytes([cpu_bank])
                occurrences = []
                cursor = 0
                while True:
                    cursor = self.rom.find(far_pointer, cursor)
                    if cursor < 0:
                        break
                    occurrences.append(cursor)
                    cursor += 1
                self.assertEqual(
                    occurrences,
                    incidental_pointer_bytes.get((cpu_bank, cpu_start), []),
                )
                if start == 0x077F8A:
                    self.assertEqual(
                        hashlib.sha256(self.rom[start:end]).hexdigest(),
                        "f006bf56fa691e62cae4a7b60be45a367ae52de2725d74ee677faceb55204595",
                    )
                if start == 0x07FFFA:
                    self.assertEqual(
                        hashlib.sha256(self.rom[start:end]).hexdigest(),
                        "ce8bee525d6736e9825261b19a9b51719f9dc4bb728e95cf7067a2142b03b362",
                    )
                if start == 0x00DD14:
                    self.assertEqual(
                        hashlib.sha256(self.rom[start:end]).hexdigest(),
                        "463facc7506af7a8434f700c81def7b9705f9b32d5aab8f7176179810fb06705",
                    )
                if start == 0x027476:
                    self.assertEqual(
                        hashlib.sha256(self.rom[start:end]).hexdigest(),
                        "d8a27c6db64c96bfaa24c4434dcbdbd357df323f6babd3c6ef664e094d567cd0",
                    )

    def test_unused_bank_b6_renderer_source_area_is_structurally_classified(self):
        graphics = self.regions[("$1B63C0", "$1B641F")]
        self.assertEqual(graphics["type"], "graphics")
        self.assertEqual(graphics["confidence"], "strong_inference")
        self.assertNotEqual(set(self.rom[0x1B63C0:0x1B6420]), {0})

        fill = self.regions[("$1B6420", "$1B7C9F")]
        self.assertEqual(fill["type"], "fill")
        self.assertEqual(fill["confidence"], "strong_inference")
        self.assertEqual(set(self.rom[0x1B6420:0x1B7CA0]), {0})

    def test_complete_battle_text_pointer_table_and_corpus_are_classified(self):
        pointer_region = self.regions[("$1A0000", "$1A0703")]
        self.assertEqual(pointer_region["type"], "pointer_table")
        self.assertEqual(pointer_region["confidence"], "confirmed")

        text_region = self.regions[("$1A0800", "$1A7525")]
        self.assertEqual(text_region["type"], "text")
        self.assertEqual(text_region["confidence"], "confirmed")

        targets = []
        for index in range(898):
            pointer_offset = 0x1A0000 + index * 2
            address = int.from_bytes(self.rom[pointer_offset:pointer_offset + 2], "little")
            self.assertGreaterEqual(address, 0x8800)
            self.assertLessEqual(address, 0xF4FC)
            targets.append(address)
        self.assertEqual(len(set(targets)), 729)

        cursor = 0x1A0800
        for address in sorted(set(targets)):
            start = 0x1A0000 + (address & 0x7FFF)
            self.assertEqual(start, cursor)
            while True:
                word = int.from_bytes(self.rom[cursor:cursor + 2], "little")
                cursor += 2
                if word == 0x0000:
                    break
                self.assertTrue(word == 0x000A or word >= 0x0100)
        self.assertEqual(cursor, 0x1A7526)
        self.assertEqual(
            int.from_bytes(self.rom[0x1A0704:0x1A0706], "little"),
            0xF526,
        )

    def test_battle_script_tables_and_blocks_partition_the_confirmed_b5_range(self):
        expected = [
            ("$1ABA7E", "$1ABB1D", "pointer_table", 0xBB1E, 0xC5AC),
            ("$1ABB1E", "$1AC5AB", "battle_script_data", None, None),
            ("$1AC5AC", "$1AC64B", "pointer_table", 0xC64C, 0xCC74),
            ("$1AC64C", "$1ACC73", "battle_script_data", None, None),
            ("$1ACC74", "$1ACD13", "pointer_table", 0xCD14, 0xD22D),
            ("$1ACD14", "$1AD22C", "battle_script_data", None, None),
        ]
        cursor = 0x1ABA7E
        for start_text, end_text, region_type, target_start, target_end in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], region_type)
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(start, cursor)
                cursor = end
                if region_type == "pointer_table":
                    self.assertEqual(end - start, 0xA0)
                    pointers = [
                        int.from_bytes(self.rom[offset:offset + 2], "little")
                        for offset in range(start, end, 2)
                    ]
                    self.assertEqual(len(pointers), 80)
                    self.assertTrue(
                        all(target_start <= pointer <= target_end for pointer in pointers)
                    )
                else:
                    self.assertEqual(
                        region["confidence"],
                        "confirmed_structure_partial_schema",
                    )
        self.assertEqual(cursor, 0x1AD22D)

    def test_bank_81_entry_and_resource_loader_code_has_exact_boundaries(self):
        expected = [
            (
                "$008000",
                "$008684",
                "3680ca402957668faa2cb9b403c90346d796484b3c14eae19b17ebc037ed01df",
                0x60,
            ),
            (
                "$00868B",
                "$008AD6",
                "0551f86cf505df54693839f71c2e982f0a22b996fb043bd09fad37da28496fc0",
                0x89,
            ),
            (
                "$008ADB",
                "$008B5D",
                "759afd1288dfb97f490b815cbd7ad61e07d804c73e7e6f98acf0817a340e84c5",
                0x89,
            ),
            (
                "$008B63",
                "$008BDC",
                "9abfa532544824df030d7ab8bb719ea35631c9a52153ea99e0c51e5b5f288b7a",
                0x60,
            ),
            (
                "$008BE2",
                "$008C37",
                "dece52902fd1c300420788df5fe1ba976a5a9a6be1b8b68e1fe08731793c7a96",
                0x60,
            ),
            (
                "$008C3D",
                "$008C6F",
                "684975ee283d2c75a6d236d410b28cd2a6817e237008580092b25e7d6703b454",
                0x60,
            ),
            (
                "$00D883",
                "$00D8BE",
                "152f95f7da8d5bd3769f97565ef9589215e8bce466eeacece374b84ad1ffc05f",
                0x6B,
            ),
        ]
        for start_text, end_text, digest, terminal_opcode in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "code")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(
                    hashlib.sha256(self.rom[start:end]).hexdigest(),
                    digest,
                )
                self.assertEqual(self.rom[end - 1], terminal_opcode)

        self.assertEqual(self.rom[0x008685:0x00868B], bytes.fromhex("a0 00 b0 00 c0 00"))
        self.assertEqual(self.rom[0x00D8BF:0x00D8C4], bytes(5))
        self.assertEqual(self.regions[("$00D856", "$00D882")]["type"], "data")

        tables = [
            ("$008C70", "$008D23", 90, "59b447035b07535fd9ac9a526d55d0844b22b1c8e93128abcc017fa17063719e"),
            ("$008D24", "$008D55", 25, "5581eddef0988c3c7c5e0a073cbf48e0839217d7942abc28cc95444fe903fa5d"),
            ("$008D56", "$008DFF", 85, "078be6e87b0f4808fcfd37a2a093ab159afe199d761e73cb0a33c8f860d02a92"),
            ("$008E00", "$008EA9", 85, "bb27a5556b86f0fadfe65d4f4cb991522be232c28a6d6964e7a18bd58c1a3436"),
        ]
        for start_text, end_text, record_count, digest in tables:
            with self.subTest(table=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "data")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(end - start, record_count * 2)
                self.assertEqual(hashlib.sha256(self.rom[start:end]).hexdigest(), digest)

    def test_bank_84_palette_and_picker_streams_have_exact_consumed_extents(self):
        palette = self.regions[("$0203E2", "$020441")]
        self.assertEqual(palette["type"], "graphics")
        self.assertEqual(palette["confidence"], "confirmed")
        self.assertEqual(len(self.rom[0x0203E2:0x020442]), 0x60)
        self.assertEqual(
            hashlib.sha256(self.rom[0x0203E2:0x020442]).hexdigest(),
            "fac29e8a7ac468d7da39f5c1dacc39ba96c31d234dba94992fd4918124faf521",
        )

        picker = self.regions[("$0223E0", "$0225BF")]
        self.assertEqual(picker["type"], "text")
        self.assertEqual(picker["confidence"], "confirmed")
        self.assertEqual(0x0225C0 - 0x0223E0, 2 * 0xF0)
        self.assertEqual(
            hashlib.sha256(self.rom[0x0223E0:0x0225C0]).hexdigest(),
            "0677cc64d3e013aad154ab6663514d958a34776dfa3af852ad563fe3a0ce26c9",
        )
        for slot in range(2):
            start = 0x0223E0 + slot * 0xF0
            words = [
                int.from_bytes(self.rom[offset:offset + 2], "little")
                for offset in range(start, start + 0xF0, 2)
            ]
            self.assertEqual(words.index(0), 112)
            self.assertEqual(set(words[112:]), {0})

    def test_bank_84_battle_display_stream_union_preserves_unread_gaps(self):
        expected = [
            (
                "$0206BE",
                "$0207CF",
                "c8ba9987c8188a2ad926555ad04f12591a9341557b43a06a9d3b5f25eb66e916",
            ),
            (
                "$0207D2",
                "$0208E3",
                "e05ee2f121b343871c554700ed72f8fb877358bc5f5e6be27bd55e910c8e68da",
            ),
            (
                "$0208F8",
                "$020C0B",
                "2e6eb23863ae745a0538f5a55ea218354c7b4779e2b27115ef446f33edbc55be",
            ),
        ]
        for start_text, end_text, digest in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "text")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(hashlib.sha256(self.rom[start:end]).hexdigest(), digest)

        self.assertEqual(self.regions[("$0207D0", "$0207D1")]["type"], "padding")
        self.assertEqual(self.regions[("$0208E4", "$0208F7")]["type"], "padding")
        self.assertEqual(self.rom[0x0207D0:0x0207D2], bytes.fromhex("72 02"))
        self.assertEqual(
            self.rom[0x0208E4:0x0208F8],
            bytes.fromhex("85 05 72 02 05 01 41 01 31 01 41 01 30 05 42 02 a1 05 a2 05"),
        )

        for slot in range(8):
            start = 0x02097E + slot * 0x30
            words = [
                int.from_bytes(self.rom[offset:offset + 2], "little")
                for offset in range(start, start + 0x30, 2)
            ]
            terminator = words.index(0)
            self.assertIn(terminator, (15, 16, 17))
            self.assertEqual(set(words[terminator:]), {0})

        separate_stream = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x020AFE, 0x020B0C, 2)
        ]
        self.assertEqual(separate_stream[-1], 0)
        self.assertNotIn(0, separate_stream[:-1])

        for slot in range(8):
            start = 0x020B0C + slot * 0x20
            words = [
                int.from_bytes(self.rom[offset:offset + 2], "little")
                for offset in range(start, start + 0x20, 2)
            ]
            terminator = words.index(0)
            self.assertIn(terminator, (12, 13, 14))
            self.assertEqual(set(words[terminator:]), {0})

    def test_bank_84_additional_palette_copies_exclude_unread_neighbors(self):
        expected = [
            (
                "$020C96",
                "$020CB5",
                0x20,
                "8da7cd70f3ea659c5f8d24c36882145043649592dc0e04c95fea881fba3779f0",
            ),
            (
                "$021E88",
                "$021EC7",
                0x40,
                "79b4c96408c6fe9729faec8b110c845c83f731ba22e78b2d36cf75e4e5e41b12",
            ),
        ]
        for start_text, end_text, size, digest in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "graphics")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(end - start, size)
                self.assertEqual(hashlib.sha256(self.rom[start:end]).hexdigest(), digest)

        self.assertEqual(self.regions[("$020C95", "$020C95")]["type"], "padding")
        self.assertEqual(self.rom[0x020C95], 0xD8)

        threshold_slices = [
            (
                "$021EC8",
                "$021ECD",
                "13c7595f91bdc52568a6b632dd24970d0d1c2fc56fa54057c03632f8e6a2c867",
            ),
            (
                "$021F18",
                "$021F1D",
                "df95c16cd4cdad0c7ea54c277e9c2ab1eb1f49acfb1bbe4dd17f00782bf09a7e",
            ),
            (
                "$021FA8",
                "$021FAD",
                "569bf72a903fe0507964dc3dae402e99207b7683643fbdfff122c89f05862e5c",
            ),
        ]
        for start_text, end_text, digest in threshold_slices:
            with self.subTest(threshold_slice=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "data")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(end - start, 6)
                self.assertEqual(hashlib.sha256(self.rom[start:end]).hexdigest(), digest)
                self.assertTrue(any(
                    region["type"] == "data"
                    and int(region["rom_start"][1:], 16) <= end
                    and int(region["rom_end"][1:], 16) >= end + 1
                    for region in self.regions.values()
                ))

    def test_bank_84_pointer_selected_battle_display_corpus_is_lossless(self):
        rows = self.regions[("$0226C0", "$02270F")]
        self.assertEqual(rows["type"], "text")
        self.assertEqual(rows["confidence"], "confirmed")
        self.assertEqual(0x022710 - 0x0226C0, 4 * 0x14)
        self.assertEqual(
            hashlib.sha256(self.rom[0x0226C0:0x022710]).hexdigest(),
            "148a50154107d37c74123d5b4fe4bc6d02912b4f044c3cee32ddf02d59eecbe7",
        )

        pointer_region = self.regions[("$022710", "$02273B")]
        self.assertEqual(pointer_region["type"], "pointer_table")
        self.assertEqual(pointer_region["confidence"], "confirmed")
        pointers = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x022710, 0x02273C, 2)
        ]
        self.assertEqual(len(pointers), 22)
        self.assertEqual(len(set(pointers)), 22)
        self.assertEqual(pointers[0], 0xA73C)
        self.assertEqual(pointers[-1], 0xBDF8)
        self.assertEqual(pointers, sorted(pointers))
        self.assertEqual(
            hashlib.sha256(self.rom[0x022710:0x02273C]).hexdigest(),
            "1ecdd0e2c37a5b0521e48d0f3d59a05e0633760f66a117fedf75ccc4bf11db44",
        )

        corpus = self.regions[("$02273C", "$023ECD")]
        self.assertEqual(corpus["type"], "text")
        self.assertEqual(corpus["confidence"], "confirmed")
        self.assertEqual(
            hashlib.sha256(self.rom[0x02273C:0x023ECE]).hexdigest(),
            "43fc3c95859eec8bedafe88649ca4f023cb4940caeb82f0f11e20479f2054da3",
        )
        for index, address in enumerate(pointers):
            start = 0x020000 + address - 0x8000
            expected_end = (
                0x020000 + pointers[index + 1] - 0x8000
                if index + 1 < len(pointers)
                else 0x023ECE
            )
            cursor = start
            while int.from_bytes(self.rom[cursor:cursor + 2], "little") != 0:
                cursor += 2
            self.assertEqual(cursor + 2, expected_end)

        password_streams = [
            (
                "$022630",
                "$022655",
                0x26,
                "8b5a6cc77c9c164d1775efba2d980c24bde81f0ee3fd2cf97852923ab5e292df",
            ),
            (
                "$022660",
                "$022683",
                0x24,
                "13c70375acbe9ed61f030b92c5d9e547029d9469b8fcd5dcaab8b82af0ed825f",
            ),
            (
                "$022690",
                "$0226B3",
                0x24,
                "29248ae92ae3176dad33f8ca49d5729770f7f868aba64fa1e433d76fd44b6240",
            ),
        ]
        for start_text, end_text, size, digest in password_streams:
            with self.subTest(password_stream=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "text")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(end - start, size)
                self.assertEqual(self.rom[end - 2:end], bytes(2))
                self.assertNotIn(bytes(2), self.rom[start:end - 2])
                self.assertEqual(hashlib.sha256(self.rom[start:end]).hexdigest(), digest)

        self.assertEqual(self.regions[("$02262C", "$02262F")]["type"], "padding")
        self.assertEqual(self.regions[("$022656", "$02265F")]["type"], "padding")
        self.assertEqual(self.regions[("$022684", "$02268F")]["type"], "padding")
        self.assertEqual(self.regions[("$0226B4", "$0226BF")]["type"], "padding")

    def test_progression_and_encounter_stride_tables_have_exact_domains(self):
        numeric = self.regions[("$017793", "$017992")]
        self.assertEqual(numeric["type"], "data")
        self.assertEqual(numeric["confidence"], "confirmed_structure_partial_schema")
        self.assertEqual(0x017993 - 0x017793, 64 * 8)
        self.assertEqual(
            hashlib.sha256(self.rom[0x017793:0x017993]).hexdigest(),
            "c66729c7bd76c32bd590ceedc78ae3afd1a5969faf2d5e64ceb20578438ea7f3",
        )
        for index in range(64):
            start = 0x017793 + index * 8
            self.assertEqual(self.rom[start + 6:start + 8], bytes(2))
        self.assertEqual(self.regions[("$017993", "$017A1A")]["type"], "data")

        self.assertEqual(self.regions[("$021ECE", "$021F17")]["type"], "data")
        self.assertEqual(self.regions[("$021F1E", "$021FA7")]["type"], "data")
        self.assertEqual(self.regions[("$021FAE", "$022047")]["type"], "data")

    def test_bank_ae_fixed_palette_copy_has_exact_extent(self):
        palette = self.regions[("$1722EC", "$17230B")]
        self.assertEqual(palette["type"], "graphics")
        self.assertEqual(palette["confidence"], "confirmed")
        self.assertEqual(len(self.rom[0x1722EC:0x17230C]), 0x20)
        self.assertEqual(
            hashlib.sha256(self.rom[0x1722EC:0x17230C]).hexdigest(),
            "45b5db89f6bd410d03be6b4ea7ce695e47b59efc7de1c601ecc0be2534259835",
        )
        self.assertEqual(self.regions[("$1722EB", "$1722EB")]["type"], "padding")
        self.assertEqual(self.regions[("$17230C", "$177FFF")]["type"], "fill")

    def test_bank_84_candidate_display_pointer_families_partition_exactly(self):
        families = [
            (
                "$0252DA",
                "$025359",
                "$02535A",
                "$025B43",
                64,
                31,
                "109e65f11a6a2475c0a8d0535577b60d5ed73ff85803e60af6a431b14e6c56d0",
                "bc2f0197929ca6c0e8129ef27070caca9b5f0078a7173604d145ed76f5ee8d65",
            ),
            (
                "$025B44",
                "$025BC3",
                "$025BC4",
                "$0263C7",
                64,
                31,
                "304f0da4a31d2ccda855da5205a54761fb25a3cb3b75804fa3ef52c41e2dbd9d",
                "915e1b1635b74632b083655aad78b3c2b614475227f47e2443e1eade100945bd",
            ),
            (
                "$0263C8",
                "$026447",
                "$026448",
                "$026AFF",
                64,
                30,
                "8946138e3c8a5d8658c1591ee8b91730150e7e7f5bd28a166d4649a22d1b4ea2",
                "806f594c59b80fe0a018f9c2a28dd69b118886fc3c9be37e94b689d9c12eefc3",
            ),
            (
                "$026B00",
                "$026B21",
                "$026B22",
                "$027141",
                17,
                17,
                "78100eaffd02cdc184420ab2002406a3f475d43ccaa02129154f897f7f679de8",
                "d74de4bac2951c3f031b47ddea0a069d8e8f2541265ac21e30edc3c037940d18",
            ),
        ]
        for (
            table_start_text,
            table_end_text,
            corpus_start_text,
            corpus_end_text,
            slot_count,
            unique_count,
            table_digest,
            corpus_digest,
        ) in families:
            with self.subTest(table=table_start_text):
                table = self.regions[(table_start_text, table_end_text)]
                corpus = self.regions[(corpus_start_text, corpus_end_text)]
                self.assertEqual(table["type"], "pointer_table")
                self.assertEqual(table["confidence"], "confirmed")
                self.assertEqual(corpus["type"], "text")
                self.assertEqual(corpus["confidence"], "confirmed")

                table_start = int(table_start_text[1:], 16)
                table_end = int(table_end_text[1:], 16) + 1
                corpus_start = int(corpus_start_text[1:], 16)
                corpus_end = int(corpus_end_text[1:], 16) + 1
                self.assertEqual(table_end - table_start, slot_count * 2)
                self.assertEqual(
                    hashlib.sha256(self.rom[table_start:table_end]).hexdigest(),
                    table_digest,
                )
                self.assertEqual(
                    hashlib.sha256(self.rom[corpus_start:corpus_end]).hexdigest(),
                    corpus_digest,
                )

                pointers = [
                    int.from_bytes(self.rom[offset:offset + 2], "little")
                    for offset in range(table_start, table_end, 2)
                ]
                unique_pointers = sorted(set(pointers))
                self.assertEqual(len(unique_pointers), unique_count)
                self.assertEqual(
                    unique_pointers[0],
                    0x8000 + (corpus_start & 0x7FFF),
                )
                for index, address in enumerate(unique_pointers):
                    start = 0x020000 + address - 0x8000
                    end = (
                        0x020000 + unique_pointers[index + 1] - 0x8000
                        if index + 1 < len(unique_pointers)
                        else corpus_end
                    )
                    cursor = start
                    while int.from_bytes(self.rom[cursor:cursor + 2], "little") != 0:
                        cursor += 2
                    self.assertEqual(cursor + 2, end)

        self.assertEqual(0x027142 - 0x0252DA, 7_784)
        self.assertEqual(self.rom[0x027140:0x027142], bytes(2))

    def test_bank_88_fixed_selector_three_pointer_is_consumer_owned(self):
        pointer = self.regions[("$040006", "$040007")]
        self.assertEqual(pointer["type"], "pointer_table")
        self.assertEqual(pointer["confidence"], "confirmed")
        self.assertEqual(int.from_bytes(self.rom[0x040006:0x040008], "little"), 0x8070)
        self.assertEqual(
            hashlib.sha256(self.rom[0x040006:0x040008]).hexdigest(),
            "e394698d0a8ee5d8f68bf6a86bdc6bd6cd17210d6e4ceb5cc2dd75d70c9c4533",
        )

        # CPU $90:A572 fixes WRAM $6B to selector 3 immediately before the
        # shared $83:C7DC/$83:CA1C display consumer.
        self.assertEqual(
            self.rom[0x08252E:0x082537],
            bytes.fromhex("a9 03 00 85 6b 22 dc c7 83"),
        )

        target = self.regions[("$040070", "$040077")]
        self.assertEqual(target["type"], "text")
        self.assertEqual(
            self.rom[0x040070:0x040078],
            bytes.fromhex("55 05 51 05 52 05 00 00"),
        )
        self.assertEqual(self.regions[("$040000", "$040001")]["type"], "pointer_table")
        self.assertEqual(self.regions[("$040004", "$040005")]["type"], "pointer_table")
        self.assertEqual(self.regions[("$040008", "$040017")]["type"], "pointer_table")

    def test_bank_80_control_stream_dispatch_has_exact_domain_and_boundaries(self):
        table = self.regions[("$004B8A", "$004BE7")]
        self.assertEqual(table["type"], "pointer_table")
        self.assertEqual(table["confidence"], "confirmed")
        self.assertEqual(
            hashlib.sha256(self.rom[0x004B8A:0x004BE8]).hexdigest(),
            "c8515b8961525cf0ef8bc4e026a67733e301af7dafa99d3d831fc9f302e97a72",
        )

        targets = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x004B8A, 0x004BE8, 2)
        ]
        self.assertEqual(len(targets), 0x2F)
        self.assertEqual(targets[0], 0)
        self.assertEqual(
            targets[1:],
            [
                0xCBE8, 0xCD7C, 0xCE71, 0xCEB2, 0xCFBD, 0xD069,
                0xD07F, 0xD09F, 0xD0AC, 0xD0C3, 0xD0DA, 0xD0E4,
                0xD0EE, 0xD0F4, 0xD0FA, 0xD104, 0xD10E, 0xD12A,
                0xD175, 0xD1CD, 0xD218, 0xD270, 0xD2BB, 0xD313,
                0xD336, 0xD35F, 0xD3C5, 0xD3FD, 0xD427, 0xD42A,
                0xD42D, 0xD475, 0xD492, 0xD495, 0xD4CA, 0xD522,
                0xD52B, 0xD54D, 0xD62B, 0xD6F8, 0xD743, 0xD79B,
                0xD7E6, 0xD83E, 0xD86C, 0xD88E,
            ],
        )

        expected_code = (
            (
                "$004BE8",
                "$004EF9",
                "cb5df04376152bf86907a4352dd141b237802b25ec5d925b0be6b79e2274e014",
            ),
            (
                "$004FBD",
                "$0058AB",
                "540683723feb23e83688502a835bd7a2e0b64b906c849230b02c446e24e499c9",
            ),
        )
        for start_text, end_text, digest in expected_code:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "code")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(hashlib.sha256(self.rom[start:end]).hexdigest(), digest)
                self.assertEqual(self.rom[end - 1], 0x60)

        # The first handler starts immediately after the final table word, so
        # its PHP/SEP bytes cannot be interpreted as an additional $2F entry.
        self.assertEqual(self.rom[0x004BE8:0x004BEC], bytes.fromhex("08 e2 20 ad"))
        self.assertEqual(self.rom[0x004EFA], 0x08)
        self.assertEqual(self.rom[0x004FBC], 0x6B)
        self.assertEqual(self.rom[0x0058AC], 0x08)
        self.assertNotIn(("$004EFA", "$0058AB"), self.regions)

    def test_bank_80_control_stream_callback_family_has_exact_boundary(self):
        region = self.regions[("$005A9A", "$006190")]
        self.assertEqual(region["type"], "code")
        self.assertEqual(region["confidence"], "confirmed")
        self.assertEqual(0x006191 - 0x005A9A, 1_783)
        self.assertEqual(
            hashlib.sha256(self.rom[0x005A9A:0x006191]).hexdigest(),
            "2bd44a2db0232f2d3bcad03978a2a83a4caa550eced31eb0392866068d64e621",
        )
        self.assertEqual(self.rom[0x006190], 0x60)

        # Opcode handler $01 installs $80:DA9A into the callback vector.
        self.assertEqual(
            self.rom[0x004BFA:0x004C0D],
            bytes.fromhex("22 8c d9 80 c2 20 a9 9a da 8d 79 03 e2 20 a9 80 8d 7b 03"),
        )

        local_jsr_targets = {
            int.from_bytes(self.rom[offset + 1:offset + 3], "little")
            for offset in range(0x005A9A, 0x00618F)
            if self.rom[offset] == 0x20
            and 0xDA9A <= int.from_bytes(self.rom[offset + 1:offset + 3], "little") <= 0xE190
        }
        self.assertEqual(
            local_jsr_targets,
            {
                0xDB30, 0xDB4D, 0xDB80, 0xDBB3, 0xDBC1,
                0xDC1E, 0xDC2F, 0xDC60, 0xDCBA, 0xDCC4,
                0xDD0D, 0xDD56, 0xDD9F, 0xDDE0, 0xDE4B,
                0xDE7A, 0xDEBF, 0xDF23, 0xDF36, 0xDF65,
                0xDFB8, 0xE022, 0xE07C, 0xE0EF, 0xE141,
            },
        )

        # $80:E191 is read as table data by $80:DF65 and is not swept into code.
        self.assertNotIn(("$006191", "$006191"), self.regions)
        self.assertEqual(self.rom[0x005F6D:0x005F71], bytes.fromhex("bf 91 e1 80"))

    def test_bank_80_callback_tables_classify_only_fully_consumed_blocks(self):
        expected = (
            ("$006191", "$00623A", 170, "67d735010ee560c4bf496342c49f75bc1aaecfe6129b94f49ecda8ea86de6036"),
            ("$0063A3", "$006506", 356, "1d6ea4ac2fb385369fb63825061a81b96225c7fed4379e3ba03418c32b5de179"),
            ("$00659F", "$0065FE", 96, "f5bce138cad323ba99638c5d9deb169bb1dcd83e2b832de0481a2f4361924c33"),
            ("$006617", "$006632", 28, "de7a353391227397615d0461c2f3f526147af93e5d3422c579f1012aaf6d0934"),
            ("$0066DB", "$006716", 60, "4e9533d87e552936a6527002c1d89d80f64b34b141b83cda21566a1cd859fc17"),
            ("$0067D7", "$0068D6", 256, "9325315210e87b971c799fab7a39d2c5107b95f0873c61160aafc910e5476eae"),
        )
        for start_text, end_text, size, digest in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "data")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(end - start, size)
                self.assertEqual(hashlib.sha256(self.rom[start:end]).hexdigest(), digest)

        consumed = set()
        def consume(start: int, size: int) -> None:
            consumed.update(range(start, start + size))

        for start, size in (
            (0x006191, 34), (0x0061B3, 42), (0x0061DD, 14),
            (0x0061EB, 32), (0x00620B, 22), (0x006221, 26),
        ):
            consume(start, size)
        for index in range(5):
            consume(0x0063A3 + index * 4, 4)
        for index in range(14):
            consume(0x0063B7 + index * 24, 24)
        for base in (0x00659F, 0x0065BF, 0x0065DF):
            for index in range(8):
                consume(base + index * 4, 4)
        consume(0x006617, 28)
        consume(0x0066DB, 28)
        for index in range(8):
            consume(0x0066F7 + index * 4, 4)
        for index in range(16):
            consume(0x0067D7 + index * 16, 16)

        for start_text, end_text, _, _ in expected:
            start = int(start_text[1:], 16)
            end = int(end_text[1:], 16) + 1
            self.assertTrue(set(range(start, end)) <= consumed)

        # The two unrelated gaps remain separate data records rather than being swept into adjacent callback tables.
        self.assertEqual(self.regions[("$006507", "$00651E")]["type"], "data")
        self.assertEqual(self.regions[("$00639B", "$0063A2")]["type"], "data")

    def test_bank_80_callback_stride_tables_own_exact_records(self):
        expected = (
            ("$00623B", "$00629A", 6, 0x10, 14, "305aad724f6629a0aba55fa96b8e02de8ae842ee679a18b86edb3e89d60c0dac"),
            ("$00629B", "$00633A", 10, 0x10, 12, "be5d5a33046289c759f92e7f026542d2177569bd3791aace69cd9cfad3a5c64f"),
            ("$00633B", "$00639A", 12, 0x08, 6, "1194c4d3165ad5b361893d401272558db411ca8f729781aebf2e386e879d2393"),
            ("$00651F", "$00659E", 16, 0x08, 6, "d284c78c9552edd2b4bd5ddc34ecf7bbb5069fc807ccf7f090a22418d30290be"),
            ("$0065FF", "$006616", 3, 0x08, 6, "47b3c2ef3853a404687b5cb567e3c7465fba2d7f0de9bdb141b0a61a886f3df6"),
            ("$006633", "$00667A", 9, 0x08, 6, "cfd3425dcde11ac2f1e54ad47d5ad61462e08e2304d8319d4ce519ecee3aef07"),
            ("$00667B", "$0066DA", 6, 0x10, 12, "6c23d57e1398eda5739dfd988730cfcc0f2ea8ffe0d8f64b164c222b592414b9"),
            ("$006717", "$0067D6", 12, 0x10, 12, "755738c8518b3d7cbfa6a4e5d70e16f0159e8c19082c309d1d396ec8e66fb34a"),
            ("$0068D7", "$006966", 9, 0x10, 12, "c216f9f0aff7c9f3b733bf9effd26bc70fdb35142382611d62178fe59272df9e"),
            ("$006967", "$006A56", 15, 0x10, 10, "7dc2c82e3dcf2e5c79aa2159f86c2329968da4d2f1f6443b4383cbecbecf30c7"),
        )
        for start_text, end_text, count, stride, copied, digest in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "data")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(end - start, count * stride)
                self.assertEqual(hashlib.sha256(self.rom[start:end]).hexdigest(), digest)
                for index in range(count):
                    padding = self.rom[
                        start + index * stride + copied:
                        start + (index + 1) * stride
                    ]
                    self.assertEqual(padding, bytes(stride - copied))

        self.assertEqual(self.regions[("$00639B", "$0063A2")]["type"], "data")
        self.assertEqual(self.regions[("$006507", "$00651E")]["type"], "data")

    def test_bank_80_post_allocation_fill_continuation_is_exact(self):
        region = self.regions[("$006DB3", "$007F7F")]
        self.assertEqual(region["type"], "fill")
        self.assertEqual(region["confidence"], "strong_inference")
        self.assertEqual(0x007F80 - 0x006DB3, 4_557)
        self.assertEqual(set(self.rom[0x006DB3:0x007F80]), {0xFF})
        self.assertEqual(self.rom[0x006DB2], 0xFF)
        self.assertNotIn(bytes.fromhex("b3 ed 80"), self.rom)
        self.assertEqual(self.rom[0x007F80:0x007F90], b"95/08/0306:38:02")

    def test_bank_80_post_timestamp_fill_has_only_compressed_false_pointers(self):
        region = self.regions[("$007F90", "$007FAF")]
        self.assertEqual(region["type"], "fill")
        self.assertEqual(region["confidence"], "strong_inference")
        self.assertEqual(self.rom[0x007F90:0x007FB0], bytes([0xFF]) * 32)

        far_pointer = bytes.fromhex("90 ff 80")
        hits = [
            offset
            for offset in range(len(self.rom) - 2)
            if self.rom[offset:offset + 3] == far_pointer
        ]
        self.assertEqual(hits, [0x0383DA, 0x0A1B44, 0x18AA88])
        for offset in hits:
            self.assertTrue(
                any(
                    region["type"] == "compressed_resource"
                    and int(region["rom_start"][1:], 16) <= offset
                    and int(region["rom_end"][1:], 16) >= offset + 2
                    for region in self.regions.values()
                )
            )

    def test_bank_81_name_entry_routine_and_coordinate_table_have_exact_extents(self):
        code = self.regions[("$008EAA", "$00939E")]
        self.assertEqual(code["type"], "code")
        self.assertEqual(code["confidence"], "confirmed")
        self.assertEqual(0x00939F - 0x008EAA, 1_269)
        self.assertEqual(
            hashlib.sha256(self.rom[0x008EAA:0x00939F]).hexdigest(),
            "47d23b36129c54bc7bdbf76ed20248d4535ce2e46df57bf23f0b3ac1d091f344",
        )

        # The already classified menu workflow provides the sole exact entry.
        self.assertEqual(
            self.rom[0x008413:0x00842B],
            bytes.fromhex("01 22 38 80 83 c2 20 ad 16 02 f0 22 20 aa 8e 20 39 87 22 06 89 80 e2 20"),
        )
        self.assertEqual(
            [
                offset
                for offset in range(len(self.rom) - 2)
                if self.rom[offset:offset + 3] == bytes.fromhex("20 aa 8e")
            ],
            [0x00841F],
        )
        self.assertEqual(self.rom[0x008EAA:0x008EAD], bytes.fromhex("c2 20 a9"))
        self.assertEqual(self.rom[0x00939E], 0x60)

        local_jsr_targets = {
            int.from_bytes(self.rom[offset + 1:offset + 3], "little")
            for offset in range(0x008EAA, 0x00939F)
            if self.rom[offset] == 0x20
            and 0x8EAA <= int.from_bytes(self.rom[offset + 1:offset + 3], "little") <= 0x939E
        }
        self.assertEqual(local_jsr_targets, {0x9334, 0x936C})
        local_jmp_targets = {
            int.from_bytes(self.rom[offset + 1:offset + 3], "little")
            for offset in range(0x008EAA, 0x00939F)
            if self.rom[offset] == 0x4C
            and 0x8EAA <= int.from_bytes(self.rom[offset + 1:offset + 3], "little") <= 0x939E
        }
        self.assertEqual(
            local_jmp_targets,
            {0x90B7, 0x90E4, 0x91A0, 0x91C2, 0x91E4, 0x92F6},
        )

        coordinates = self.regions[("$00939F", "$009426")]
        self.assertEqual(coordinates["type"], "data")
        self.assertEqual(coordinates["confidence"], "confirmed")
        self.assertEqual(0x009427 - 0x00939F, 68 * 2)
        self.assertEqual(
            hashlib.sha256(self.rom[0x00939F:0x009427]).hexdigest(),
            "7b36aeaf918644bcc36b3bf00969f672e9cd3f3b99487900e199408e37458390",
        )
        records = [
            tuple(self.rom[offset:offset + 2])
            for offset in range(0x00939F, 0x009427, 2)
        ]
        self.assertEqual(len(records), 0x44)
        self.assertEqual(records[0], (0x18, 0xA8))
        self.assertEqual(records[-1], (0xD8, 0xD8))

        # The consumer doubles $022B, while insertion stops incrementing at
        # $43; index $43 therefore reads exactly the final record and no byte
        # from the separately entered routine at $81:9427.
        self.assertEqual(
            self.rom[0x009334:0x00934D],
            bytes.fromhex("c2 20 ad 2b 02 0a c2 30 aa bf 9f 93 81 29 ff 00 85 45 bf a0 93 81 29 ff 00"),
        )
        self.assertEqual(
            self.rom[0x009216:0x009225],
            bytes.fromhex("ad 2b 02 c9 43 00 f0 33 ee 2b 02 ad 2b 02 c9"),
        )
        self.assertEqual(self.rom[0x009427:0x00942E], bytes.fromhex("08 8b 22 2d 82 80 e2"))

    def test_bank_82_battle_controller_partition_is_exact(self):
        expected = (
            ("$010000", "$010BD7", "code", 3_032, "595a61bf929d8525182a0db2338e5a6af1e6015965c3d42db27e936327e9b8a9"),
            ("$010BD8", "$010BDF", "pointer_table", 8, "afbe83dbc2415ab48f4a99c5cfcc10bf5c04fddf898b4be2344c7ca9ed813f70"),
            ("$010BE0", "$010F1F", "code", 832, "7144141c86ffcb5865957a398bec8cd578fc5ede3fec96cc670fe954cfe6bd54"),
            ("$010F20", "$010F4F", "data", 48, "88896f4b7d04f754d5c9c346841dd7e233af9af213c7edca1b8fa8877e75594c"),
            ("$010F50", "$011286", "code", 823, "d9bebad2287d47dc7a4ee59c4b0b4f76230aafaa4783d0e5b93cd83f7faeaf2f"),
        )
        for start_text, end_text, region_type, size, digest in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], region_type)
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                self.assertEqual(end - start, size)
                self.assertEqual(hashlib.sha256(self.rom[start:end]).hexdigest(), digest)

        main_entry = bytes.fromhex("22 00 80 82")
        self.assertEqual(
            [
                offset
                for offset in range(len(self.rom) - 3)
                if self.rom[offset:offset + 4] == main_entry
            ],
            [0x002E06, 0x004DE3, 0x018526, 0x018530, 0x01858B, 0x018595, 0x0813C6],
        )
        self.assertEqual(self.rom[0x010000:0x010008], bytes.fromhex("08 8b 4b ab e2 20 80 00"))
        self.assertEqual(self.rom[0x010BD7], 0x60)

        jump_targets = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x010BD8, 0x010BE0, 2)
        ]
        self.assertEqual(jump_targets, [0x8BE0, 0x8C4A, 0x8C71, 0x8C7E])
        self.assertEqual(self.rom[0x0104C9:0x0104D2], bytes.fromhex("ad 23 0e 0a aa bf d8 8b 82"))

        # Handler/initializer state assignments cover only dispatch indexes 0-3.
        for value in range(4):
            pattern = bytes.fromhex(f"a9 {value:02x} 00 8d 23 0e")
            self.assertIn(pattern, self.rom[0x010BE0:0x010F20])
        self.assertEqual(self.rom[0x010F1D:0x010F21], bytes.fromhex("ab 28 6b f0"))

        lookup = [
            int.from_bytes(self.rom[offset:offset + 2], "little")
            for offset in range(0x010F20, 0x010F50, 2)
        ]
        self.assertEqual(lookup, [0x08F0] * 24)
        self.assertEqual(self.rom[0x010E2B:0x010E34], bytes.fromhex("ad 27 0e 0a aa bf 20 8f 82"))

        helper_entries = {
            0x828F50: [0x002D0D, 0x002E2A, 0x010048],
            0x828FCB: [0x010098, 0x0100C7, 0x0100FC, 0x0119BD, 0x0155B1],
            0x82907E: [0x015613, 0x015664],
            0x829131: [0x002E65, 0x01005C],
            0x82922F: [0x002D17, 0x002D50, 0x002D6E, 0x002E61, 0x010058],
        }
        for address, expected_offsets in helper_entries.items():
            pattern = bytes((0x22, address & 0xFF, (address >> 8) & 0xFF, 0x82))
            self.assertEqual(
                [
                    offset
                    for offset in range(len(self.rom) - 3)
                    if self.rom[offset:offset + 4] == pattern
                ],
                expected_offsets,
            )
        self.assertEqual(self.rom[0x011282:0x01128A], bytes.fromhex("04 dc ab 28 6b f2 bc b0"))

    def test_bank_82_battle_helper_family_closes_before_hud_routine(self):
        region = self.regions[("$0112A2", "$011842")]
        self.assertEqual(region["type"], "code")
        self.assertEqual(region["confidence"], "confirmed")
        payload = self.rom[0x0112A2:0x011843]
        self.assertEqual(len(payload), 1_441)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "0fb0c771131768913d5ebacac6a917a35009b96a92ed31bc81a01e4edc0387f4",
        )

        entries = {
            0x8292A2: [0x002CBC, 0x01505A],
            0x8292BE: [0x002C6F, 0x01505E],
            0x8292D8: [0x002CC0, 0x015062],
            0x829313: [0x002C73, 0x015066],
            0x8293FE: [
                0x002CD6,
                0x01021B,
                0x010293,
                0x0102D0,
                0x01033E,
                0x012212,
                0x0147F0,
                0x01482F,
                0x015079,
                0x016F61,
            ],
            0x829465: [
                0x002C8F,
                0x010398,
                0x010407,
                0x01043C,
                0x0104BD,
                0x01356B,
                0x014CCB,
                0x014D0A,
                0x015081,
            ],
        }
        for address, expected_offsets in entries.items():
            pattern = bytes((0x22, address & 0xFF, (address >> 8) & 0xFF, 0x82))
            self.assertEqual(
                [
                    offset
                    for offset in range(len(self.rom) - 3)
                    if self.rom[offset:offset + 4] == pattern
                ],
                expected_offsets,
            )

        self.assertEqual(self.rom[0x0112A2:0x0112AE], bytes.fromhex("08 c2 20 a9 00 40 85 eb a9 2e 00 c2"))
        self.assertEqual(self.rom[0x011838:0x011848], bytes.fromhex("38 ed 85 03 85 48 22 fb 95 80 60 c2 10 a2 00 00"))

    def test_bank_82_visual_transitions_and_bitset_helper_have_exact_extents(self):
        expected = (
            ("$0156C3", "$01620A", 2_888, "000ad43152dc8be8898c121d098b41bc23d8870dedcd8c9951337b48cd6203d3"),
            ("$01620B", "$016695", 1_163, "23f5a3bcda6b45a19b16479f52dc60e0ba1574ccc379402873ff45fb1e988c35"),
            ("$016DFB", "$016E29", 47, "f3b61a7ecc313c98a6bb202d3955927a0493ebc5c01722af6f588166b5d9742a"),
        )
        for start_text, end_text, size, digest in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "code")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                payload = self.rom[start:end]
                self.assertEqual(len(payload), size)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)

        transitions = {
            0x82D6C3: [0x01314B, 0x014467],
            0x82D9C3: [0x013182, 0x01449E],
            0x82DC17: [0x0131B9, 0x0144D5],
            0x82DF3D: [0x01326A, 0x014586],
            0x82E20B: [0x0132AD, 0x0145C9],
        }
        for address, expected_offsets in transitions.items():
            pattern = bytes((0x22, address & 0xFF, (address >> 8) & 0xFF, 0x82))
            self.assertEqual(
                [
                    offset
                    for offset in range(len(self.rom) - 3)
                    if self.rom[offset:offset + 4] == pattern
                ],
                expected_offsets,
            )
        self.assertEqual(
            [self.rom[offset] for offset in (0x0159C2, 0x015C16, 0x015F3C, 0x01620A, 0x016695)],
            [0x6B] * 5,
        )
        self.assertEqual(self.rom[0x016696:0x01669E], bytes.fromhex("08 c2 20 64 29 ad 28 01"))

        bitset_call = bytes.fromhex("22 fb ed 82")
        self.assertEqual(
            sum(
                1
                for offset in range(len(self.rom) - 3)
                if self.rom[offset:offset + 4] == bitset_call
            ),
            65,
        )
        self.assertEqual(self.rom[0x016E21:0x016E29], bytes.fromhex("bd 2e 0d 05 00 9d 2e 0d"))
        self.assertEqual(self.rom[0x016E29], 0x6B)

    def test_bank_82_controller_owned_helper_tail_is_partitioned_exactly(self):
        expected = (
            ("$016696", "$01677B", 230, "e492aac4d1825c1b456fc062bda91c7140455137ea9a26a116f41ffbca24726b"),
            ("$01677C", "$0167DA", 95, "03c52a8d58d57e31a951f538fda6e6779c1e93b32fbce3756829c861a9bc0124"),
            ("$0167DB", "$016DFA", 1_568, "01533b0bd840b329665d9b6178bf3906c0b38ecda7e65fa1f0d2eb40a7846d70"),
            ("$016E2A", "$016E7A", 81, "5289481f2cc1816af3dc7b62f63d37d934f96664a5a8ad9533368b05cd6a055a"),
            ("$016E7B", "$016E8B", 17, "34b7d7039222c9a216c2c563d90ede757b3056b724eb30603d477cb525d192fb"),
            ("$016E8C", "$016F2B", 160, "23d518917bf409963c386eec7c4f0e84d4757099f6a49efdb0ecaa7079406102"),
            ("$016F2C", "$01701B", 240, "032c654e78a4fe980fbc67b3432965ab8656aee47d0ee74a13db6ec65c56358e"),
        )
        for start_text, end_text, size, digest in expected:
            with self.subTest(start=start_text):
                region = self.regions[(start_text, end_text)]
                self.assertEqual(region["type"], "code")
                self.assertEqual(region["confidence"], "confirmed")
                start = int(start_text[1:], 16)
                end = int(end_text[1:], 16) + 1
                payload = self.rom[start:end]
                self.assertEqual(len(payload), size)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)

        self.assertEqual(self.rom[0x016696:0x01669E], bytes.fromhex("08 c2 20 64 29 ad 28 01"))
        self.assertEqual(self.rom[0x016778:0x016780], bytes.fromhex("00 85 2f 60 08 c2 20 ad"))
        self.assertEqual(self.rom[0x016DF4:0x016DFC], bytes.fromhex("c2 20 80 00 ab 28 60 c2"))
        self.assertEqual(self.rom[0x016E77:0x016E7F], bytes.fromhex("9d 36 0d 60 c2 20 ad 2b"))
        self.assertEqual(self.rom[0x017018:0x017020], bytes.fromhex("2d 82 80 60 08 c2 30 a5"))

        calls = {
            bytes.fromhex("20 96 e6"): 4,
            bytes.fromhex("20 7c e7"): 1,
            bytes.fromhex("20 db e7"): 2,
            bytes.fromhex("20 2a ee"): 2,
            bytes.fromhex("20 7b ee"): 1,
            bytes.fromhex("20 8c ee"): 1,
            bytes.fromhex("20 2c ef"): 1,
        }
        for pattern, expected_count in calls.items():
            self.assertEqual(
                sum(
                    1
                    for offset in range(0x010000, 0x018000 - len(pattern) + 1)
                    if self.rom[offset:offset + len(pattern)] == pattern
                ),
                expected_count,
            )


if __name__ == "__main__":
    unittest.main()