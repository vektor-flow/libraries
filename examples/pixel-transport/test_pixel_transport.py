import unittest
import numpy as np
from scipy import ndimage as ndi
from pixel_transport import segment,match,positions,Region,plan_paths

class PixelTransportTests(unittest.TestCase):
    def test_geometry_matches_swapped_objects_without_ids(self):
        a=np.zeros((100,180),bool);a[20:40,20:35]=True;a[60:80,120:155]=True
        b=np.zeros_like(a);b[20:40,20:55]=True;b[60:80,120:135]=True
        source,target=segment(a,0),segment(b,0)
        matches=match(source,target)
        self.assertEqual([m['target'] for m in matches],[1,0])
        self.assertTrue(all(m['mode']=='rigid' for m in matches))
    def test_rotation_recovered_from_pixels(self):
        a=np.zeros((120,120),bool);a[30:80,40:50]=True;a[70:80,40:80]=True
        b=ndi.rotate(a.astype(float),37,reshape=False,order=1)>.5
        matches=match(segment(a,0),segment(b,0))
        self.assertAlmostEqual(matches[0]['angle']*180/np.pi,-37,delta=.7)
        self.assertEqual(matches[0]['mode'],'rigid')
    def test_deformation_is_not_silently_reported_as_rigid(self):
        a=np.zeros((80,80),bool);a[10:30,10:30]=True
        b=np.zeros_like(a);b[10:20,10:50]=True
        matches=match(segment(a,0),segment(b,0))
        self.assertEqual(matches[0]['mode'],'needs-deformation')
        with self.assertRaises(ValueError):plan_paths(segment(a,0),segment(b,0),matches,a.shape)
    def test_split_requires_explicit_solver(self):
        a=np.zeros((80,80),bool);a[10:30,10:30]=True
        b=a.copy();b[50:60,50:60]=True
        with self.assertRaises(ValueError):match(segment(a,0),segment(b,0))
    def test_overlapping_material_cannot_pass_path_check(self):
        r=Region(np.array([[0.,0.],[1.,0.],[0.,1.]]),np.array([30.,30.]),3)
        matches=[dict(source=i,target=i,angle=0,mode='rigid') for i in range(2)]
        with self.assertRaises(ValueError):plan_paths([r,r],[r,r],matches,(80,80))
    def test_curved_rigid_path_preserves_distances_and_endpoints(self):
        a=Region(np.array([[0.,0.],[4.,0.],[0.,3.]]),np.array([30.,30.]),3)
        b=Region(a.points,np.array([80.,80.]),3)
        for t in np.linspace(0,1,31):
            p=positions(a,b,1.1,t,20)
            self.assertAlmostEqual(np.linalg.norm(p[1]-p[2]),5)
        np.testing.assert_allclose(positions(a,b,1.1,0,20),a.points+a.center)

if __name__=='__main__':unittest.main()
