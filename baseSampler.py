import numpy as np
import random
import rrtstar

class Sampler:
    """
    Base sampler that defines each unique methods that some
    sampler uses but not all. This sampler does nothing with its own.
    """

    def init(self, *argv, **kwargs):
        self.XDIM = kwargs['XDIM']
        self.YDIM = kwargs['YDIM']
        self.RRT = kwargs['RRT']
        self.EPSILON = kwargs['EPSILON']
        self.scaling = kwargs['SCALING']

    def get_next_node(self, *argv, **kwargs):
        pass

    def get_valid_next_node(self):
        """Loop until we find a valid next node"""
        while True:
            coordinate, report_success, report_fail = self.get_next_node()
            rand = rrtstar.Node(coordinate)
            self.RRT.stats.add_sampled_node(rand)
            if not self.RRT.collides(rand.pos):
                return rand, report_success, report_fail
            report_fail(pos=rand, obstacle=True)
            self.RRT.stats.add_invalid(perm=True)

    def report_success(self, *argv, **kwargs):
        pass

    def report_fail(self, *argv, **kwargs):
        pass

    def add_tree_node(self, *argv, **kwargs):
        pass

    def add_sample_line(self, *argv, **kwargs):
        pass

    def paint(self, *argv, **kwargs):
        pass
