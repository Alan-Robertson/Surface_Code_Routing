import numpy as np
import copy
from utils import log

class DAGNode():
    def __init__(self, targs, edges=None, data=None, layer_num=None, slack=0, magic_state=False, cycles=1):
        if type(targs) is int:
            targs = [targs]
        if edges is None:
            edges = {}

        if data is None:
            data = ""

        self.targs = targs
        self.data = data
        self.cycles = cycles
        # TODO remove when we subclass 
        if self.data == 'CNOT':
            self.cycles = 3

        # We will be filling these in once we've got an allocation
        self.start = -1
        self.end = -1
        self.anc = None
        
        self.edges_precede = edges
        self.edges_antecede = {}

        self.non_local = len(self.targs) > 1
        self.slack = slack

        self.resolved = False
        self.magic_state = magic_state

        if layer_num is None:
            layer_num = max(self.edges_precede[i].layer_num + 1 for i in self.edges_precede)
        self.layer_num = layer_num

    def add_antecedent(self, targ, node):
        self.edges_antecede[targ] = node 

    def __contains__(self, i):
        return self.targs.__contains__(i)

    def __repr__(self):
        return "{}:{}".format(self.data, self.targs)
    def __str__(self):
        return self.__repr__()

class DAG():
    def __init__(self, n_blocks):

        self.n_blocks = n_blocks
        
        # Initial Nodes
        self.gates = [DAGNode(i, data="INIT", layer_num = 0) for i in range(n_blocks)]
        self.blocks = {i:self.gates[i] for i in range(n_blocks)}

        # Layer Later
        self.layers = []
        self.layers_conjestion = []
        self.layers_msf = []

        # Magic State Factory Nodes
        self.msfs = {} #
        self.msf_extra = None

        # Tracks which node each gate was last involved in
        # Ease of construction
        self.last_block = {i:self.gates[i] for i in range(n_blocks)} 
        self.layer()

    def __repr__(self):
        return str(self.layers)

    def add_gate(self, targs, data=None, magic_state=False):
        if type(targs) is int:
            targs = [targs]

        targs = copy.deepcopy(targs)
        if magic_state:
            targs.append(data)
            if data and data not in self.msfs:
                self.msfs[data] = DAGNode(targs=data, data='INIT', layer_num=0, magic_state=magic_state)
                self.blocks[data] = self.msfs[data]
                self.last_block[data] = self.msfs[data]

        edges = {}
        for t in targs:
            if t in self.msfs:
                edges[t] = self.blocks[t]
            else:
                edges[t] = self.last_block[t]
        
        gate = DAGNode(targs, edges, data=data)

        for t in targs:
            if t not in self.msfs: 
                self.last_block[t] = gate 

        for t in gate.edges_precede:
            gate.edges_precede[t].slack = max(gate.edges_precede[t].slack, 1 / (gate.layer_num - gate.edges_precede[t].layer_num))
            gate.edges_precede[t].edges_antecede[t] = gate

        self.gates.append(gate)
        self.layer_gate(gate)

    def layer_gate(self, gate):
        if gate.layer_num >= len(self.layers):
            self.layers += [[] for _ in range(gate.layer_num - len(self.layers) + 1)]
            self.layers_conjestion += [0 for _ in range(gate.layer_num - len(self.layers_conjestion) + 1)]
            self.layers_msf += [[] for _ in range(gate.layer_num - len(self.layers_msf) + 1)]
        
        self.layers_conjestion[gate.layer_num] += gate.non_local
        self.layers[gate.layer_num].append(gate)
        if gate.data in self.msfs:
            self.layers_msf[gate.layer_num].append(gate)


    def layer(self):
        self.layers = []
        for g in self.gates:
            self.layer_gate(g)

    def depth_parallel(self, n_channels):
        return sum(max(1, 1 + layer_conjestion - n_channels) for layer_conjestion in self.layers_conjestion)
        

    def dag_traverse(self, n_channels, *msfs, blocking=True, debug=False):
        traversed_layers = []

        # Magic state factory data
        msfs = list(msfs)
        msfs.sort(key = lambda x : x.cycles)
        msfs_state = [0] * len(msfs)

        # Labelling
        msfs_index = {}
        msfs_type_counts = {}
        for i, m in enumerate(msfs):
            msfs_index[i] = msfs_type_counts.get(m.symbol, 0)
            msfs_type_counts[m.symbol] = msfs_index[i] + 1 
        # print(f"{msfs_index=}")
        unresolved = copy.copy(self.layers[0])
        unresolved_update = copy.copy(unresolved)

        for symbol in self.msfs:
            self.msfs[symbol].resolved = 0

        while len(unresolved) > 0:
            traversed_layers.append([])
            non_local_gates_in_layer = 0
            patch_used = [False] * self.n_blocks

            unresolved.sort(key=lambda x: x.slack, reverse=True)

            for gate in unresolved:
               
                # Gate already resolved, ignore
                if gate.resolved:
                    continue

                # Channel resolution
                if (not gate.non_local) or (gate.non_local and non_local_gates_in_layer < n_channels):

                    # Check predicates
                    predicates_resolved = True
                    for predicate in gate.edges_precede:
                        if not gate.edges_precede[predicate].resolved or (gate.edges_precede[predicate].magic_state == False and patch_used[predicate]):
                            predicates_resolved = False
                            break
                    # print("resolved", gate, gate.layer_num)
                    # if gate.layer_num == 12:
                    #     print(f"{ {m: g.resolved for m,g in self.msfs.items()}=} {msfs=} {msfs_state=}")

                    if predicates_resolved:
                        traversed_layers[-1].append(gate)
                        gate.resolved = True

                        # Fungible MSF nodes
                        for targ in gate.targs:
                            if self.blocks[targ].magic_state is False:
                                patch_used[targ] = True
                        # Add antecedent gates
                        for antecedent in gate.edges_antecede:
                            if (gate.edges_antecede[antecedent] not in unresolved_update):
                                unresolved_update.append(gate.edges_antecede[antecedent])

                        # Expend a channel
                        if gate.non_local:
                            non_local_gates_in_layer += 1

                        # Remove the gate from the next round
                        unresolved_update.remove(gate)

                        # Resolve magic state factory resources
                        for predicate in gate.edges_precede:
                            if gate.edges_precede[predicate].magic_state:
                                for i, factory in enumerate(msfs):
                                    # Consume first predicate for each MS needed for the gate
                                    if predicate == factory.symbol and msfs_state[i] >= factory.cycles:
                                        msfs_state[i] = 0
                                        gate.edges_precede[predicate].resolved -= 1
                                        # TODO fix: ugly hack
                                        log("set", gate, i)
                                        gate.msf_extra = (msfs_index[i], factory)
                                                           #msfs_index[factory]
                                        break
            
            # Update MSF cycle state
            for i, gate in enumerate(msfs):
                if msfs_state[i] <= msfs[i].cycles:
                    msfs_state[i] += 1
                if msfs_state[i] == msfs[i].cycles:
                    self.msfs[msfs[i].symbol].resolved += 1

            unresolved = copy.copy(unresolved_update)
            if debug:
                print("FL:", front_layer)

        for gate in self.gates:
            gate.resolved = False

        for symbol in self.msfs:
            self.msfs[symbol].resolved = 0

        return len(traversed_layers), traversed_layers


    def depth_msf(self, *msfs, blocking=True, debug=True):
        ms_factories = {}
        for msf in msfs:
            if msf.symbol not in ms_factories:
                ms_factories[msf.symbol] = [[msf, 0]]
            else:
                ms_factories[msf.symbol].append([msf, 0])

        # Sort low to high cycles for maximum throughput
        for symbol in ms_factories:
            ms_factories[symbol].sort(key=lambda msf: msf[0].cycles)

        if debug:
            print(ms_factories)

        ms_gates = []
        n_cycles = 0
        while n_cycles < len(self.layers_msf) or len(ms_gates) > 0:
            
            if n_cycles < len(self.layers_msf):
                ms_gates += self.layers_msf[n_cycles]

            if debug:
                print(n_cycles)
                print(ms_factories)
                print(ms_gates)
                print("#####")

            # Clear all gates possible
            if (len(ms_gates) > 0):
                i = 0
                for ms_gate in ms_gates:
                    for j, (factory, count) in enumerate(ms_factories[ms_gate.data]):
                        if count >= factory.cycles:
                            ms_factories[ms_gate.data[1]] -= factory.cycles
                            ms_gates.pop(i)
                            i -= 1
                            break
                    i += 1

            # Update
            for symbol in ms_factories:
                for i, (factory, count) in enumerate(ms_factories[symbol]):
                    if blocking and count < factory.cycles:
                        ms_factories[symbol][i][1] += 1
                    elif not blocking:
                        ms_factories[symbol][i][1] += 1
            n_cycles += 1
        return n_cycles

              

    
    def calculate_proximity(self):
        m, minv = {}, []
        syms = self.msfs.keys()
        for i in range(self.n_blocks):
            m[i] = i
            minv.append(i)
        for s in syms:
            m[s] = len(minv)
            minv.append(s)
        
        prox = np.zeros((len(minv), len(minv)))

        for layer in self.layers:
            for gate in layer:
                if len(gate.targs) > 1:
                    for other_gate in layer:
                        if other_gate is not gate and len(other_gate.targs) > 1:
                            for targ in gate.targs:                            
                                for other_targ in other_gate.targs:
                                    prox[m[targ], m[other_targ]] += 1
        return prox, m, minv

    def calculate_conjestion(self):
        m, minv = {}, []
        syms = self.msfs.keys()
        for i in range(self.n_blocks):
            m[i] = i
            minv.append(i)
        for s in syms:
            m[s] = len(minv)
            minv.append(s)
        
        conj = np.zeros((len(minv), len(minv)))

        for layer in self.layers:
            for gate in layer:
                if len(gate.targs) > 1:
                    for other_gate in layer:
                        if other_gate is not gate and len(other_gate.targs) > 1:
                            for targ in gate.targs:
                                for other_targ in other_gate.targs:
                                    conj[m[targ], m[other_targ]] += 1
        return conj, m, minv

    def remap_msfs(self, n_channels, msfs):
        # TODO fix ugly hack
        # gates_copy = copy.deepcopy(self.gates)

        self.dag_traverse(n_channels, *msfs)

        for gate in self.gates:
            old_msf = None
            log(f"{gate=} {gate.edges_precede=} {gate.edges_antecede=}")
            for predicate in gate.edges_precede:
                if gate.edges_precede[predicate].magic_state:
                    old_msf = predicate

                    msf_id, factory = gate.msf_extra
                    new_sym = f"{old_msf}_#{msf_id}"
                    
                    if old_msf in self.msfs:
                        del self.msfs[old_msf]
                    del gate.edges_precede[predicate]

                    if new_sym not in self.msfs:
                        self.msfs[new_sym] = DAGNode(targs=[new_sym], data='INIT', layer_num=0, 
                                                     magic_state=True, cycles=factory.cycles)
                        self.gates.append(self.msfs[new_sym])
                        gate.edges_precede[new_sym] = self.msfs[new_sym]
                        self.msfs[new_sym].edges_antecede[new_sym] = gate
                    else:
                        prev = self.msfs[new_sym].edges_antecede[new_sym]

                        prep = DAGNode(targs=[new_sym], data='PREP', layer_num=prev.layer_num + 1, 
                                       magic_state=True, cycles=factory.cycles)

                        prev.edges_antecede[new_sym] = prep
                        prep.edges_precede[new_sym] = prev
                        prep.edges_antecede[new_sym] = gate
                        gate.edges_precede[new_sym] = prep
                        self.gates.append(prep)
                        self.msfs[new_sym] = prep



                    break
                    # gates_copy.append(gate.edges_precede[predicate])
            if old_msf:
                gate.targs[gate.targs.index(old_msf)] = new_sym
        log("new_gates", self.gates)
        # return gates_copy
            
