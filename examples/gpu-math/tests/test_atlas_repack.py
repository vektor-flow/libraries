import sys,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from repack_font_atlas import repack
class AtlasRepackTests(unittest.TestCase):
 def test_all_field_pixels_and_aliases_survive_repacking(self):
  image=Image.new('RGBA',(32,32));image.paste((1,25,125,255),(2,2,10,12));image.paste((240,80,20,0),(20,20,26,27))
  a={'uv':[2/32,2/32,10/32,12/32],'plane':[-1,-2,3,4]};b={'uv':[20/32,20/32,26/32,27/32],'rect':[0,0,6,7]}
  data={'atlasSize':[32,32],'tiles':{'one':a,'alias':dict(a)},'coverage96':{'coverage':[b]}}
  new,actual,receipt=repack(data,image)
  self.assertEqual(receipt['fields'],2);self.assertTrue(receipt['unchangedFieldPixels']);self.assertEqual(new['tiles']['one'],new['tiles']['alias']);self.assertEqual(data['tiles']['one']['uv'],a['uv'])
  for old,tile in [(a,new['tiles']['one']),(b,new['coverage96']['coverage'][0])]:
   original=tuple(round(v*32)for v in old['uv']);moved=tuple(round(v*32)for v in tile['uv']);self.assertEqual(image.crop(original).tobytes(),actual.crop(moved).tobytes())
if __name__=='__main__':unittest.main()
