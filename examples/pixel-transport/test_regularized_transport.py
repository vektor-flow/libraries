import unittest
import numpy as np
from scipy import ndimage as ndi
from lineage_transport import make_plan,frame
from regularized_transport import configure,activity_clock

class RegularizedTests(unittest.TestCase):
    def test_clock_preserves_order_and_endpoints_when_speed_varies(self):
        y,x=np.mgrid[:60,:100]
        images=[]
        for t in np.linspace(0,1,101):
            center=20+60*t**3
            images.append(np.uint8(255*np.clip(7-np.hypot(x-center,y-30),0,1)))
        times=activity_clock(images)
        self.assertEqual(times[0],0);self.assertEqual(times[-1],1)
        self.assertTrue(np.all(np.diff(times)>0))
        before=np.diff(np.linspace(0,1,101)**3)[20:80]
        after=np.diff(times**3)[20:80]
        self.assertLess(after.std()/after.mean(),before.std()/before.mean())
    def test_stationary_clock_does_not_invent_motion(self):
        images=[np.zeros((20,20),np.uint8)]*101
        np.testing.assert_allclose(activity_clock(images),np.linspace(0,1,101),atol=1e-12)
    def test_rigid_sampling_has_no_canvas_rounding_jump(self):
        from types import SimpleNamespace
        from regularized_transport import RigidPatch
        patch=np.zeros((15,18));patch[2:13,3:15]=1
        node=SimpleNamespace(part=SimpleNamespace(patch=patch),final=SimpleNamespace(patch=patch),rigid_angle=0.)
        def placed(x):
            layer=RigidPatch(node,.5).stamp(np.array([x,40.]),0)
            result=np.zeros((80,120));ox,oy=layer['origin'];h,w=layer['alpha'].shape
            result[oy:oy+h,ox:ox+w]=layer['alpha'];return result
        for x in [50.,50.5,51.]:
            self.assertLess(abs(placed(x-1e-6)-placed(x+1e-6)).sum(),.001)
    def test_shape_continuity_and_exact_endpoints(self):
        a=np.zeros((150,260));b=a.copy();a[55:95,50:80]=1;b[55:95,140:150]=1;b[85:95,140:180]=1
        plan=make_plan(a,b,1);configure(plan)
        for t in [.33,.61,.77]:
            def delta(eps):
                left,_=frame(plan,t-eps,{},size=(260,150),offset=np.zeros(2))
                right,_=frame(plan,t+eps,{},size=(260,150),offset=np.zeros(2))
                return abs(left-right).sum()
            self.assertLess(delta(1e-5),delta(1e-3)*.03)
        start,_=frame(plan,0,{},size=(260,150),offset=np.zeros(2))
        end,_=frame(plan,1,{},size=(260,150),offset=np.zeros(2))
        np.testing.assert_array_equal(start,a);np.testing.assert_array_equal(end,b)

if __name__=='__main__':unittest.main()
