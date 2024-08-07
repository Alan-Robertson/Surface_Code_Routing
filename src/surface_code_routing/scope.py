class Scope():
    def __init__(self, *outer):

        self.mapping = {}

        if len(outer) == 0:
            outer = {}

        if isinstance(outer, str):
            outer = {outer}

        for element in outer:
            if isinstance(element, dict):
                self |= element
            elif isinstance(element, Scope):
                self |= element.mapping
            elif isinstance(element, Symbol):
                if element not in self:
                    self[element] = None
            else:
                self |= {i:None for i in element}
        self.mapping = {symbol_resolve(i):symbol_resolve(j) for i, j in self.mapping.items()}

    def __getitem__(self, index):
        return self.mapping[index]

    def __setitem__(self, index, item):
        self.mapping[index] = item

    def __iter__(self):
        return self.mapping.__iter__()

    def __repr__(self):
        return self.mapping.__repr__()

    def __str__(self):
        return self.__repr__()

    def __call__(self, index):
        return symbol_resolve(index) 

    def __len__(self):
        return len(self.mapping)

    def __or__(self, other:'Scope'):
        scope = Scope(self.mapping)
        for i in other:
            if i in self and other[i] is not None:
                scope[i] = other[i]
            else:
                scope[i] = other[i]
        return scope

    def __ior__(self, other):
        for i in other:
            if i in self and other[i] is not None:
                self[i] = other[i]
            else:
                self[i] = other[i]
        return self

    def items(self):
        return self.mapping.items()

    def keys(self):
        return self.mapping.keys()

    def values(self):
        return self.mapping.values()

    def __contains__(self, other):
        return other in self.mapping

    def unrollable(self):
        return ExternSymbol(None, None) not in self.values()

    def satisfies(self, symbol, subscope, exception=False):
        interface = symbol.bind_scope()
        for element in interface:
            if element not in subscope and element is not subscope[element]:
                if exception:
                    raise Exception(f"Invalid sub-scope {subscope}: Missing {element}")
                return False
            if subscope[element] not in self and subscope[element] is not element:
                if exception:
                    raise Exception(f"{element}:{subscope[element]} not in {self}")
                return False
        return True

    def contains(self, symbol):
        return any(map(lambda element: element.satisfies(symbol), self.mapping))

    def exactly_satisfies(self, subscope):
        for element in subscope:
            if element not in self:
                return False
        return True

    def inject(self, scope):
        new_mapping = dict()
        for i in self.mapping:
            new_mapping[scope[i]] = self.mapping[i]
        self.mapping = new_mapping

    def clear_scope(self):
        for i in self.mapping:
            self.mapping[i] = None 
      
    def backfill_scope(self):
        for i in self.mapping:
            if not i.is_extern() and self.mapping[i] is None:
                self.mapping[i] = self.mapping[i]

from surface_code_routing.symbol import Symbol, ExternSymbol, symbol_resolve
