import sys, os
sys.path.append(os.getcwd() + "/..")

import numpy as np
import autompc as ampc
from pdb import set_trace

dummy = ampc.System(["x1", "x2"], ["u"])


from autompc.sysid.dummy_nonlinear import DummyNonlinear
x0 = [2.0, 3.0]
u0 = [1.0]
traj = ampc.zeros(dummy, 1)
traj[0].obs[:] = x0
traj[0].ctrl[:] = u0

model = DummyNonlinear(dummy)
state = model.traj_to_state(traj)
xnew, grad = model.pred_diff(state, u0)

print("xnew={}".format(xnew))

print("d x1[k+1] / d x2[k] = {}".format(grad[0,1]))
