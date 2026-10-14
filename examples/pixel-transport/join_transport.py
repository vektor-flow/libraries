"""Let sibling bodies contact before their deformation completes in reverse."""
import numpy as np
from lineage_transport import desired_center,center
from regularized_transport import configure as regularized_configure
from pixel_transport import clock


def configure(plan,lane_scale=.5,power=2.,area_power=1.5):
    regularized_configure(plan,lane_scale)
    for node in plan['nodes']:node.area_power=area_power
    def branch_center(node,t,scale):
        if node.parent is None:return desired_center(node,t,scale)
        parent=branch_center(node.parent,t,scale)
        v=clock(float(np.clip((t-node.birth)/(1-node.birth),0,1)))**power
        return parent+(1-v)*(center(node.part,scale)-center(node.parent.part,scale))+v*(node.goal-node.parent.goal)
    plan['desired_center']=branch_center
    plan['gentle_sibling_release']=True
    plan['branch_power']=power
    plan['area_power']=area_power
