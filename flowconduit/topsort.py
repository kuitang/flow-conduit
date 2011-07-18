# Based on CLRS 3rd ed, 613
# 

from itertools import chain
from functools import reduce
from collections import deque, defaultdict

intern('gray')
intern('black')

class TopsortState(object):
    def __init__(self):
        self.visited = {}
        self.result  = deque()

class CycleError(Exception): pass

def dfs(adj, state):
    #verts = chain(adj.iterkeys(), *adj.itervalues())
    # TODO: Figure out the generator
    verts = chain((j for i in adj.values() for j in i), adj.keys())
    for u in verts:
        if u not in state.visited: dfs_visit(adj, u, state)

def dfs_visit(adj, u, state):
    state.visited[u] = 'gray'
    for v in adj[u]:
        if v not in state.visited: dfs_visit(adj, v, state)
        elif state.visited[v] == 'gray':
            raise CycleError("Cycle with edge (%s, %s) detected."%(u,v))
    state.visited[u] = 'black'
    state.result.appendleft(u)

def topsort(adj):
    state = TopsortState()
    dfs(adj, state)
    del state.visited
    return state.result

def topsort_from_srcs(adj, srcs):
    state = TopsortState()
    for s in srcs:
        if s not in state.visited: dfs_visit(adj, s, state)
    del state.visited
    return state.result

