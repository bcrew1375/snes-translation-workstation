import unittest
from snesworkbench.rom import cpu_to_offset,strip_copier_header
class RomTest(unittest.TestCase):
 def test_lorom(self): self.assertEqual(cpu_to_offset(0x02,0x8000,'lorom'),0x10000)
 def test_hirom(self): self.assertEqual(cpu_to_offset(0xC1,0x2345,'hirom'),0x12345)
 def test_copier(self): self.assertEqual(strip_copier_header(bytes(0x10200))[1],0x200)
if __name__=='__main__': unittest.main()
