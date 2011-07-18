from symboltable import SymbolTable, SymbolTableFunc
from topsort import topsort_from_srcs, dfs_visit, TopsortState

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
        gf = SymbolTableFunc(f, inputs, outputs)
        self.supplier.update((sym, gf) for sym in gf.output_syms)
        symdeps = (gf, gf.input_syms)
        self.symdeps.append(symdeps)

    def finalize(self):
        if not self.finalized:
            for gf,syms in self.symdeps:
                if syms is not None:
                    self.depends[gf] = set(self.supplier[s] for s in syms)
            self.preceded_by = transpose(self.depends)

    def _topsort_subgraph(self, symnames):
        suppliers = set(self.supplier[s] for s in symnames)
        depends_toporder = topsort_from_srcs(self.depends, suppliers)
        toporder         = topsort_from_srcs(self.depends, depends_toporder)
        return toporder

    def run(self, symnames, init_symbols=None, N=4):
        if isinstance(symnames, (str, unicode)):
            symnames = [ symnames ]
        
        self.finalize()
        toporder = self._topsort_subgraph(symnames)
        sources  = ( v for v in toporder if len(self.depends[v]) == 0 )
        remain_to_submit = SynchronizedCounter(len(toporder))
        finished_deps = defaultdict(SynchronizedCounter)
        p = ThreadPool(N)

        if init_symbols is None:
            syms = SymbolTable()
        else:
            syms = init_symbols

        parentlock = RLock()

        done_submitting = Condition()
        # If the child thread notifies before the parent thread reaches the
        # wait statement, then the parent will never receive the notification
        # and will block forever. To fix this, the child will decrement this
        # counter to zero, and the parent will check this before waiting.
        done_submitting_helper = SynchronizedCounter(1)
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
                            print >> sys.stderr, "All jobs have been submitted. Waiting for parent thread to be ready to receive done_submitting"
                            done_submitting.acquire()
                            done_submitting.notify()
                            done_submitting.release()
                            done_submitting_helper.dec()
            return finished                            

        for s in sources:
            remain_to_submit.dec()
            p.add_task(s, args=(SymbolTable(),), callback=make_apply_callback(s))

        if done_submitting_helper.get() > 0:
            done_submitting.acquire()
            print >> sys.stderr, "PARENT THREAD: Awaiting condition variable"
            done_submitting.wait()
            done_submitting.release()
        print >> sys.stderr, "PARENT THREAD: Joining the thread pool"
        p.wait_completion()

        ret = dict((sym, self.results[self.supplier[sym]][sym]) for sym in symnames)
        return ret

