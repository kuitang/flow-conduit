
from collections import Mapping, Iterable, deque
from itertools import chain, imap, izip

class SymbolTable(Mapping):
    """
    Nested, "immutable" symbol tables.

    Based on http://code.activestate.com/recipes/577434-nested-contexts-a-chain-of-mapping-objects/
    """

    def __init__(self, parents=(), map={}):
        'Create a new root context.'
        #print "SymbolTable.__init__: parents = ", parents
        assert isinstance(parents, Iterable)
        assert isinstance(map, Mapping)
        self._parents = parents
        
        # Cycles are impossible because these things are immutable.
        if map is not None:
            self.map = map
        else:
            self.map = {}

    # 7/18: made truly structural/recursive. Should make memoization easier.
    # It is inefficient to iterate every time, but this makes pickling
    # easier.
    # TODO: Figure out how to ignore pickling certain objects.
    def maps(self):
        # bfs the parents
        q = deque([self])
        # add cycle detection
        visited = set()
        while q:
            t = q.popleft()
            if id(t) not in visited:
                q.extend(t._parents)
                visited.add(id(t))
                yield t.map
        
    def new_child(self, map=None):
        'Make a child context.'
        return self.__class__(parents=(self,), map=map)
    
    # nah, can't really hash it because we don't know about the data!
    def __getitem__(self, key):
        for m in self.maps():
            if key in m: break
        return m[key]
    
    def __len__(self, len=len, sum=sum, imap=imap):
        return sum(imap(len, self.maps()))

    def __iter__(self, chain_from_iterable=chain.from_iterable):
        return chain_from_iterable(self.maps())

    def __contains__(self, key, any=any):
        return any(key in m for m in self.maps())
    
    def __repr__(self, repr=repr):
        return 'SymbolTable(map=%s, parents=%s)'%(repr(self.map), repr(self._parents))

def wrap_input_for_symtable(f, inputs):
    if isinstance(inputs, Mapping):
        def pf_mapping(syms):
            d = dict((k, syms[v]) for k,v in inputs.items())
            return f(**d)
        prepared_f = pf_mapping
        input_syms = inputs.values()
    elif isinstance(inputs, (str, unicode)):
        prepared_f = lambda syms: f(syms[inputs])
        input_syms = [ inputs ]
    elif isinstance(inputs, Iterable):
        prepared_f = lambda syms: f(*[syms[k] for k in inputs])
        input_syms = inputs
    elif inputs is None:
        prepared_f = lambda _: f()
        input_syms = None
    else:
        raise TypeError("SymbolTableFunc's inputs must be Mapping, str, unicode, Iterable, or None")
    return (prepared_f, input_syms)

def wrap_output_for_symtable(outputs):
    if isinstance(outputs, Mapping):
        def osym_mapping(symtable, retval):
            if isinstance(retval, Mapping):
                d = retval
            elif hasattr(retval, '__dict__'):
                d = retval.__dict__
            else:
                raise TypeError('SymbolTableFunc called with a Mapping outputs expects f to return a Mapping or object with __dict__ attribute')

            newtable_d = dict((v, d[k]) for k,v in outputs.items())
            return symtable.new_child(newtable_d)
        output = osym_mapping 
        output_syms = outputs.values()
    elif isinstance(outputs, (str, unicode)):
        def osym_scalar(symtable, retval):
            return symtable.new_child({outputs: retval})
        output = osym_scalar
        output_syms = [ outputs ]
    elif isinstance(outputs, Iterable):
        def osym_iterable(symtable, retval):
            if isinstance(retval, Mapping):
                newtable_d = dict((k, retval[k]) for k in outputs)
            elif hasattr(retval, '__dict__'):
                newtable_d = dict((k, retval.__dict__[k]) for k in outputs)
            elif isinstance(retval, Iterable):
                newtable_d = dict(izip(outputs, retval))
            else:
                raise TypeError('SymbolTableFunc called with a Iterable output expects f to return a Mapping or object with __dict__ attribute or a Iterable')
            return symtable.new_child(newtable_d)
        output = osym_iterable
        output_syms = outputs
    elif outputs is None:
        output = lambda syms, _: syms
        output_syms = None
    else:
        raise TypeError("SymbolTableFunc's outputs must be Mapping, str, unicode, Iterable, or None")
    return (output, output_syms)

class SymbolTableFunc(object):
    """Wraps a function to run with SymbolTables"""
    def __init__(self, f, inputs=None, outputs=None):
        self.name = f.__name__
        self.input,  self.input_syms  = wrap_input_for_symtable(f, inputs)
        self.output, self.output_syms = wrap_output_for_symtable(outputs)

    def __call__(self, symtable):
        newsyms = self.output(symtable, self.input(symtable))
        return newsyms

