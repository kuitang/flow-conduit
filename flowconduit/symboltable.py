
from collections import Mapping, Iterable, deque
from itertools import chain, imap, izip

class SymbolTable(dict):
    """
    Nested write-once symbol tables.

    Based on http://code.activestate.com/recipes/577434-nested-contexts-a-chain-of-mapping-objects/
    """
    def __init__(self, parents=(), map=None):
        'Create a new root context.'
        #print "SymbolTable.__init__: parents = ", parents
        self.parents = parents
        if map is not None:
            self.map = map
        else:
            self.map = {}

    # 7/18: made truly structural/recursive. Should make memoization easier.
    def maps(self):
        # bfs the parents
        q = deque([self])
        while q:
            t = q.popleft()
            assert isinstance(t, SymbolTable)
            q.extend(t.parents)
            yield t.map
        
    def new_child(self):
        'Make a child context.'
        return self.__class__(parents=(self,))

    def __getitem__(self, key):
        for m in self.maps():
            if key in m: break
        return m[key]
    
    def __setitem__(self, key, value):
        for m in self.maps():
            if key in m:
                raise TypeError("Key %s already exists in dictionary %x"%
                                key, id(m))
        self.map[key] = value

    def add_symbols(self, mapping_or_iterable):
        if isinstance(mapping_or_iterable, Mapping):
            if hasattr(mapping_or_iterable, 'iteritems'):
                iterable = mapping_or_iterable.iteritems()
            else:
                iterable = mapping_or_iterable.items()
        for k,v in iterable: self[k] = v

    def __len__(self, len=len, sum=sum, imap=imap):
        return sum(imap(len, self.maps()))

    def __iter__(self, chain_from_iterable=chain.from_iterable):
        return chain_from_iterable(self.maps())

    def __contains__(self, key, any=any):
        return any(key in m for m in self.maps())
    
    def __repr__(self, repr=repr):
        return 'SymbolTable(map=%s, parents=%s)'%(repr(self.map), repr(self.parents))

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
            newtable = symtable.new_child()
            if isinstance(retval, Mapping):
                d = retval
            elif hasattr(retval, '__dict__'):
                d = retval.__dict__
            else:
                raise TypeError('SymbolTableFunc called with a Mapping outputs expects f to return a Mapping or object with __dict__ attribute')

            for k,v in outputs.items(): newtable[v] = d[k]
            return newtable
        output = osym_mapping 
        output_syms = outputs.values()
    elif isinstance(outputs, (str, unicode)):
        def osym_scalar(symtable, retval):
            newsyms = symtable.new_child()
            newsyms[outputs] = retval
            return newsyms
        output = osym_scalar
        output_syms = [ outputs ]
    elif isinstance(outputs, Iterable):
        def osym_iterable(symtable, retval):
            newtable = symtable.new_child()
            if isinstance(retval, Mapping):
                for k in outputs: newtable[k] = retval[k]
            elif hasattr(retval, '__dict__'):
                for k in outputs: newtable[k] = retval.__dict__[k]
            elif isinstance(retval, Iterable):
                for k,v in izip(outputs, retval): newtable[k] = v
            else:
                raise TypeError('SymbolTableFunc called with a Iterable output expects f to return a Mapping or object with __dict__ attribute or a Iterable')
            return newtable
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

