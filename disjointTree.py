import random
import math
import sys
import logging

from checkCollision import *
from overrides import overrides

LOGGER = logging.getLogger(__name__)

def update_progress(progress, total_num, num_of_blocks=10):
    if not logging.getLogger().isEnabledFor(logging.INFO):
        return
    percentage = progress / total_num
    print('\r[{bar:<{num_of_blocks}}] {cur}/{total} {percen:0.1f}%'.format(
        bar='#' * int(percentage * num_of_blocks),
        cur=progress,
        total=total_num,
        percen=percentage * 100,
        num_of_blocks=num_of_blocks), end='')
    if percentage == 1:
        print()


class BFS:
    """Walk through the connected nodes with BFS"""

    def __init__(self, node, validNodes):
        self.visitedNodes = set()
        self.validNodes = validNodes
        self.next_node_to_visit = [node]
        self.next_node = None

    def visit_node(self, node):
        self.visitedNodes.add(node)
        self.next_node_to_visit.extend(node.edges)
        self.next_node = node

    def has_next(self):
        if self.next_node is not None:
            return True
        if len(self.next_node_to_visit) < 1:
            return False
        # get next available node
        while True:
            _node = self.next_node_to_visit.pop(0)
            if _node not in self.visitedNodes and _node in self.validNodes:
                break
            if len(self.next_node_to_visit) < 1:
                return False
        self.visit_node(_node)
        return True

    def next(self):
        node = self.next_node
        self.next_node = None
        return node


class TreesManager:
    def __init__(self, RRT, restart_when_merge):
        self.root = None
        self.disjointedTrees = []
        self.rrt = RRT
        self.restart_when_merge = restart_when_merge

    def connect_two_nodes(self, newnode, nn, parent_tree=None, draw_only=False):
        """Add node to disjoint tree OR root tree. Draw line for it too."""
        if not draw_only:
            if parent_tree is self.root:
                # using rrt* algorithm to add each nodes
                newnode, nn = self.rrt.rrt_star_add_node(newnode, nn)
            else:
                newnode.edges.append(nn)
                nn.edges.append(newnode)
            if parent_tree is not None:
                parent_tree.nodes.append(newnode)
        self.rrt.draw_path(newnode, nn)
        return newnode, nn

    def add_pos_to_existing_tree(self, newnode, parent_tree):
        """Try to add pos to existing tree. If success, return True."""
        nearest_nodes = self.find_nearest_node_from_neighbour(
            node=newnode,
            parent_tree=parent_tree,
            radius=self.rrt.RADIUS)
        for nearest_neighbour_node, nearest_neighbour_tree in nearest_nodes:
            if self.rrt.cc.path_is_free(newnode, nearest_neighbour_node):
                if parent_tree is None:
                    ### joining ORPHAN NODE to a tree
                    self.connect_two_nodes(newnode, nearest_neighbour_node, nearest_neighbour_tree)
                    parent_tree = nearest_neighbour_tree
                    LOGGER.debug(" ==> During respawning particle, joining to existing tree with size: {}".format(len(nearest_neighbour_tree.nodes)))
                else:
                    ### joining a TREE to another tree
                    try:
                        parent_tree = self.join_trees(parent_tree, nearest_neighbour_tree,
                                                               tree1_node=newnode, tree2_node=nearest_neighbour_node)
                    except AssertionError as e:
                        LOGGER.warning("== Assertion error in joining sampled point to existing tree... Skipping this node...")
        return parent_tree

    def find_nearest_node_from_neighbour(self, node, parent_tree, radius):
        """
        Given a tree, a node within that tree, and radius
        Return a list of cloest nodes (and its corresponding tree) within the radius (that's from other neighbourhood trees)
        Return None if none exists
        IF root exists in the list, add it at the last position (So the connection behaviour would remain stable)
            This ensure all previous action would only add add edges to each nodes, and only the last action would it
            modifies the entire tree structures wtih rrt* procedures.
        """
        nearest_nodes = {}
        for tree in [*self.disjointedTrees, self.root]:
            if tree is parent_tree:
                # skip self
                continue
            nn = self.rrt.find_nearest_neighbour(node, tree.nodes)
            if dist(nn.pos, node.pos) < radius:
                nearest_nodes[tree] = nn
            # nn = None
            # nn_dist = None
            # for n in tree.nodes:
            #     # only add the closest node form each trees
            #     _dist = dist(node.pos, n.pos)
            #     if _dist < radius:
            #         if nn_dist is None or _dist < nn_dist:
            #             # this node is not closer than other found nodes.
            #             nn = n
            #             nn_dist = _dist
            #             nearest_nodes[tree] = nn
        # construct list of the found solution. And root at last (or else the result won't be stable)
        root_nn = nearest_nodes.pop(self.root, None)
        nearest_nodes_list = [(nearest_nodes[key], key) for key in nearest_nodes]
        if root_nn is not None:
            nearest_nodes_list.append((root_nn, self.root))
        return nearest_nodes_list

    def join_tree_to_root(self, tree, middle_node):
        """It will join the given tree to the root"""
        from rrtstar import Colour
        bfs = BFS(middle_node, validNodes=tree.nodes)
        # add all nodes from disjoint tree via rrt star method
        total_num = len(tree.nodes)
        progress = 0
        LOGGER.info("> Joining to root tree")
        while bfs.has_next():
            newnode = bfs.next()
            progress += 1
            update_progress(progress, total_num, num_of_blocks=20)
            # draw white (remove edge for visual) on top of disjointed tree
            for e in (x for x in newnode.edges if x not in bfs.visitedNodes and x in bfs.validNodes):
                self.rrt.draw_path(e, newnode, Colour.white)
            try:
                self.connect_two_nodes(newnode, nn=None, parent_tree=self.root)
            except LookupError:
                LOGGER.warning("nn not found when attempting to joint to root. Ignoring...")
            # remove this node's edges (as we don't have a use on them anymore) to free memory
            del newnode.edges

        assert progress == total_num, "Inconsistency in BFS walk {} != {}".format(progress, total_num)

        # raise Exception("NOT implemented yet")

    def join_trees(self, tree1, tree2, tree1_node, tree2_node):
        """
        Join the two given tree together (along with their nodes).
        It will delete the particle reference from the second tree.
        It will use RRT* method to add all nodes if one of the tree is the ROOT.

        tree1_node & 2 represent the nodes that join the two tree together. It only matters currently to
        joining root tree to disjointed treeself.

        Return the tree that has not been killed
        """
        assert tree1 is not tree2, "Both given tree should not be the same"
        if tree1 not in self.disjointedTrees:
            assert tree1 is self.root, "Given tree is neither in disjointed tree, nor is it the root: {}".format(tree1)
        if tree2 not in self.disjointedTrees:
            assert tree2 is self.root, "Given tree is neither in disjointed tree, nor is it the root: {}".format(tree2)

        LOGGER.info(" => Joining trees with size {} to {}".format(len(tree1.nodes), len(tree2.nodes)))
        # Re-arrange only. Make it so that tree1 will always be root (if root exists among the two)
        # And tree1 node must always be belong to tree1, tree2 node belong to tree2
        if tree1 is not self.root:
            # set tree1 as root (if root exists among the two)
            tree1, tree2 = tree2, tree1
        if tree1_node in tree2.nodes or tree2_node in tree1.nodes:
            # swap to correct position
            tree1_node, tree2_node = tree2_node, tree1_node
        assert tree1_node in tree1.nodes, "Given nodes does not belong to the two given corresponding trees"
        assert tree2_node in tree2.nodes, "Given nodes does not belong to the two given corresponding trees"

        if tree1 is self.root:
            # find which middle_node belongs to the disjointed tree
            self.join_tree_to_root(tree2, tree2_node)
            self.connect_two_nodes(tree1_node, tree2_node, draw_only=True)
        else:
            self.connect_two_nodes(tree1_node, tree2_node)
            tree1.nodes.extend(tree2.nodes)
        del tree2.nodes
        self.disjointedTrees.remove(tree2)

        if self.restart_when_merge:
            # restart all particles
            for p in tree2.particle_handler:
                p.restart()
            del tree2.particle_handler
        else:
            # pass the remaining particle to the remaining tree
            for p in tree2.particle_handler:
                p.tree = tree1
                tree1.particle_handler.append(p)
        return tree1


############################################################
##              Disjointed Particles Sampler              ##
############################################################
from particleFilterSampler import ParticleFilterSampler, Particle, RANDOM_RESTART_PARTICLES_ENERGY_UNDER, ENERGY_START

RANDOM_RESTART_EVERY = 20
ENERGY_START = 10
RANDOM_RESTART_PARTICLES_ENERGY_UNDER = 0.75


class DisjointTreeParticle(Particle):
    @overrides
    def __init__(self, tree_manager, p_manager, direction=None, pos=None, isroot=False,
                 startPtNode=None):
        self.isroot = isroot
        self.p_manager = p_manager
        self.tree_manager = tree_manager
        self.last_node = None
        if isroot:
            self.tree_manager.root = TreeRoot(particle_handler=self)
            self.tree = self.tree_manager.root
            self.tree.nodes.append(startPtNode)
        super().__init__(direction=direction, pos=pos)

    @overrides
    def restart(self, direction=None, pos=None, restart_when_merge=True):
        if self.isroot:
            # root particles has a different initialisation method
            # (for the first time)
            self.isroot = False
            super().restart(direction, pos)
            return
        self.last_node = None
        merged_tree = None
        if pos is None:
            # get random position
            pos = self.p_manager.new_pos_in_free_space()
            merged_tree = self.tree_manager.add_pos_to_existing_tree(Node(pos), None)
            if merged_tree is not None and restart_when_merge:
                # Successfully found a new valid node that's close to existing tree
                # Return False to indicate it (and abort restart if we want more exploration)
                self.p_manager.add_to_restart(self)
                # we need to abort the restart procedure. add this to pending restart
                return False
        try:
            self.tree.particle_handler.remove(self)
        except AttributeError:
            # probably this is its first init
            pass
        # initialise to initial value, create new d-tree
        self.p_manager.modify_energy(particle_ref=self, set_val=ENERGY_START)
        if merged_tree is not None:
            self.tree = merged_tree
            merged_tree.particle_handler.append(self)
        else:
            self.tree = TreeDisjoint(particle_handler=self)
            self.tree.nodes.append(Node(pos))
            self.tree_manager.disjointedTrees.append(self.tree)
        super().restart(direction, pos)
        return True



class DisjointParticleFilterSampler(ParticleFilterSampler):

    @overrides
    def __init__(self, restart_when_merge=True):
        self.restart_when_merge = restart_when_merge
        super().__init__()

    @overrides
    def init(self, **kwargs):

        super().init(**kwargs)
        # Monkey patch the RRT for this smapler's specific stuff
        import types

        self.rrt.run_once = types.MethodType(rrt_dt_patched_run_once, self.rrt)
        self.rrt.rrt_star_add_node = types.MethodType(rrt_star_add_node, self.rrt)

        self.lsamplers_to_be_restart = []
        self.tree_manager = TreesManager(RRT=self.rrt, restart_when_merge=self.restart_when_merge)

        # ditch the particles created by the original particle filter sampler, and
        # create ones that has link towards the disjointed tree
        self.p_manager.particles = []
        for _ in range(self.p_manager.num_particles - 1):
            pos = self.p_manager.new_pos_in_free_space()

            dt_p = DisjointTreeParticle(
                direction=random.uniform(0, math.pi * 2),
                pos=pos,
                tree_manager=self.tree_manager,
                p_manager=self.p_manager,
            )

            self.p_manager.particles.append(dt_p)
        # spawn one that comes from the root
        self.p_manager.particles.append(
            DisjointTreeParticle(direction=random.uniform(0, math.pi * 2),
                                 pos=self.startPt,
                                 isroot=True,
                                 startPtNode=self.rrt.startPt,
                                 tree_manager=self.tree_manager,
                                 p_manager=self.p_manager,
                                 ))

    def particles_random_free_space_restart(self):
        for i in range(self.p_manager.size()):
            if self.p_manager.particles_energy[i] < RANDOM_RESTART_PARTICLES_ENERGY_UNDER:
                self.p_manager.add_to_restart(self.p_manager.particles[i])

    @overrides
    def report_success(self, idx, **kwargs):
        self.p_manager.particles[idx].last_node = kwargs['newnode']
        self.p_manager.confirm(idx, kwargs['pos'])
        self.p_manager.modify_energy(idx=idx, factor=0.95)

    @overrides
    def get_valid_next_node(self):
        """Loop until we find a valid next node"""
        while True:
            _tmp = self.get_next_node()
            if _tmp is None:
                # This denotes a particle had tried to restart and added the new node
                # to existing tree instead. Skip remaining steps and iterate to next loop
                return None
            rand = _tmp[0]
            self.rrt.stats.add_sampled_node(rand)
            if not self.rrt.collides(rand.pos):
                return _tmp
            report_fail = _tmp[-1]
            report_fail(pos=rand, obstacle=True)
            self.rrt.stats.add_invalid(obs=True)

    def restart_all_pending_local_samplers(self):
        # restart all pending local samplers
        while len(self.p_manager.local_samplers_to_be_rstart) > 0:
            # during the proces of restart, if the new restart position
            # is close to an existing tree, it will simply add to that new tree.
            if not self.p_manager.local_samplers_to_be_rstart[0].restart(restart_when_merge=self.restart_when_merge):
                # This flag denotes that a new position was found among the trees,
                # And it NEEDS to get back to restarting particles in the next ierations
                return False
            self.p_manager.local_samplers_to_be_rstart.pop(0)
        return True

    @overrides
    def get_next_node(self):
        self.counter += 1
        self._c_random += 1
        self._c_resample += 1

        if self._c_random > RANDOM_RESTART_EVERY > 0:
            self._c_random = 0
            self.particles_random_free_space_restart()
        if not self.restart_all_pending_local_samplers():
            LOGGER.debug("Adding node to existing trees.")
            return None
        # get a node to random walk
        choice = self.get_random_choice()

        # NOTE This controls if testing (via mouse) or actual runs
        pos = self.randomWalk(choice)
        # pos, choice = self.randomWalk_by_mouse()

        return (Node(pos), self.p_manager.particles[choice].tree, self.p_manager.particles[choice].last_node,
                lambda c=choice, **kwargs: self.report_success(c, **kwargs),
                lambda c=choice, **kwargs: self.report_fail(c, **kwargs))

    def randomWalk_by_mouse(self):
        """FOR testing purpose. Mimic random walk, but do so via mouse click."""
        from mouseSampler import MouseSampler as mouse
        pos = mouse.get_mouse_click_position(scaling=self.scaling)
        # find the cloest particle from this position
        _dist = None
        p_idx = None
        for i in range(len(self.p_manager.particles)):
            p = self.p_manager.particles[i]
            if _dist is None or _dist > dist(pos, p.pos):
                _dist = dist(pos, p.pos)
                p_idx = i
        LOGGER.debug("num of tree: {}".format(len(self.tree_manager.disjointedTrees)))
        self.p_manager.new_pos(idx=p_idx,
                               pos=pos,
                               dir=0)
        return pos, p_idx


############################################################
##    PATCHING RRT with disjointed-tree specific stuff    ##
############################################################

class Node:
    def __init__(self, pos):
        self.pos = np.array(pos)
        self.cost = 0  # index 0 is x, index 1 is y
        self.edges = []
        self.children = []
    def __repr__(self):
        try:
            num_edges = len(self.edges)
        except AttributeError:
            num_edges = "DELETED"
        return "Node(pos={}, cost={}, num_edges={})".format(self.pos, self.cost, num_edges)


def rrt_star_add_node(self, newnode, nn=None):
    """This function perform finding optimal parent, and rewiring."""
    from rrtstar import Colour, GOAL_RADIUS

    newnode, nn = self.choose_least_cost_parent(newnode, nn=nn, nodes=self.sampler.tree_manager.root.nodes)
    self.rewire(newnode, nodes=self.sampler.tree_manager.root.nodes)
    # check for goal condition
    if dist(newnode.pos, self.goalPt.pos) < GOAL_RADIUS:
        if newnode.cost < self.c_max:
            self.c_max = newnode.cost
            self.goalPt.parent = newnode
            newnode.children.append(self.goalPt.parent)
    return newnode, nn


def rrt_dt_patched_run_once(self):
    # Get an sample that is free (not in blocked space)
    _tmp = self.sampler.get_valid_next_node()
    if _tmp is None:
        # we have added a new samples when respawning a local sampler
        return
    rand, parent_tree, last_node, report_success, report_fail = _tmp
    if last_node is not None:
        # use the last succesful node as the nearest node
        # This is expliting the advantage of local sampler :)
        nn = last_node
        newnode = rand
    else:
        nn = self.find_nearest_neighbour(rand, parent_tree.nodes)
        # get an intermediate node according to step-size
        newnode = Node(self.step_from_to(nn.pos, rand.pos))
    # check if it is free or not ofree
    if not self.cc.path_is_free(nn, newnode):
        self.stats.add_invalid(obs=False)
        report_fail(pos=rand, free=False)
    else:
        self.stats.add_free()
        self.sampler.add_tree_node(newnode.pos)
        report_success(newnode=newnode, pos=newnode.pos)
        ######################
        newnode, nn = self.sampler.tree_manager.connect_two_nodes(newnode, nn, parent_tree)
        # try to add this newnode to existing trees
        self.sampler.tree_manager.add_pos_to_existing_tree(newnode, parent_tree)


############################################################
##                         Classes                        ##
############################################################


class TreeRoot:
    def __init__(self, particle_handler):
        self.particle_handler = [particle_handler]
        self.nodes = []
        # This stores the last node added to this tree (by local sampler)

    def __repr__(self):
        string = super().__repr__()
        string += '\n'
        import pprint
        string += pprint.pformat(vars(self), indent=4)
        # string += ', '.join("%s: %s" % item for item in vars(self).items())
        return string


class TreeDisjoint(TreeRoot):
    @overrides
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
