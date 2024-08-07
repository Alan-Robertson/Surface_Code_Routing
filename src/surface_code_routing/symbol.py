def symbol_map(*args):
    return map(symbol_resolve, args)

def symbol_resolve(arg):
    if isinstance(arg, Symbol):
        return arg
    return Symbol(arg)

class Symbol(object):

    def __init__(self, symbol:object, io_in=None, io_out=None, parent=None):
        '''
            Perfectly reasonable Python code
        '''
        if io_in is None:
            io_in = set()
        if io_out is None:
            io_out = set()

        if isinstance(symbol, Symbol) and not isinstance(symbol, ExternSymbol):
            io_in |= symbol.io_in
            io_out |= symbol.io_out
            symbol = symbol.symbol
            
        self.symbol = symbol
        self.parent = parent
        self.predicate = self
        self.io_in, self.io_out = map(self.format, (io_in, io_out))
        self.io = {j:i for i, j in enumerate(self.io_in)}
        self.io |= {j:len(self.io_in) + i for i, j in enumerate(self.io_out - self.io_in)}
        self.io_rev = dict(((j, i) for i, j in self.io.items()))
        self.io_element = None

        self.z = self.io_in
        self.x = self.io_out

    def format(self, io:'object|Sequence'):
        '''
            Basically overloads our constructor
        '''
        if io is None:
            io = set()
        elif not (type(io) in (list, tuple, set)):
            io = [symbol_resolve(io)]
        io = [symbol_resolve(i) for i in io]
        return {*io}

    def __getitem__(self, index):
        return self.io_rev[index]

    def __call__(self, index):
        return self[self.io[index]]

    def __len__(self):
        return len(self.io)

    def __iter__(self):
        return iter(self.io)
      
    def ordered_io(self):
        for i in range(len(self.io)):
            yield self[i]
        return

    def ordered_io_in(self):
        for i in range(len(self.io_in)):
            yield self[i]
        return

    def ordered_io_out(self):
        for i in range(len(self.io_out)):
            yield self[i]
        return


    def __contains__(self, other):
        if isinstance(other, Symbol):
            return other in self.io
        else:
            return other.__in__(Symbol)

    def __repr__(self, f_delim='<', b_delim='>'):
        if len(self.io_in) == 0 and len(self.io_out) == 0:
            return f'{f_delim}{self.symbol}{b_delim}'
        if len(self.io_in) == 0:
            return f'{f_delim}{self.symbol}: {tuple(self.io_out)}{b_delim}'
        if len(self.io_out) == 0:
            return f'{f_delim}{self.symbol}: {tuple(self.io_in)}{b_delim}'
        return f'{f_delim}{self.symbol}: {tuple(self.io_in)} {tuple(self.io_out)}{b_delim}'

    def __str__(self):
        return self.__repr__()

    def __eq__(self, comparator):
        if isinstance(comparator, Symbol):
            return self.symbol == comparator.symbol
        else:
            return self.symbol == comparator

    def satisfies(self, comparator):
        return self.symbol == comparator.symbol

    def __hash__(self):
        return hash(self.symbol)

    def get_parent(self):
        if self.parent is None:
            return self
        return self.parent.get_parent()

    def discriminator(self):
        return self

    def bind_scope(self):
        return Scope(self.io.keys())

    def inject(self, scope):
        io_in = set(scope[i] for i in self.io_in)
        io_out = set(scope[i] for i in self.io_out)

        io = {j:self.io[i] for i, j in zip(self.io_in, io_in)}
        io |= {j:self.io[i] for i, j in zip(self.io_out, io_out)}

        self.io = io
        self.io_rev = dict(((j, i) for i, j in self.io.items()))
        self.io_in = io_in
        self.io_out = io_out
        self.z = io_in
        self.x = io_out
        return self

    def is_extern(self):
        return False

    def get_symbol(self):
        return self

    def extern(self, io_in=None, io_out=None):
        predicate = Symbol(self.symbol)
        io = tuple(self.io.keys())
        if len(io) == 1:
            io = io[0]
        if io_in is None:
            io_in = self.io_in
        if io_out is None:
            io_out = self.io_out
        return ExternSymbol(predicate, io, io_in=io_in, io_out=io_out)

class ExternSymbol(Symbol):
    singleton = object()

    def __init__(self, predicate, io_element=None, io_in=None, io_out=None):
        
        self.symbol = Symbol('Extern Symbol')

           
        if isinstance(predicate, str):
            predicate = Symbol(predicate)
        
        if isinstance(io_element, str):
            io_element = Symbol(io_element)

        if predicate is not None and predicate.is_extern():
            parent = predicate
            predicate = predicate.discriminator()
        else:
            parent = None

        self.parent = parent
        self.predicate = predicate
        self.io_element = io_element
        self.io_in = {self}
        self.io_out = {self}
        self.io = {self:self}
        self.externs = [self]

        if io_in is None:
            io_in = set()
        if io_out is None:
            io_out = set()
        self.__internal_io_in = io_in
        self.__internal_io_out = io_out


    def __repr__(self):
        if self.io_element is not None:
            return f'EXTERN: {self.predicate.__repr__()} : {self.io_element.__repr__()}'
        else:
            return f'EXTERN: {self.predicate.__repr__()}'

    def __str__(self):
        return self.__repr__()

    def __hash__(self):
        return id(self.singleton)

    def __eq__(self, other):
        if not isinstance(other, ExternSymbol):
            return False
        return id(self.predicate) == id(other.predicate)

    def __len__(self):
        return 1

    def is_factory(self):
        return  None is next(iter(i for i in self.__internal_io_in if i is not self), None)

    def __call__(self, io_element):
        return ExternSymbol(self, io_element, io_in=self.__internal_io_in, io_out=self.__internal_io_out)

    def discriminator(self):
        return self.predicate.discriminator()

    def satisfies(self, other):
        if isinstance(other.predicate, ExternSymbol):
            return self.predicate.symbol == other.predicate.predicate
        return self.predicate.symbol == other.predicate.symbol

    def is_extern(self):
        return True


from surface_code_routing.scope import Scope
