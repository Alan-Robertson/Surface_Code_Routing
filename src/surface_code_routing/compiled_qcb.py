import copy
from surface_code_routing.symbol import symbol_resolve
from surface_code_routing.scope import Scope
from surface_code_routing.instructions import RESET, MOVE

from surface_code_routing.dag import DAG
from surface_code_routing.qcb import QCB, SCPatch
from surface_code_routing.allocator import Allocator
from surface_code_routing.qcb_graph import QCBGraph
from surface_code_routing.qcb_tree import QCBTree
from surface_code_routing.router import QCBRouter
from surface_code_routing.mapper import QCBMapper

from surface_code_routing.circuit_model import PatchGraph
from surface_code_routing.inject_rotations import RotationInjector

def compile_qcb(dag, height, width, *externs, verbose=False):
    if verbose:
        print(f"Compiling {dag}")
        print("\tConstructing QCB...")
    qcb = QCB(height, width, dag)

    if verbose:
        print(f"\tAllocating QCB...")
    allocator = Allocator(qcb, *externs, tikz_build=True, verbose=verbose)
    qcb.allocator = allocator

    if verbose:
        print(f"\tConstructing Mapping")
    graph = QCBGraph(qcb)
    tree = QCBTree(graph)
    mapper = QCBMapper(dag, tree)

    if verbose:
        print(f"\tRouting...")
    circuit_model = PatchGraph(qcb.shape, mapper, None)
    rot_injector = RotationInjector(dag, mapper, qcb, graph=circuit_model)
    router = QCBRouter(qcb, dag, mapper, graph=circuit_model, verbose=verbose)
    compiled_qcb = CompiledQCB(qcb, router, dag)
    return compiled_qcb

class CompiledQCB:
    def __init__(self, qcb, router, dag):
        self.dag = dag
        self.router = router
        self.qcb = qcb

        self.symbol = qcb.symbol.extern()
        self.n_cycles = lambda : len(router.layers)
        self.n_pre_warm_cycles = lambda : 0
        self.width = qcb.width
        self.height = qcb.height
        self.externs = qcb.externs
        self.predicate = qcb.symbol
        self.io = qcb.symbol.io
        self.io_in = self.dag.symbol.io_in
        self.io_out = self.dag.symbol.io_out
        self.__is_factory = (sum(i is not self.symbol for i in self.symbol.io_in) == 0)
    
    def is_extern(self):
        return True

    def is_factory(self):
        return self.__is_factory 

    def instantiate(self):
        return CompiledQCB(self.qcb, self.router, self.dag) 

    def satisfies(self, other):
        return self.symbol.satisfies(other)

    def get_symbol(self):
        return self.symbol

    def get_obj(self):
        return self
    
    def __call__(self, *args):
        return self.instruction(*args)

    def __repr__(self):
        return self.symbol.__repr__()

    def instruction(self, args, targs):
        args = tuple(map(symbol_resolve, args))
        targs = tuple(map(symbol_resolve, targs))

        sym = symbol_resolve(f'CALL {self.predicate.symbol}') 
        fn = self.predicate.extern()
        scope = Scope({fn:fn})

        dag = DAG(sym, scope=scope)
        
        for arg, fn_arg in zip(args, self.predicate.ordered_io_in()):
            dag.add_gate(MOVE(arg, fn(fn_arg)))
        
        dag.add_node(fn, n_cycles=self.n_cycles())

        for targ, fn_arg in zip(targs, self.predicate.ordered_io_out()):
            dag.add_gate(MOVE(fn(fn_arg), targ))

        dag.add_gate(RESET(fn))
        return dag


    def __tikz__(self):
        return self.router.__tikz__()
