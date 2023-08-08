from functools import reduce
from utils import consume
from tree_slots import TreeSlots, TreeSlot, SegmentSlot
from mapping_tree import RegNode, RouteNode
from qcb import SCPatch
import unittest

class TreeNodeInterface():
    def __init__(self, symbol, weight, slots, segment=None):
        self.symbol = symbol
        self.weight = weight
        self.slots = slots
        self.segment = segment
    
    def get_weight(self, *symbol):
        return self.weight

    def alloc(self, symbol):
        if self.symbol != symbol:
            return TreeSlots.NO_CHILDREN_ERROR
        if self.slots == 0:
            return TreeSlots.NO_CHILDREN_ERROR
        else:
            self.slots -= 1
            return self

    def get_symbol(self):
        return self.symbol

    def get_segment(self):
        return self.segment

    def exhausted(self, symbol):
        return self.slots == 0

    def __repr__(self):
        return f"[{self.symbol}: {self.weight}, {self.slots}]"

    def n_slots(self):
        return self.slots

class GraphNodeInterface:
    '''
        A dummy interface that implements the required functions for the test
    '''
    def __init__(self, symbol, n_slots=1):
        self.symbol = symbol
        self.n_slots = n_slots

    def get_symbol(self):
        return self.symbol

    def get_segment(self):
        return self

    def get_n_slots(self):
        return self.n_slots

    def __repr__(self):
        return str(self.string)

class SlotTest(unittest.TestCase):

    def test_no_slots(self):
        s = TreeSlots(None)
        assert s.alloc('TST') == TreeSlots.NO_CHILDREN_ERROR

    def test_one_alloc(self):
        s = TreeSlots(None)
        obj = TreeNodeInterface('TST', 2, 1)
        s.distribute('TST', obj)
        assert s.get_weight('TST') == 2
        assert s.alloc('TST').n_slots() == 0
        assert s.alloc('TST') == TreeSlots.NO_CHILDREN_ERROR

    def test_two_allocs(self):
        s = TreeSlots(None)
        obj = TreeNodeInterface('TST', 2, 2)
        s.distribute('TST', obj)
        assert s.get_weight('TST') == 2
        assert s.alloc('TST').n_slots() == 1
        assert s.alloc('TST').n_slots() == 0
        assert s.alloc('TST') == TreeSlots.NO_CHILDREN_ERROR

    def test_two_slots(self):
        s = TreeSlots(None)
        obj_a = TreeNodeInterface('TST', 3, 1)
        obj_b = TreeNodeInterface('TST', 2, 2)
        s.distribute('TST', obj_a)
        s.distribute('TST', obj_b)

        assert s.get_weight('TST') == 3
        assert s.alloc('TST').n_slots() == 0
        assert(len(s.slots['TST'].ordering) == 1)
        # Slot exhausted
        assert s.get_weight('TST') == 2

    def test_nested(self):
        s = TreeSlots(None)
        top = TreeSlots(None)

        # Segments
        segment_a = GraphNodeInterface(SCPatch.REG, n_slots=2) 
        segment_b = GraphNodeInterface(SCPatch.REG, n_slots=2) 

        # Associated with leaves on the tree
        obj_a = TreeNodeInterface(SCPatch.REG, 3, 1, segment=segment_a)
        obj_b = TreeNodeInterface(SCPatch.REG, 2, 1, segment=segment_b)
       
        # Associated with slots
        slot_a = SegmentSlot(obj_a)
        slot_b = SegmentSlot(obj_b)

        # Bound to other slots
        s.bind_slot(slot_a)
        s.bind_slot(slot_b)
        
        # Bound to other slots
        top.distribute_slots(s)

        # And allocated from the root
        assert top.alloc(SCPatch.REG) == slot_a
        assert top.alloc(SCPatch.REG) == slot_b
        assert top.alloc(SCPatch.REG) == slot_a
        assert top.alloc(SCPatch.REG) == slot_b
        assert top.alloc(SCPatch.REG) == TreeSlots.NO_CHILDREN_ERROR 


    def test_segment_slot(self):
        segment_a = GraphNodeInterface(SCPatch.REG)
        segment_b = GraphNodeInterface(SCPatch.REG)
        obj_a = SegmentSlot(TreeNodeInterface('TST', 3, 1, segment=segment_a))
        obj_b = SegmentSlot(TreeNodeInterface('TST', 2, 2, segment=segment_b))
 
        s = TreeSlots(None)
        top = TreeSlots(None)
        s.bind_slot(obj_a)
        s.bind_slot(obj_b)
        top.distribute_slots(s)

    def test_nested_distribute(self):
        s = TreeSlots(None)
        top = TreeSlots(None)
        obj_a = TreeNodeInterface('TST', 3, 1)
        obj_b = TreeNodeInterface('TST', 2, 2)
        obj_c = TreeNodeInterface('QWOP', 1, 1)
        s.distribute('TST', obj_a)
        s.distribute('TST', obj_b)
        s.distribute('QWOP', obj_c)
        top.distribute_slots(s)
        assert (len(s.slots['TST'].ordering) == 2)
        assert top.get_weight('TST') == 3
        assert top.alloc('TST') == obj_a
        assert(len(s.slots['TST'].ordering) == 1)
        assert top.get_weight('TST') == 2
        assert top.alloc('TST') == obj_b
        assert top.alloc('TST') == obj_b
        assert top.alloc('TST') == TreeSlots.NO_CHILDREN_ERROR
        assert top.get_weight('TST') == 0 
        assert top.alloc('QWOP') == obj_c

    def test_slot_merger(self):
        '''
            Build all the way from the graph
        '''
        a = RegNode(GraphNodeInterface('a'))
        b = RegNode(GraphNodeInterface('b'))
        c = RegNode(GraphNodeInterface('c'))
        d = RegNode(GraphNodeInterface('d'))
        route_a = RouteNode(GraphNodeInterface('route_a'))
        route_b = RouteNode(GraphNodeInterface('route_b'))
        route_b_one = RouteNode(GraphNodeInterface('route_b_1'))
        route_b_two = RouteNode(GraphNodeInterface('route_b_2'))
        route_c = RouteNode(GraphNodeInterface('route_c'))
        route_c_one = RouteNode(GraphNodeInterface('route_c'))
        route_d = RouteNode(GraphNodeInterface('route_d'))
        route_e = RouteNode(GraphNodeInterface('route_e'))

        a.neighbours = {route_a}
        b.neighbours = {route_b, route_b_one}
        c.neighbours = {route_c, route_c_one}
        d.neighbours = {route_d}
        route_a.neighbours = {a, route_e}
        route_b.neighbours = {b, route_e}
        route_b_one.neighbours = {b, route_b_two}
        route_b_two.neighbours = {route_b_one}
        route_c.neighbours = {c, route_e}
        route_c_one.neighbours = {c}
        route_d.neighbours = {d, route_e}
        route_e.neighbours = {route_a, route_b, route_c, route_d}

        leaves = {a, b, c, d}
        fringe = {a, b, c, d}
        parents = fringe

        while len(parents) > 1: 

            joint_nodes = set()
            starter = fringe
            fringe = reduce(lambda a, b: a | b, map(lambda x: x.get_adjacent(), starter))
 
            for node in starter:
                 for adjacent_node in node.get_adjacent():
                     parent = node.get_parent()
                     adj_parent = adjacent_node.get_parent()
                     if parent in joint_nodes:
                         joint_nodes.remove(parent)
                     if adj_parent in joint_nodes:
                         joint_nodes.remove(adj_parent)
                     joint_nodes.add(adj_parent.merge(parent))

            consume(map(lambda x: x.distribute(), fringe))
            consume(map(lambda x: x.bind(), joint_nodes))
            consume(map(lambda x: x.bind(), fringe))

            parents = set(map(lambda x : x.parent, fringe))

        layer = {a, b, c, d}
        while len(layer) > 1:
            consume(map(lambda x: x.distribute_slots(), layer))
            layer = set(map(lambda x: x.get_parent(), layer))


if __name__ == '__main__':
    unittest.main()
