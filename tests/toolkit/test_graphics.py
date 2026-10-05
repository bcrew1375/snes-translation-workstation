import unittest
from snesworkbench.graphics import encode_tiles,decode_tiles
class GraphicsTest(unittest.TestCase):
 def test_roundtrip(self):
  tile=[[((x+y)&15) for x in range(8)] for y in range(8)]
  self.assertEqual(decode_tiles(encode_tiles([tile],4),4),[tile])
if __name__=='__main__': unittest.main()
