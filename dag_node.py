import numpy as np
import copy
from utils import log

class DAGNode():
    def __init__(self, 
                 deps=None, 
                 targs=None, 
                 predicates=None, 
                 symbol=None, 
                 layer_num=None, 
                 slack=0, 
                 magic_state=None, 
                 cycles=1):

        if targs is not None and type(targs) is not list:
            targs = [targs]

        if deps is not None and type(deps) is not list:
            deps = [deps]

        if predicates is None:
             predicates = {}

        if symbol is None:
            symbol = ""

        self.targs = targs
        self.symbol = symbol
        self.cycles = cycles

        # We will be filling these in once we've got an allocation
        self.start = -1
        self.end = -1
        self.anc = anc
        
        self.predicates = predicates 
        self.antecedents = {}

        self.non_local = len(self.targs) > 1
        self.slack = slack

        self.resolved = False
        self.magic_state = magic_state

        if layer_num is None:
            layer_num = max((self.predicates[i].layer_num + 1 for i in self.predicate), default=0)
        self.layer_num = layer_num

    def add_antecedent(self, targ, node):
        self.antecedent[targ] = node 

    def __contains__(self, i):
        return self.targs.__contains__(i)

    def __repr__(self):
        return "{}:{}".format(self.symbol, self.targs)
    def __str__(self):
        return self.__repr__()

    def add_node(self, targs):
        return self
