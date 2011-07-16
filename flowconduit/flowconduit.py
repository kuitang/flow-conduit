from symboltable import SymbolTable
from functools import wraps
from itertools import izip
from collections import namedtuple, Mapping, Sequence, defaultdict
#from collections import namedtuple

GraphFunc = namedtuple('GraphFunc', ['f', 'inputter', 'outputter'])

class GraphFunc(object):
    def __init__(f, inputs=None, outputs=None):
        self.name = f.__name__
        if isinstance(inputs, Mapping):
            def pf_mapping(syms):
                d = dict((k, syms[v]) for k,v in inputs.items())
                return f(**d)
            self.prepared_f = pf_mapping
            self.input_syms = inputs.values()
        elif isinstance(inputs, Sequence):
            self.prepared_f = lambda syms: f(*[syms[k] for k in inputs])
            self.input_syms = inputs
        elif inputs is None:
            self.prepared_f = lambda _: f()
            self.input_syms = None
        else:
            self.prepared_f = lambda syms: f(syms[inputs])
            self.input_syms = [ inputs ]

        if isinstance(outputs, Mapping):
            def osym_mapping(symtable, retval):
                newtable = symtable.new_child()
                if isinstance(retval, Mapping):
                    d = retval
                elif hasattr(retval, '__dict__'):
                    d = retval.__dict__
                else:
                    raise ArgumentError('GraphFunc called with a Mapping outputs expects f to return a Mapping or object with __dict__ attribute')
                for k,v in outputs:
                    newtable[v] = d[k]
                return newtable
            self.output = osym_mapping 
            self.output_syms = outputs.values()
        elif isinstance(outputs, Sequence):
            def osym_sequence(symtable, retval):
                newtable = symtable.new_child()
                if isinstance(retval, Mapping):
                    for k in outputs: newtable[k] = retval[k]
                elif hasattr(retval, '__dict__'):
                    for k in outputs: newtable[k] = retval.__dict__[k]
                elif isinstance(retval, Sequence):
                    for k,v in izip(outputs, retval): newtable[k] = v
                else:
                    raise ArgumentError('GraphFunc called with a Sequence output expects f to return a Mapping or object with __dict__ attribute or a Sequence')
            self.output = osym_sequence
            self.output_syms = outputs
        elif outputs is None:
            self.output = lambda syms, _: syms
            self.output_syms = None
        else:
            def osym_scalar(symtable, retval):
                newsyms = symtable.new_child()
                newsyms[outputs] = retval
                return newsyms
            self.output = osym_scalar
            self.output_syms = [ outputs ]
    
    def call(symtable):
        newsyms = self.output(symtable, self.prepared_f(symtable))
        return newsyms

class ControlGraph(object):
    def __init__():
        self.depends  = defaultdict(list)
        self.symdeps  = []
        self.supplier = {}
        self.finalized = False

    def add_func(self, f, inputs=None, outputs=None):
        self.finalized = False
        gf = GraphFunc(f, inputs, outputs)
        self.supplier.update((sym, gf) for sym in gf.output_syms)
        symdeps = (gf, gf.input_syms)
        self.symdeps.append(symdeps)

    def finalize():
        if not self.finalized:
            for gf,syms in self.symdeps:
                self.depends[gf] = [ self.supplier[s] for s in syms ] # literally want lists



