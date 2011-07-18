from symboltable import SymbolTable
from topsort import topsort

import sys
from threading import Lock, RLock, Condition
from threadpool import ThreadPool
from functools import wraps
from itertools import izip
from collections import namedtuple, Mapping, Iterable, defaultdict, deque
#import multiprocessing as MP
#from collections import namedtuple

def transpose(adj):
    newadj = defaultdict(set)
    for u,vs in adj.iteritems():
        for v in vs:
            newadj[v].add(u)
    return newadj

class GraphFunc(object):
    def __init__(self, f, inputs=None, outputs=None):
        self.name = f.__name__
        if isinstance(inputs, Mapping):
            def pf_mapping(syms):
                d = dict((k, syms[v]) for k,v in inputs.items())
                return f(**d)
            self.prepared_f = pf_mapping
            self.input_syms = inputs.values()
        elif isinstance(inputs, (str, unicode)):
            self.prepared_f = lambda syms: f(syms[inputs])
            self.input_syms = [ inputs ]
        elif isinstance(inputs, Iterable):
            self.prepared_f = lambda syms: f(*[syms[k] for k in inputs])
            self.input_syms = inputs
        elif inputs is None:
            self.prepared_f = lambda _: f()
            self.input_syms = None
        else:
            raise ArgumentError("GraphFunc's inputs must be Mapping, str, unicode, Iterable, or None")

        if isinstance(outputs, Mapping):
            def osym_mapping(symtable, retval):
                newtable = symtable.new_child()
                if isinstance(retval, Mapping):
                    d = retval
                elif hasattr(retval, '__dict__'):
                    d = retval.__dict__
                else:
                    raise ArgumentError('GraphFunc called with a Mapping outputs expects f to return a Mapping or object with __dict__ attribute')

                for k,v in outputs.items(): newtable[v] = d[k]
                return newtable
            self.output = osym_mapping 
            self.output_syms = outputs.values()
        elif isinstance(outputs, str):
            def osym_scalar(symtable, retval):
                newsyms = symtable.new_child()
                newsyms[outputs] = retval
                return newsyms
            self.output = osym_scalar
            self.output_syms = [ outputs ]
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
                    raise ArgumentError('GraphFunc called with a Iterable output expects f to return a Mapping or object with __dict__ attribute or a Iterable')
                return newtable
            self.output = osym_iterable
            self.output_syms = outputs
        elif outputs is None:
            self.output = lambda syms, _: syms
            self.output_syms = None
        else:
            raise ArgumentError("GraphFunc's outputs must be Mapping, str, unicode, Iterable, or None")
    
    def get_func(self):
        def f(symtable):
            newsyms = self.output(symtable, self.prepared_f(symtable))
            return newsyms
        return f

    def __call__(self, symtable):
        newsyms = self.output(symtable, self.prepared_f(symtable))
        return newsyms

class SynchronizedCounter(object):
    """A counter to share between threads."""
    def __init__(self, initval=0):
        self.val   = initval 
        self.rlock = RLock()
    # we should use reader/writer locks but I'm too busy now.

    def _locked(f):
        @wraps(f)
        def decorated(self, *args, **kwargs):
            self.rlock.acquire()
#            print >> sys.stderr, "SynchronizedCounter.%s: lock acquired!"%f.__name__
            ret = f(self, *args, **kwargs)
            self.rlock.release()
#            print >> sys.stderr, "SynchronizedCounter.%s: lock released!"%f.__name__
            return ret
        return decorated

    @_locked
    def set(self, newval): self.val = newval

    @_locked
    def get(self): ret = self.val

    @_locked
    def inc(self):
        self.val += 1
        return self.val

    @_locked
    def dec(self):
        self.val -= 1
        return self.val

    @_locked
    def add(self, x):
        self.val += x
        return self.val

    @_locked
    def sub(self, x):
        self.val -= x
        return self.val

    @_locked
    def __repr__(self):
        return "SynchronizedCounter(%s)"%self.val

class ControlGraph(object):
    def __init__(self):
        self.depends  = defaultdict(set)
        self.symdeps  = []
        self.supplier = {}
        self.results  = {}
        self.finalized = False

    def add_func(self, f, inputs=None, outputs=None):
        self.finalized = False
        gf = GraphFunc(f, inputs, outputs)
        self.supplier.update((sym, gf) for sym in gf.output_syms)
        symdeps = (gf, gf.input_syms)
        self.symdeps.append(symdeps)

    def finalize(self):
        if not self.finalized:
            for gf,syms in self.symdeps:
                if syms is not None:
                    self.depends[gf] = set(self.supplier[s] for s in syms)
            self.preceded_by = transpose(self.depends)

    def run(self, symnames, init_symbols=None, N=4):
        if isinstance(symnames, (str, unicode)):
            symnames = [ symnames ]
        
        self.finalize()
        toporder = topsort(self.preceded_by)
        sources  = [ v for v in toporder if len(self.depends[v]) == 0 ] 
        remain_to_submit = SynchronizedCounter(len(toporder))
        
        finished_deps = defaultdict(SynchronizedCounter)
        p = ThreadPool(N)

        if init_symbols is None:
            syms = SymbolTable()
        else:
            syms = init_symbols

        parentlock = RLock()
        cv_done_submitting = Condition()
        # The callback runs within the thread. Don't know how to fix.
        def make_apply_callback(gf):
            def finished(new_syms):
                parentlock.acquire()
                self.results[gf] = new_syms
                parentlock.release()

                parentlock.acquire()
#                print "%s finished! printing state"%(gf.name)
#                print "finished_deps", finished_deps
#                print >> sys.stderr, "%s completed. new_syms = %s"%(gf.name, new_syms)
#                print "self.depends", self.depends
                parentlock.release()
                # Update the functions which we precede
                for next_gf in self.preceded_by[gf]:
                    finished_deps_next_gf = finished_deps[next_gf].inc()

                    if finished_deps_next_gf == len(self.depends[next_gf]):
                        # All dependencies satisfied; we can run!
                        # This may take a bit of time, but we want to do
                        # all data manipulation in this process.
                        print >> sys.stderr, "Dependencies for %s satisfied. Queueing."%next_gf.name
                        symtable = SymbolTable(parents=[self.results[r] for r in self.depends[next_gf]])

                        # Queue doesn't need to be locked
                        p.add_task(next_gf, args=(symtable,), callback=make_apply_callback(next_gf))
                        if remain_to_submit.dec() == 0:
                            print >> sys.stderr, "All jobs have been submitted. Notifying parent thread."
                            cv_done_submitting.acquire()
                            cv_done_submitting.notify()
                            cv_done_submitting.release()
            return finished                            

        for s in sources:
            remain_to_submit.dec()
            p.add_task(s, args=(SymbolTable(),), callback=make_apply_callback(s))

        cv_done_submitting.acquire()
        print >> sys.stderr, "PARENT THREAD: Awaiting condition variable"
        cv_done_submitting.wait()
        cv_done_submitting.release()
        print >> sys.stderr, "PARENT THREAD: Joining the thread pool"
        p.wait_completion()

        ret = dict((sym, self.results[self.supplier[sym]][sym]) for sym in symnames)
        return ret

