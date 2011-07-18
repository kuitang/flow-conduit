"""
Nested write-once symbol tables.

Based on http://code.activestate.com/recipes/577434-nested-contexts-a-chain-of-mapping-objects/
"""

from collections import Mapping, Iterable
from itertools import chain, imap

class SymbolTable(dict):
    def __init__(self, parents=None):
        'Create a new root context.'
        #print "SymbolTable.__init__: parents = ", parents
        self.parents = parents
        self.map     = {}
        self.maps    = [ self.map ]
        if parents is not None:
            # Remember, it's a list of pointers.
            added = set()
            for p in parents:
                for m in p.maps:
                    if id(m) not in added:
                        added.add(id(m))
                        self.maps.append(m)

    def new_child(self):
        'Make a child context.'
        return self.__class__(parents=[ self ])

    def root(self):
        return self if self.parent is None else self.parent.root
    
    def __getitem__(self, key):
        for m in self.maps:
            if key in m: break
        return m[key]
    
    def __setitem__(self, key, value):
        for m in self.maps:
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
        return sum(imap(len, self.maps))

    def __iter__(self, chain_from_iterable=chain.from_iterable):
        return chain_from_iterable(self.maps)

    def __contains__(self, key, any=any):
        return any(key in m for m in self.maps)

    def __repr__(self, repr=repr):
        return ' -> '.join(imap(repr, self.maps))

