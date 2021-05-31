# Created by William Edwards (wre2@illinois.edu)

from pdb import set_trace

import numpy as np

from ConfigSpace import ConfigurationSpace
from ConfigSpace.hyperparameters import (UniformIntegerHyperparameter, 
        CategoricalHyperparameter)
import ConfigSpace.conditions as CSC

from .controller import Controller, ControllerFactory

class ZeroController(Controller):
    def __init__(self, system, task, model):
        super().__init__(system, task, model)

    @property
    def state_dim(self):
        return 0

    @staticmethod
    def is_compatible(system, task, model):
        return True
 
    def traj_to_state(self, traj):
        return np.zeros(0)

    def run(self, state, new_obs):

        return np.zeros(self.system.ctrl_dim), state
