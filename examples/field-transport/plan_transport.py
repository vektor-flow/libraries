"""Select a bounded research candidate from anonymous endpoint geometry only.

Selection is not acceptance. Renderers must validate trajectories and reject
unsupported or failed plans; there is no semantic or crossfade fallback.
"""
from affine_transport import AffineTransport
from field_transport import Transport
from registered_transport import RegisteredTransport
from replica_transport import ReplicaScene
from rigid_routes import RoutedScene

def plan_transport(a,b):
 if not a or not b:raise ValueError('Empty endpoints require an explicit material policy')
 if len(a)!=len(b):return 'replica',ReplicaScene(a,b)
 if len(a)>1:return 'route',RoutedScene(a,b)
 try:return 'affine',AffineTransport(a[0],b[0])
 except ValueError:pass
 if len(a[0])!=len(b[0]):raise ValueError('Hole creation/deletion is unsupported')
 if len(a[0])>2:return 'registered',RegisteredTransport(a[0],b[0])
 return 'contour',Transport(a[0],b[0])
